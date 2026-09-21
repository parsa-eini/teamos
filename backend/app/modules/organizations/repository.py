"""Persistence helpers for organizations and memberships."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Organization, OrganizationMembership
from app.modules.users.models import User


def get_organization_by_id(session: Session, organization_id: UUID) -> Organization | None:
    return session.get(Organization, organization_id)


def get_organization_by_slug(session: Session, slug: str) -> Organization | None:
    return session.scalar(select(Organization).where(Organization.slug == slug))


def get_membership_for_user(session: Session, user_id: UUID) -> OrganizationMembership | None:
    """Return the user's organization membership.

    Phase 1 does not have an organization switcher. If a user has more than one membership, the
    earliest one is used so the result is deterministic.
    """
    return session.scalar(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id)
        .order_by(OrganizationMembership.created_at.asc(), OrganizationMembership.id.asc())
        .limit(1)
    )


def get_membership_in_organization(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> OrganizationMembership | None:
    return session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )


def add_organization(session: Session, organization: Organization) -> Organization:
    session.add(organization)
    return organization


def add_membership(
    session: Session,
    membership: OrganizationMembership,
) -> OrganizationMembership:
    session.add(membership)
    return membership


def reporting_lines(session: Session, organization_id: UUID) -> dict[UUID, UUID | None]:
    """Map every member of the organization to the person they report to."""
    rows = session.execute(
        select(OrganizationMembership.user_id, OrganizationMembership.reports_to_user_id).where(
            OrganizationMembership.organization_id == organization_id
        )
    ).all()
    return {row[0]: row[1] for row in rows}


def list_all_members(
    session: Session,
    organization_id: UUID,
) -> list[tuple[OrganizationMembership, User]]:
    """Return every membership in the organization, for whole-tree operations."""
    rows = session.execute(
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(User.last_name.asc(), User.first_name.asc(), User.email.asc())
    ).all()
    return [(row[0], row[1]) for row in rows]


def list_members(
    session: Session,
    organization_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[OrganizationMembership, User]], int]:
    filters = [OrganizationMembership.organization_id == organization_id]
    stmt = (
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(*filters)
    )
    total = (
        session.scalar(
            select(func.count()).select_from(OrganizationMembership).where(*filters)
        )
        or 0
    )
    rows = list(
        session.execute(
            stmt.order_by(User.last_name.asc(), User.first_name.asc(), User.email.asc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [(row[0], row[1]) for row in rows], total
