"""Persistence helpers for check-ins. Every query is scoped to an organization."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.checkins.models import CheckIn


def get_by_id(session: Session, checkin_id: UUID, organization_id: UUID) -> CheckIn | None:
    return session.scalar(
        select(CheckIn).where(
            CheckIn.id == checkin_id,
            CheckIn.organization_id == organization_id,
        )
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    participant_user_id: UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[CheckIn], int]:
    filters = [CheckIn.organization_id == organization_id]
    stmt = select(CheckIn).where(*filters)
    count_stmt = select(func.count()).select_from(CheckIn).where(*filters)

    if participant_user_id is not None:
        visibility = or_(
            CheckIn.manager_id == participant_user_id,
            CheckIn.member_id == participant_user_id,
        )
        stmt = stmt.where(visibility)
        count_stmt = count_stmt.where(visibility)

    total = session.scalar(count_stmt) or 0
    checkins = list(
        session.scalars(
            stmt.order_by(CheckIn.created_at.desc(), CheckIn.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return checkins, total


def add(session: Session, checkin: CheckIn) -> CheckIn:
    session.add(checkin)
    return checkin
