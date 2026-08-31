"""Dashboard API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.checkins.models import CheckInStatus
from app.modules.goals.models import GoalStatus


class GoalSummaryItem(BaseModel):
    id: UUID
    title: str
    progress: int
    status: GoalStatus


class GoalSummary(BaseModel):
    total: int
    items: list[GoalSummaryItem]


class RecentCheckIn(BaseModel):
    id: UUID
    member_id: UUID
    status: CheckInStatus
    period_start: date
    period_end: date
    updated_at: datetime


class ActivityItem(BaseModel):
    type: str
    message: str
    occurred_at: datetime


class DashboardRead(BaseModel):
    member_count: int
    active_projects: int
    open_tasks: int
    overdue_tasks: int
    goal_summary: GoalSummary
    recent_checkins: list[RecentCheckIn]
    recent_activity: list[ActivityItem]
