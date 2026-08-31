"""Notification use cases. Recipients come from the authenticated user, never from the client."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.pagination import PaginationMeta, PaginationParams
from app.modules.notifications import repository as notifications_repository
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationRead
from app.modules.users.models import User


def add_notification(
    session: Session,
    *,
    user_id: UUID,
    actor_id: UUID,
    notification_type: str,
    title: str,
    message: str,
) -> Notification | None:
    """Queue a notification in the current transaction. Skips notifying the actor."""
    if user_id == actor_id:
        return None
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        is_read=False,
    )
    return notifications_repository.add(session, notification)


def list_notifications(
    session: Session,
    user: User,
    pagination: PaginationParams,
) -> tuple[list[NotificationRead], PaginationMeta]:
    notifications, total = notifications_repository.list_for_user(
        session,
        user.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [NotificationRead.model_validate(item) for item in notifications], meta


def mark_notification_read(
    session: Session,
    user: User,
    notification_id: UUID,
) -> Notification:
    notification = notifications_repository.get_by_id_for_user(session, notification_id, user.id)
    if notification is None:
        raise ResourceNotFoundError("Notification not found")
    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
