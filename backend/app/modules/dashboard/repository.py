"""Organization-scoped aggregate queries for the dashboard."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.dashboard.schemas import ActivityItem, GoalSummaryItem, RecentMeeting
from app.modules.goals.models import Goal, GoalStatus
from app.modules.meetings.models import Meeting, MeetingStatus, MeetingType
from app.modules.organizations.models import OrganizationMembership
from app.modules.projects.models import Project, ProjectStatus
from app.modules.tasks.models import Task, TaskStatus
from app.modules.users.models import User

_OPEN_TASK_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
_GOAL_LIST_LIMIT = 10
_RECENT_MEETING_LIMIT = 5
_ACTIVITY_LIMIT = 10
_MEETING_LABELS = {
    MeetingType.CHECK_IN: "check-in",
    MeetingType.ONE_ON_ONE: "one-on-one",
    MeetingType.PERFORMANCE_REVIEW: "performance review",
}


def count_members(session: Session, organization_id: UUID) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
        )
        or 0
    )


def count_active_projects(session: Session, organization_id: UUID) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.organization_id == organization_id,
                Project.status == ProjectStatus.ACTIVE,
            )
        )
        or 0
    )


def count_open_tasks(session: Session, organization_id: UUID) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.organization_id == organization_id,
                Task.status.in_(_OPEN_TASK_STATUSES),
            )
        )
        or 0
    )


def count_overdue_tasks(session: Session, organization_id: UUID, today: date) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.organization_id == organization_id,
                Task.status.in_(_OPEN_TASK_STATUSES),
                Task.due_date.is_not(None),
                Task.due_date < today,
            )
        )
        or 0
    )


def goal_summary(session: Session, organization_id: UUID) -> tuple[int, list[GoalSummaryItem]]:
    total = (
        session.scalar(
            select(func.count()).select_from(Goal).where(Goal.organization_id == organization_id)
        )
        or 0
    )
    goals = list(
        session.scalars(
            select(Goal)
            .where(
                Goal.organization_id == organization_id,
                Goal.status != GoalStatus.CANCELLED,
            )
            .order_by(Goal.updated_at.desc(), Goal.id.desc())
            .limit(_GOAL_LIST_LIMIT)
        ).all()
    )
    items = [
        GoalSummaryItem(id=goal.id, title=goal.title, progress=goal.progress, status=goal.status)
        for goal in goals
    ]
    return total, items


def recent_meetings(session: Session, organization_id: UUID) -> list[RecentMeeting]:
    rows = list(
        session.scalars(
            select(Meeting)
            .where(Meeting.organization_id == organization_id)
            .order_by(Meeting.updated_at.desc(), Meeting.id.desc())
            .limit(_RECENT_MEETING_LIMIT)
        ).all()
    )
    return [
        RecentMeeting(
            id=row.id,
            member_id=row.member_id,
            type=row.type,
            status=row.status,
            scheduled_on=row.scheduled_on,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _display_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def recent_activity(session: Session, organization_id: UUID) -> list[ActivityItem]:
    events: list[ActivityItem] = []

    projects = session.execute(
        select(Project, User)
        .join(User, User.id == Project.created_by)
        .where(Project.organization_id == organization_id)
        .order_by(Project.created_at.desc())
        .limit(_ACTIVITY_LIMIT)
    ).all()
    for project, user in projects:
        events.append(
            ActivityItem(
                type="project_created",
                message=f"{_display_name(user)} created a new project",
                occurred_at=project.created_at,
            )
        )

    tasks = session.execute(
        select(Task, User)
        .join(User, User.id == Task.created_by)
        .where(Task.organization_id == organization_id, Task.status == TaskStatus.DONE)
        .order_by(Task.updated_at.desc())
        .limit(_ACTIVITY_LIMIT)
    ).all()
    for task, user in tasks:
        events.append(
            ActivityItem(
                type="task_completed",
                message=f'{_display_name(user)} completed "{task.title}"',
                occurred_at=task.updated_at,
            )
        )

    meetings = session.execute(
        select(Meeting, User)
        .join(User, User.id == Meeting.member_id)
        .where(
            Meeting.organization_id == organization_id,
            Meeting.status.in_((MeetingStatus.SUBMITTED, MeetingStatus.REVIEWED)),
        )
        .order_by(Meeting.updated_at.desc())
        .limit(_ACTIVITY_LIMIT)
    ).all()
    for meeting, user in meetings:
        events.append(
            ActivityItem(
                type="meeting_submitted",
                message=f"{_display_name(user)} submitted a {_MEETING_LABELS[meeting.type]}",
                occurred_at=meeting.updated_at,
            )
        )

    events.sort(key=lambda item: item.occurred_at, reverse=True)
    return events[:_ACTIVITY_LIMIT]


def utc_today() -> date:
    return datetime.now(UTC).date()
