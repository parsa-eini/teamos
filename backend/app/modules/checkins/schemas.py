"""Check-in API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.checkins.models import CheckInStatus


class CheckInCreate(BaseModel):
    member_id: UUID
    manager_id: UUID | None = None
    period_start: date
    period_end: date
    wins: str | None = Field(default=None, max_length=5000)
    challenges: str | None = Field(default=None, max_length=5000)
    next_steps: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def period_must_be_ordered(self) -> "CheckInCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        return self


class CheckInUpdate(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    status: CheckInStatus | None = None
    wins: str | None = Field(default=None, max_length=5000)
    challenges: str | None = Field(default=None, max_length=5000)
    next_steps: str | None = Field(default=None, max_length=5000)
    manager_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def period_must_be_ordered(self) -> "CheckInUpdate":
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end must not be before period_start")
        return self


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    manager_id: UUID
    member_id: UUID
    period_start: date
    period_end: date
    status: CheckInStatus
    wins: str | None
    challenges: str | None
    next_steps: str | None
    manager_notes: str | None
    created_at: datetime
    updated_at: datetime
