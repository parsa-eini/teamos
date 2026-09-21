"""Meeting API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.meetings.models import MeetingStatus, MeetingType


class MeetingCreate(BaseModel):
    member_id: UUID
    manager_id: UUID | None = None
    type: MeetingType = MeetingType.CHECK_IN
    scheduled_on: date
    wins: str | None = Field(default=None, max_length=5000)
    challenges: str | None = Field(default=None, max_length=5000)
    next_steps: str | None = Field(default=None, max_length=5000)


class MeetingUpdate(BaseModel):
    type: MeetingType | None = None
    scheduled_on: date | None = None
    status: MeetingStatus | None = None
    wins: str | None = Field(default=None, max_length=5000)
    challenges: str | None = Field(default=None, max_length=5000)
    next_steps: str | None = Field(default=None, max_length=5000)
    manager_notes: str | None = Field(default=None, max_length=5000)


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    manager_id: UUID
    member_id: UUID
    type: MeetingType
    scheduled_on: date
    status: MeetingStatus
    wins: str | None
    challenges: str | None
    next_steps: str | None
    manager_notes: str | None
    created_at: datetime
    updated_at: datetime
