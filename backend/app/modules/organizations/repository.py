"""Persistence helpers for organizations and memberships."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Organization, OrganizationMembership


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
