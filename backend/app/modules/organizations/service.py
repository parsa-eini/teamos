"""Organization use cases. Organization identity is never taken from the client."""

import re
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import (
    ForbiddenError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.core.security import hash_password
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import Organization, OrganizationMembership, OrganizationRole
from app.modules.organizations.schemas import (
    HierarchyNode,
    OrganizationMemberCreate,
    OrganizationMemberRead,
    OrganizationMemberUpdate,
    OrganizationUpdate,
)
from app.modules.users import repository as users_repository
from app.modules.users.models import User

_SLUG_MAX_LENGTH = 100
_MANAGE_MEMBER_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = "organization"
    return slug[:_SLUG_MAX_LENGTH]


def allocate_unique_slug(session: Session, name: str) -> str:
    base = slugify(name)
    if organizations_repository.get_organization_by_slug(session, base) is None:
        return base

    suffix_room = 9  # hyphen + 8 hex chars
    trimmed = base[: _SLUG_MAX_LENGTH - suffix_room].rstrip("-") or "organization"
    for _ in range(8):
        candidate = f"{trimmed}-{uuid4().hex[:8]}"
        if organizations_repository.get_organization_by_slug(session, candidate) is None:
            return candidate
    raise ResourceAlreadyExistsError("An organization with this slug already exists")


def create_organization_with_owner(
    session: Session,
    *,
    name: str,
    owner_user_id: UUID,
) -> Organization:
    """Create an organization and OWNER membership. Caller owns the surrounding transaction."""
    organization = Organization(name=name.strip(), slug=allocate_unique_slug(session, name))
    organizations_repository.add_organization(session, organization)
    session.flush()

    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=owner_user_id,
        role=OrganizationRole.OWNER,
    )
    organizations_repository.add_membership(session, membership)
    session.flush()
    return organization


def update_organization(
    session: Session,
    organization: Organization,
    payload: OrganizationUpdate,
    *,
    role: OrganizationRole,
) -> Organization:
    if role != OrganizationRole.OWNER:
        raise ForbiddenError("Only the organization owner can update the organization")

    if payload.name is not None:
        organization.name = payload.name

    if payload.slug is not None and payload.slug != organization.slug:
        existing = organizations_repository.get_organization_by_slug(session, payload.slug)
        if existing is not None and existing.id != organization.id:
            raise ResourceAlreadyExistsError("An organization with this slug already exists")
        organization.slug = payload.slug

    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def list_members(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
) -> tuple[list[OrganizationMemberRead], PaginationMeta]:
    rows, total = organizations_repository.list_members(
        session,
        context.organization.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    members = [_member_read(membership, user) for membership, user in rows]
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return members, meta


def _member_read(membership: OrganizationMembership, user: User) -> OrganizationMemberRead:
    return OrganizationMemberRead(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=membership.role,
        reports_to_user_id=membership.reports_to_user_id,
        created_at=membership.created_at,
    )


def is_manager_of(
    session: Session,
    *,
    organization_id: UUID,
    manager_user_id: UUID,
    subject_user_id: UUID,
) -> bool:
    """Whether `manager_user_id` is anywhere above `subject_user_id` in the reporting tree."""
    if manager_user_id == subject_user_id:
        return False
    lines = organizations_repository.reporting_lines(session, organization_id)
    return manager_user_id in _ancestors(lines, subject_user_id)


def subordinate_user_ids(
    session: Session,
    *,
    organization_id: UUID,
    manager_user_id: UUID,
) -> set[UUID]:
    """Everyone below `manager_user_id` in the reporting tree, at any depth."""
    lines = organizations_repository.reporting_lines(session, organization_id)
    return {
        user_id
        for user_id in lines
        if user_id != manager_user_id and manager_user_id in _ancestors(lines, user_id)
    }


def _ancestors(lines: dict[UUID, UUID | None], user_id: UUID) -> set[UUID]:
    """Walk up the reporting chain. The seen set also stops a pre-existing cycle."""
    seen: set[UUID] = set()
    current = lines.get(user_id)
    while current is not None and current not in seen:
        seen.add(current)
        current = lines.get(current)
    return seen


def update_member(
    session: Session,
    context: OrganizationContext,
    user_id: UUID,
    payload: OrganizationMemberUpdate,
    redis: RedisClient,
) -> OrganizationMemberRead:
    if context.role not in _MANAGE_MEMBER_ROLES:
        raise ForbiddenError("You do not have permission to manage members")

    membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=context.organization.id,
        user_id=user_id,
    )
    if membership is None:
        raise ResourceNotFoundError("Member not found")

    if "reports_to_user_id" in payload.model_fields_set:
        _set_reporting_line(session, context.organization.id, membership, payload)

    session.add(membership)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(membership)
    user = users_repository.get_by_id(session, user_id)
    if user is None:
        raise ResourceNotFoundError("Member not found")
    return _member_read(membership, user)


def _set_reporting_line(
    session: Session,
    organization_id: UUID,
    membership: OrganizationMembership,
    payload: OrganizationMemberUpdate,
) -> None:
    manager_user_id = payload.reports_to_user_id
    if manager_user_id is None:
        membership.reports_to_user_id = None
        return

    if manager_user_id == membership.user_id:
        raise ValidationError("A member cannot report to themselves")

    manager_membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=organization_id,
        user_id=manager_user_id,
    )
    if manager_membership is None:
        raise ValidationError("reports_to_user_id must be a member of this organization")

    lines = organizations_repository.reporting_lines(session, organization_id)
    lines[membership.user_id] = manager_user_id
    if membership.user_id in _ancestors(lines, membership.user_id):
        raise ValidationError("Reporting cycle detected")

    membership.reports_to_user_id = manager_user_id


def get_hierarchy(session: Session, context: OrganizationContext) -> list[HierarchyNode]:
    """Return the reporting tree. Members whose manager is missing are treated as roots."""
    rows = organizations_repository.list_all_members(session, context.organization.id)
    nodes = {
        user.id: HierarchyNode(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=membership.role,
        )
        for membership, user in rows
    }

    lines = {membership.user_id: membership.reports_to_user_id for membership, _ in rows}
    roots: list[HierarchyNode] = []
    for membership, user in rows:
        node = nodes[user.id]
        parent_id = membership.reports_to_user_id
        parent = nodes.get(parent_id) if parent_id is not None else None
        # A member inside a cycle has no reachable root, so surface them at the top level.
        if parent is None or user.id in _ancestors(lines, user.id):
            roots.append(node)
        else:
            parent.reports.append(node)
    return roots


def create_member(
    session: Session,
    context: OrganizationContext,
    payload: OrganizationMemberCreate,
    redis: RedisClient,
) -> OrganizationMemberRead:
    if context.role not in _MANAGE_MEMBER_ROLES:
        raise ForbiddenError("You do not have permission to manage members")

    email = _normalize_email(str(payload.email))
    if users_repository.get_by_email(session, email) is not None:
        raise ResourceAlreadyExistsError("A user with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        is_active=True,
    )
    users_repository.add(session, user)
    session.flush()

    membership = OrganizationMembership(
        organization_id=context.organization.id,
        user_id=user.id,
        role=payload.role,
    )
    organizations_repository.add_membership(session, membership)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceAlreadyExistsError("A user with this email already exists") from exc

    invalidate_dashboard(redis, context.organization.id)
    session.refresh(user)
    session.refresh(membership)
    return _member_read(membership, user)
