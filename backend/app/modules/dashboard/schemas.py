"""Dashboard API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.goals.models import GoalStatus
from app.modules.meetings.models import MeetingStatus, MeetingType


class GoalSummaryItem(BaseModel):
    id: UUID
    title: str
    progress: int
    status: GoalStatus


class GoalSummary(BaseModel):
    total: int
    items: list[GoalSummaryItem]


class RecentMeeting(BaseModel):
    id: UUID
    member_id: UUID
    type: MeetingType
    status: MeetingStatus
    scheduled_on: date
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
    recent_meetings: list[RecentMeeting]
    recent_activity: list[ActivityItem]
