"""Persistence helpers for feedback. Every query is scoped to an organization."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.feedback.models import Feedback, FeedbackSentiment


def get_by_id(session: Session, feedback_id: UUID, organization_id: UUID) -> Feedback | None:
    return session.scalar(
        select(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.organization_id == organization_id,
        )
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    subject_id: UUID | None,
    sentiment: FeedbackSentiment | None,
    author_id: UUID | None,
    exclude_subject_id: UUID,
    visible_subject_ids: Sequence[UUID] | None,
    offset: int,
    limit: int,
) -> tuple[list[Feedback], int]:
    """List feedback.

    `visible_subject_ids` is None for readers who may see every subject. Otherwise the reader sees
    feedback they wrote plus feedback about the listed subjects. Feedback about
    `exclude_subject_id` is always hidden, so nobody reads feedback written about them.
    """
    filters = [
        Feedback.organization_id == organization_id,
        Feedback.subject_id != exclude_subject_id,
    ]
    if subject_id is not None:
        filters.append(Feedback.subject_id == subject_id)
    if sentiment is not None:
        filters.append(Feedback.sentiment == sentiment)

    if visible_subject_ids is not None:
        visibility = Feedback.author_id == author_id
        if visible_subject_ids:
            visibility = or_(visibility, Feedback.subject_id.in_(visible_subject_ids))
        filters.append(visibility)

    stmt = select(Feedback).where(*filters)
    total = session.scalar(select(func.count()).select_from(Feedback).where(*filters)) or 0
    ordered = stmt.order_by(Feedback.created_at.desc(), Feedback.id.desc())
    rows = list(session.scalars(ordered.offset(offset).limit(limit)).all())
    return rows, total


def add(session: Session, feedback: Feedback) -> Feedback:
    session.add(feedback)
    return feedback


def delete(session: Session, feedback: Feedback) -> None:
    session.delete(feedback)
