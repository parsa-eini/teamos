"""Meeting use cases. Organization id is taken from membership context, never from the client.

Workflow: DRAFT → SUBMITTED → REVIEWED. Status cannot skip or reverse. This holds for every
meeting type; a performance review moves through the same states as a weekly check-in.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.meetings import repository as meetings_repository
from app.modules.meetings.models import Meeting, MeetingStatus, MeetingType
from app.modules.meetings.schemas import MeetingCreate, MeetingRead, MeetingUpdate
from app.modules.notifications.models import NotificationType
from app.modules.notifications.service import add_notification
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationMembership, OrganizationRole
from app.modules.users import repository as users_repository

_VIEW_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}
_CONDUCT_ROLES = {OrganizationRole.OWNER, OrganizationRole.MANAGER}
_ALLOWED_TRANSITIONS: dict[MeetingStatus, set[MeetingStatus]] = {
    MeetingStatus.DRAFT: {MeetingStatus.SUBMITTED},
    MeetingStatus.SUBMITTED: {MeetingStatus.REVIEWED},
    MeetingStatus.REVIEWED: set(),
}
_MEMBER_CONTENT_FIELDS = {"wins", "challenges", "next_steps"}
_SCHEDULING_FIELDS = {"type", "scheduled_on"}

_TYPE_LABELS = {
    MeetingType.CHECK_IN: "check-in",
    MeetingType.ONE_ON_ONE: "one-on-one",
    MeetingType.PERFORMANCE_REVIEW: "performance review",
}


def _label(meeting_type: MeetingType) -> str:
    return _TYPE_LABELS[meeting_type]


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


def _can_view(context: OrganizationContext, meeting: Meeting) -> bool:
    if context.role in _VIEW_ALL_ROLES:
        return True
    return meeting.manager_id == context.user.id or meeting.member_id == context.user.id


def _is_manager_participant(context: OrganizationContext, meeting: Meeting) -> bool:
    return context.role == OrganizationRole.OWNER or meeting.manager_id == context.user.id


def _is_member_participant(context: OrganizationContext, meeting: Meeting) -> bool:
    return meeting.member_id == context.user.id


def _get_meeting_or_404(session: Session, meeting_id: UUID, organization_id: UUID) -> Meeting:
    meeting = meetings_repository.get_by_id(session, meeting_id, organization_id)
    if meeting is None:
        raise ResourceNotFoundError("Meeting not found")
    return meeting


def list_meetings(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
    *,
    meeting_type: MeetingType | None = None,
) -> tuple[list[MeetingRead], PaginationMeta]:
    participant_user_id = None if context.role in _VIEW_ALL_ROLES else context.user.id
    meetings, total = meetings_repository.list_for_organization(
        session,
        context.organization.id,
        participant_user_id=participant_user_id,
        meeting_type=meeting_type,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [MeetingRead.model_validate(meeting) for meeting in meetings], meta


def create_meeting(
    session: Session,
    context: OrganizationContext,
    payload: MeetingCreate,
    redis: RedisClient,
) -> Meeting:
    if context.role not in _CONDUCT_ROLES:
        raise ForbiddenError("You do not have permission to create meetings")

    manager_id = payload.manager_id or context.user.id
    if context.role == OrganizationRole.MANAGER and manager_id != context.user.id:
        raise ForbiddenError("Managers can only create meetings they conduct")

    manager_membership = _org_membership(session, context.organization.id, manager_id)
    if manager_membership.role not in _CONDUCT_ROLES:
        raise ForbiddenError("manager_id must be an owner or manager")
    _org_membership(session, context.organization.id, payload.member_id)
    if manager_id == payload.member_id:
        raise ValidationError("manager_id and member_id must be different")

    meeting = Meeting(
        organization_id=context.organization.id,
        manager_id=manager_id,
        member_id=payload.member_id,
        type=payload.type,
        scheduled_on=payload.scheduled_on,
        status=MeetingStatus.DRAFT,
        wins=payload.wins,
        challenges=payload.challenges,
        next_steps=payload.next_steps,
    )
    meetings_repository.add(session, meeting)
    add_notification(
        session,
        user_id=payload.member_id,
        actor_id=context.user.id,
        notification_type=NotificationType.MEETING_CREATED,
        title="Meeting scheduled",
        message=f"A {_label(payload.type)} was scheduled for you",
    )
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(meeting)
    return meeting


def get_meeting(session: Session, context: OrganizationContext, meeting_id: UUID) -> Meeting:
    meeting = _get_meeting_or_404(session, meeting_id, context.organization.id)
    if not _can_view(context, meeting):
        raise ForbiddenError()
    return meeting


def update_meeting(
    session: Session,
    context: OrganizationContext,
    meeting_id: UUID,
    payload: MeetingUpdate,
    redis: RedisClient,
) -> Meeting:
    meeting = _get_meeting_or_404(session, meeting_id, context.organization.id)
    if not _can_view(context, meeting):
        raise ForbiddenError()

    previous_status = meeting.status
    fields = payload.model_fields_set
    if meeting.status == MeetingStatus.REVIEWED:
        raise ValidationError("Reviewed meetings cannot be modified")

    if fields & _SCHEDULING_FIELDS:
        if meeting.status != MeetingStatus.DRAFT or not _is_manager_participant(context, meeting):
            raise ForbiddenError()
        if "type" in fields:
            if payload.type is None:
                raise ValidationError("type is required")
            meeting.type = payload.type
        if "scheduled_on" in fields:
            if payload.scheduled_on is None:
                raise ValidationError("scheduled_on is required")
            meeting.scheduled_on = payload.scheduled_on

    content_fields = fields & _MEMBER_CONTENT_FIELDS
    if content_fields:
        if meeting.status != MeetingStatus.DRAFT:
            raise ForbiddenError()
        if not (
            _is_member_participant(context, meeting) or _is_manager_participant(context, meeting)
        ):
            raise ForbiddenError()
        if "wins" in fields:
            meeting.wins = payload.wins
        if "challenges" in fields:
            meeting.challenges = payload.challenges
        if "next_steps" in fields:
            meeting.next_steps = payload.next_steps

    if "manager_notes" in fields:
        if meeting.status != MeetingStatus.SUBMITTED or not _is_manager_participant(
            context, meeting
        ):
            raise ForbiddenError()
        meeting.manager_notes = payload.manager_notes

    if payload.status is not None and payload.status != meeting.status:
        allowed = _ALLOWED_TRANSITIONS[meeting.status]
        if payload.status not in allowed:
            raise ValidationError("Invalid meeting status transition")
        if payload.status == MeetingStatus.SUBMITTED:
            if not (
                _is_member_participant(context, meeting) or context.role == OrganizationRole.OWNER
            ):
                raise ForbiddenError("Only the member can submit this meeting")
        elif payload.status == MeetingStatus.REVIEWED and not _is_manager_participant(
            context, meeting
        ):
            raise ForbiddenError("Only the manager can review this meeting")
        meeting.status = payload.status

    if meeting.status == MeetingStatus.SUBMITTED and previous_status != MeetingStatus.SUBMITTED:
        add_notification(
            session,
            user_id=meeting.manager_id,
            actor_id=context.user.id,
            notification_type=NotificationType.MEETING_SUBMITTED,
            title="Meeting submitted",
            message=f"A {_label(meeting.type)} was submitted for review",
        )
    elif meeting.status == MeetingStatus.REVIEWED and previous_status != MeetingStatus.REVIEWED:
        add_notification(
            session,
            user_id=meeting.member_id,
            actor_id=context.user.id,
            notification_type=NotificationType.MEETING_REVIEWED,
            title="Meeting reviewed",
            message=f"Your {_label(meeting.type)} was reviewed",
        )

    session.add(meeting)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(meeting)
    return meeting
