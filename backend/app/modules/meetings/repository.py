"""Persistence helpers for meetings. Every query is scoped to an organization."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.meetings.models import Meeting, MeetingType


def get_by_id(session: Session, meeting_id: UUID, organization_id: UUID) -> Meeting | None:
    return session.scalar(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.organization_id == organization_id,
        )
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    participant_user_id: UUID | None,
    meeting_type: MeetingType | None,
    offset: int,
    limit: int,
) -> tuple[list[Meeting], int]:
    filters = [Meeting.organization_id == organization_id]
    if meeting_type is not None:
        filters.append(Meeting.type == meeting_type)
    stmt = select(Meeting).where(*filters)
    count_stmt = select(func.count()).select_from(Meeting).where(*filters)

    if participant_user_id is not None:
        visibility = or_(
            Meeting.manager_id == participant_user_id,
            Meeting.member_id == participant_user_id,
        )
        stmt = stmt.where(visibility)
        count_stmt = count_stmt.where(visibility)

    total = session.scalar(count_stmt) or 0
    meetings = list(
        session.scalars(
            stmt.order_by(Meeting.created_at.desc(), Meeting.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return meetings, total


def add(session: Session, meeting: Meeting) -> Meeting:
    session.add(meeting)
    return meeting
