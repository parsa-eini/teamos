"""Organization context derived from the authenticated user's membership."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.exceptions import OrganizationAccessDeniedError, ResourceNotFoundError
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.models import Organization, OrganizationMembership, OrganizationRole
from app.modules.users.models import User


@dataclass(frozen=True)
class OrganizationContext:
    user: User
    organization: Organization
    membership: OrganizationMembership

    @property
    def role(self) -> OrganizationRole:
        return self.membership.role


def get_organization_context(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> OrganizationContext:
    """Resolve the current organization from membership. Never from a client-supplied id."""
    membership = organizations_repository.get_membership_for_user(session, user.id)
    if membership is None:
        raise OrganizationAccessDeniedError()

    organization = organizations_repository.get_organization_by_id(
        session,
        membership.organization_id,
    )
    if organization is None:
        raise ResourceNotFoundError("Organization not found")

    return OrganizationContext(user=user, organization=organization, membership=membership)
