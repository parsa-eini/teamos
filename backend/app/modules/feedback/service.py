"""Feedback use cases.

Any member may write feedback about a colleague. Only the author may change or remove it.
Reads are limited to the author, the subject's management line, and owners and admins. The
subject never sees feedback written about them, whatever their role.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.modules.feedback import repository as feedback_repository
from app.modules.feedback.models import Feedback, FeedbackSentiment
from app.modules.feedback.schemas import FeedbackCreate, FeedbackRead, FeedbackUpdate
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations import service as organizations_service
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole

_VIEW_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _require_membership(session: Session, organization_id: UUID, user_id: UUID) -> None:
    membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=organization_id,
        user_id=user_id,
    )
    if membership is None:
        raise ResourceNotFoundError("User not found in this organization")


def _can_view(session: Session, context: OrganizationContext, feedback: Feedback) -> bool:
    if feedback.subject_id == context.user.id:
        return False
    if feedback.author_id == context.user.id or context.role in _VIEW_ALL_ROLES:
        return True
    return organizations_service.is_manager_of(
        session,
        organization_id=context.organization.id,
        manager_user_id=context.user.id,
        subject_user_id=feedback.subject_id,
    )


def list_feedback(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
    *,
    subject_id: UUID | None = None,
    sentiment: FeedbackSentiment | None = None,
) -> tuple[list[FeedbackRead], PaginationMeta]:
    if subject_id == context.user.id:
        # The subject never reads feedback about themselves.
        meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=0)
        return [], meta

    visible_subject_ids: set[UUID] | None = None
    if context.role not in _VIEW_ALL_ROLES:
        visible_subject_ids = organizations_service.subordinate_user_ids(
            session,
            organization_id=context.organization.id,
            manager_user_id=context.user.id,
        )
        visible_subject_ids.discard(context.user.id)

    rows, total = feedback_repository.list_for_organization(
        session,
        context.organization.id,
        subject_id=subject_id,
        sentiment=sentiment,
        author_id=context.user.id,
        exclude_subject_id=context.user.id,
        visible_subject_ids=None if visible_subject_ids is None else sorted(visible_subject_ids),
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [FeedbackRead.model_validate(row) for row in rows], meta


def create_feedback(
    session: Session,
    context: OrganizationContext,
    payload: FeedbackCreate,
) -> Feedback:
    if payload.subject_id == context.user.id:
        raise ValidationError("You cannot write feedback about yourself")
    _require_membership(session, context.organization.id, payload.subject_id)

    feedback = Feedback(
        organization_id=context.organization.id,
        subject_id=payload.subject_id,
        author_id=context.user.id,
        sentiment=payload.sentiment,
        body=payload.body,
    )
    feedback_repository.add(session, feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def _get_feedback_or_404(session: Session, feedback_id: UUID, organization_id: UUID) -> Feedback:
    feedback = feedback_repository.get_by_id(session, feedback_id, organization_id)
    if feedback is None:
        raise ResourceNotFoundError("Feedback not found")
    return feedback


def get_feedback(session: Session, context: OrganizationContext, feedback_id: UUID) -> Feedback:
    feedback = _get_feedback_or_404(session, feedback_id, context.organization.id)
    if not _can_view(session, context, feedback):
        # Hide existence from the subject and from unrelated members.
        raise ResourceNotFoundError("Feedback not found")
    return feedback


def update_feedback(
    session: Session,
    context: OrganizationContext,
    feedback_id: UUID,
    payload: FeedbackUpdate,
) -> Feedback:
    feedback = _get_feedback_or_404(session, feedback_id, context.organization.id)
    if feedback.author_id != context.user.id:
        if not _can_view(session, context, feedback):
            raise ResourceNotFoundError("Feedback not found")
        raise ForbiddenError("Only the author can change this feedback")

    if payload.sentiment is not None:
        feedback.sentiment = payload.sentiment
    if payload.body is not None:
        feedback.body = payload.body

    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def delete_feedback(session: Session, context: OrganizationContext, feedback_id: UUID) -> None:
    feedback = _get_feedback_or_404(session, feedback_id, context.organization.id)
    if feedback.author_id != context.user.id:
        if not _can_view(session, context, feedback):
            raise ResourceNotFoundError("Feedback not found")
        raise ForbiddenError("Only the author can delete this feedback")

    feedback_repository.delete(session, feedback)
    session.commit()
