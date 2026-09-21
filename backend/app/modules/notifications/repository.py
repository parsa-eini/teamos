"""Persistence helpers for notifications. Queries are scoped to the recipient user."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification


def get_by_id_for_user(
    session: Session, notification_id: UUID, user_id: UUID
) -> Notification | None:
    return session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )


def list_for_user(
    session: Session,
    user_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[Notification], int]:
    filters = [Notification.user_id == user_id]
    total = session.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0
    notifications = list(
        session.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return notifications, total


def add(session: Session, notification: Notification) -> Notification:
    session.add(notification)
    return notification
