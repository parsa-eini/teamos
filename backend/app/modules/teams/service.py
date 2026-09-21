"""Team use cases. Organization id is taken from membership context, never from the client."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import (
    ForbiddenError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from app.common.pagination import PaginationMeta, PaginationParams
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole
from app.modules.teams import repository as teams_repository
from app.modules.teams.models import Team, TeamMembership
from app.modules.teams.schemas import TeamCreate, TeamMemberRead, TeamRead, TeamUpdate
from app.modules.users import repository as users_repository

_MANAGE_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _is_team_member(session: Session, team_id: UUID, user_id: UUID) -> bool:
    return teams_repository.get_membership(session, team_id, user_id) is not None


def _require_view(context: OrganizationContext, session: Session, team: Team) -> None:
    if context.role in _MANAGE_ALL_ROLES:
        return
    if _is_team_member(session, team.id, context.user.id):
        return
    raise ForbiddenError()


def _require_manage(context: OrganizationContext, session: Session, team: Team) -> None:
    if context.role in _MANAGE_ALL_ROLES:
        return
    if context.role == OrganizationRole.MANAGER and _is_team_member(
        session, team.id, context.user.id
    ):
        return
    raise ForbiddenError()


def _require_create(context: OrganizationContext) -> None:
    if context.role not in _MANAGE_ALL_ROLES:
        raise ForbiddenError("You do not have permission to create teams")


def _get_team_or_404(session: Session, team_id: UUID, organization_id: UUID) -> Team:
    team = teams_repository.get_by_id(session, team_id, organization_id)
    if team is None:
        raise ResourceNotFoundError("Team not found")
    return team


def list_teams(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
) -> tuple[list[TeamRead], PaginationMeta]:
    member_user_id = None if context.role in _MANAGE_ALL_ROLES else context.user.id
    teams, total = teams_repository.list_for_organization(
        session,
        context.organization.id,
        member_user_id=member_user_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [TeamRead.model_validate(team) for team in teams], meta


def create_team(session: Session, context: OrganizationContext, payload: TeamCreate) -> Team:
    _require_create(context)
    team = Team(
        organization_id=context.organization.id,
        name=payload.name,
        description=payload.description,
    )
    teams_repository.add(session, team)
    session.commit()
    session.refresh(team)
    return team


def get_team(session: Session, context: OrganizationContext, team_id: UUID) -> Team:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_view(context, session, team)
    return team


def update_team(
    session: Session,
    context: OrganizationContext,
    team_id: UUID,
    payload: TeamUpdate,
) -> Team:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_manage(context, session, team)

    if payload.name is not None:
        team.name = payload.name
    if "description" in payload.model_fields_set:
        team.description = payload.description

    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def delete_team(session: Session, context: OrganizationContext, team_id: UUID) -> None:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_manage(context, session, team)
    teams_repository.delete(session, team)
    session.commit()


def list_members(
    session: Session,
    context: OrganizationContext,
    team_id: UUID,
    pagination: PaginationParams,
) -> tuple[list[TeamMemberRead], PaginationMeta]:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_view(context, session, team)
    rows, total = teams_repository.list_members(
        session,
        team.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    members = [
        TeamMemberRead(
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=membership.created_at,
        )
        for membership, user in rows
    ]
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return members, meta


def add_member(
    session: Session,
    context: OrganizationContext,
    team_id: UUID,
    user_id: UUID,
) -> TeamMemberRead:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_manage(context, session, team)

    user = users_repository.get_by_id(session, user_id)
    org_membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=context.organization.id,
        user_id=user_id,
    )
    if user is None or org_membership is None:
        raise ResourceNotFoundError("User not found in this organization")

    membership = TeamMembership(team_id=team.id, user_id=user.id)
    teams_repository.add_membership(session, membership)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceAlreadyExistsError("User is already a member of this team") from exc

    session.refresh(membership)
    return TeamMemberRead(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=membership.created_at,
    )


def remove_member(
    session: Session,
    context: OrganizationContext,
    team_id: UUID,
    user_id: UUID,
) -> None:
    team = _get_team_or_404(session, team_id, context.organization.id)
    _require_manage(context, session, team)
    membership = teams_repository.get_membership(session, team.id, user_id)
    if membership is None:
        raise ResourceNotFoundError("Team member not found")
    teams_repository.delete_membership(session, membership)
    session.commit()
