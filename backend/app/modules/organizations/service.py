"""Organization use cases. Organization identity is never taken from the client."""

import re
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceAlreadyExistsError
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.models import Organization, OrganizationMembership, OrganizationRole
from app.modules.organizations.schemas import OrganizationUpdate

_SLUG_MAX_LENGTH = 100


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
