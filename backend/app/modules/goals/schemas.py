"""Goal API schemas. Progress is validated here (0-100) and again by a database check."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.goals.models import GoalStatus


def _require_non_blank_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    team_id: UUID | None = None
    user_id: UUID | None = None
    status: GoalStatus = GoalStatus.NOT_STARTED
    progress: int = Field(default=0, ge=0, le=100)
    start_date: date | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        return _require_non_blank_title(value)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    team_id: UUID | None = None
    user_id: UUID | None = None
    status: GoalStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    start_date: date | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_blank_title(value)


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    team_id: UUID | None
    user_id: UUID | None
    status: GoalStatus
    progress: int
    start_date: date | None
    due_date: date | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
