"""Task-derived goal progress.

A goal's progress comes from its linked tasks: the share of countable linked tasks that are
DONE. Cancelled tasks are excluded from both sides of the ratio, since a cancelled task is
neither outstanding work nor an achievement.

A goal with no countable linked tasks keeps whatever progress was set by hand, so goals that
have not been broken down into tasks still work.

This module imports task models only, never the tasks service, so the tasks service can call
into it without a circular import.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modules.goals.models import Goal, GoalTask
from app.modules.tasks.models import Task, TaskStatus

_COUNTABLE_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE)


def task_counts_for_goals(
    session: Session,
    goal_ids: Sequence[UUID],
) -> dict[UUID, tuple[int, int]]:
    """Return {goal_id: (done, countable)} for many goals in one query."""
    if not goal_ids:
        return {}
    done_case = case((Task.status == TaskStatus.DONE, 1), else_=0)
    rows = session.execute(
        select(GoalTask.goal_id, func.sum(done_case), func.count())
        .join(Task, Task.id == GoalTask.task_id)
        .where(GoalTask.goal_id.in_(goal_ids), Task.status.in_(_COUNTABLE_STATUSES))
        .group_by(GoalTask.goal_id)
    ).all()
    counts: dict[UUID, tuple[int, int]] = dict.fromkeys(goal_ids, (0, 0))
    for goal_id, done, countable in rows:
        counts[goal_id] = (int(done or 0), int(countable or 0))
    return counts


def task_counts(session: Session, goal_id: UUID) -> tuple[int, int]:
    """Return (done, countable) linked task counts for one goal."""
    return task_counts_for_goals(session, [goal_id])[goal_id]


def derived_progress(done: int, countable: int) -> int | None:
    """Progress implied by task counts, or None when the goal has no countable tasks."""
    if countable == 0:
        return None
    return round(100 * done / countable)


def recalculate_goal_progress(session: Session, goal: Goal) -> None:
    """Recompute and store progress for one goal. Does not commit."""
    progress = derived_progress(*task_counts(session, goal.id))
    if progress is None:
        return
    goal.progress = progress
    session.add(goal)


def recalculate_goals(session: Session, goal_ids: Sequence[UUID]) -> None:
    """Recompute progress for several goals. Does not commit; the caller owns the transaction."""
    if not goal_ids:
        return
    counts = task_counts_for_goals(session, goal_ids)
    for goal in session.scalars(select(Goal).where(Goal.id.in_(goal_ids))).all():
        progress = derived_progress(*counts[goal.id])
        if progress is not None:
            goal.progress = progress
            session.add(goal)


def recalculate_goals_for_task(session: Session, task_id: UUID) -> None:
    """Recompute every goal linked to a task. Call after the task's status changes."""
    goal_ids = list(
        session.scalars(select(GoalTask.goal_id).where(GoalTask.task_id == task_id)).all()
    )
    recalculate_goals(session, goal_ids)
