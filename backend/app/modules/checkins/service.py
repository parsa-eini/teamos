"""Check-in use cases. Organization id is taken from membership context, never from the client.

Workflow: DRAFT → SUBMITTED → REVIEWED. Status cannot skip or reverse.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.modules.checkins import repository as checkins_repository
from app.modules.checkins.models import CheckIn, CheckInStatus
from app.modules.checkins.schemas import CheckInCreate, CheckInRead, CheckInUpdate
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationMembership, OrganizationRole
from app.modules.users import repository as users_repository

_VIEW_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}
_CONDUCT_ROLES = {OrganizationRole.OWNER, OrganizationRole.MANAGER}
_ALLOWED_TRANSITIONS: dict[CheckInStatus, set[CheckInStatus]] = {
    CheckInStatus.DRAFT: {CheckInStatus.SUBMITTED},
    CheckInStatus.SUBMITTED: {CheckInStatus.REVIEWED},
    CheckInStatus.REVIEWED: set(),
}
_MEMBER_CONTENT_FIELDS = {"wins", "challenges", "next_steps"}
_PERIOD_FIELDS = {"period_start", "period_end"}


def _org_membership(
    session: Session, organization_id: UUID, user_id: UUID
) -> OrganizationMembership:
    user = users_repository.get_by_id(session, user_id)
    membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=organization_id,
        user_id=user_id,
    )
    if user is None or membership is None:
        raise ResourceNotFoundError("User not found in this organization")
    return membership


def _can_view(context: OrganizationContext, checkin: CheckIn) -> bool:
    if context.role in _VIEW_ALL_ROLES:
        return True
    return checkin.manager_id == context.user.id or checkin.member_id == context.user.id


def _is_manager_participant(context: OrganizationContext, checkin: CheckIn) -> bool:
    return context.role == OrganizationRole.OWNER or checkin.manager_id == context.user.id


def _is_member_participant(context: OrganizationContext, checkin: CheckIn) -> bool:
    return checkin.member_id == context.user.id


def _assert_period(period_start: date, period_end: date) -> None:
    if period_end < period_start:
        raise ValidationError("period_end must not be before period_start")


def _get_checkin_or_404(session: Session, checkin_id: UUID, organization_id: UUID) -> CheckIn:
    checkin = checkins_repository.get_by_id(session, checkin_id, organization_id)
    if checkin is None:
        raise ResourceNotFoundError("Check-in not found")
    return checkin


def list_checkins(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
) -> tuple[list[CheckInRead], PaginationMeta]:
    participant_user_id = None if context.role in _VIEW_ALL_ROLES else context.user.id
    checkins, total = checkins_repository.list_for_organization(
        session,
        context.organization.id,
        participant_user_id=participant_user_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [CheckInRead.model_validate(checkin) for checkin in checkins], meta


def create_checkin(
    session: Session,
    context: OrganizationContext,
    payload: CheckInCreate,
) -> CheckIn:
    if context.role not in _CONDUCT_ROLES:
        raise ForbiddenError("You do not have permission to create check-ins")

    manager_id = payload.manager_id or context.user.id
    if context.role == OrganizationRole.MANAGER and manager_id != context.user.id:
        raise ForbiddenError("Managers can only create check-ins they conduct")

    manager_membership = _org_membership(session, context.organization.id, manager_id)
    if manager_membership.role not in _CONDUCT_ROLES:
        raise ForbiddenError("manager_id must be an owner or manager")
    _org_membership(session, context.organization.id, payload.member_id)
    if manager_id == payload.member_id:
        raise ValidationError("manager_id and member_id must be different")

    checkin = CheckIn(
        organization_id=context.organization.id,
        manager_id=manager_id,
        member_id=payload.member_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=CheckInStatus.DRAFT,
        wins=payload.wins,
        challenges=payload.challenges,
        next_steps=payload.next_steps,
    )
    checkins_repository.add(session, checkin)
    session.commit()
    session.refresh(checkin)
    return checkin


def get_checkin(session: Session, context: OrganizationContext, checkin_id: UUID) -> CheckIn:
    checkin = _get_checkin_or_404(session, checkin_id, context.organization.id)
    if not _can_view(context, checkin):
        raise ForbiddenError()
    return checkin


def update_checkin(
    session: Session,
    context: OrganizationContext,
    checkin_id: UUID,
    payload: CheckInUpdate,
) -> CheckIn:
    checkin = _get_checkin_or_404(session, checkin_id, context.organization.id)
    if not _can_view(context, checkin):
        raise ForbiddenError()

    fields = payload.model_fields_set
    if checkin.status == CheckInStatus.REVIEWED:
        raise ValidationError("Reviewed check-ins cannot be modified")

    if fields & _PERIOD_FIELDS:
        if checkin.status != CheckInStatus.DRAFT or not _is_manager_participant(context, checkin):
            raise ForbiddenError()
        if "period_start" in fields:
            if payload.period_start is None:
                raise ValidationError("period_start is required")
            checkin.period_start = payload.period_start
        if "period_end" in fields:
            if payload.period_end is None:
                raise ValidationError("period_end is required")
            checkin.period_end = payload.period_end
        _assert_period(checkin.period_start, checkin.period_end)

    content_fields = fields & _MEMBER_CONTENT_FIELDS
    if content_fields:
        if checkin.status != CheckInStatus.DRAFT:
            raise ForbiddenError()
        if not (
            _is_member_participant(context, checkin) or _is_manager_participant(context, checkin)
        ):
            raise ForbiddenError()
        if "wins" in fields:
            checkin.wins = payload.wins
        if "challenges" in fields:
            checkin.challenges = payload.challenges
        if "next_steps" in fields:
            checkin.next_steps = payload.next_steps

    if "manager_notes" in fields:
        if checkin.status != CheckInStatus.SUBMITTED or not _is_manager_participant(
            context, checkin
        ):
            raise ForbiddenError()
        checkin.manager_notes = payload.manager_notes

    if payload.status is not None and payload.status != checkin.status:
        allowed = _ALLOWED_TRANSITIONS[checkin.status]
        if payload.status not in allowed:
            raise ValidationError("Invalid check-in status transition")
        if payload.status == CheckInStatus.SUBMITTED:
            if not (
                _is_member_participant(context, checkin) or context.role == OrganizationRole.OWNER
            ):
                raise ForbiddenError("Only the member can submit this check-in")
        elif payload.status == CheckInStatus.REVIEWED and not _is_manager_participant(
            context, checkin
        ):
            raise ForbiddenError("Only the manager can review this check-in")
        checkin.status = payload.status

    session.add(checkin)
    session.commit()
    session.refresh(checkin)
    return checkin
