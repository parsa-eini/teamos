"""Goal API schemas. Progress is validated here (0-100) and again by a database check."""


from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.goals.models import GoalStatus

MAX_GOAL_LINKS = 50


def _require_non_blank_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _deduplicate(value: list[UUID], *, label: str) -> list[UUID]:
    unique = list(dict.fromkeys(value))
    if len(unique) > MAX_GOAL_LINKS:
        raise ValueError(f"must not contain more than {MAX_GOAL_LINKS} {label}")
    return unique


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    team_ids: list[UUID] = Field(default_factory=list)
    owner_ids: list[UUID] = Field(default_factory=list)
    task_ids: list[UUID] = Field(default_factory=list)
    status: GoalStatus = GoalStatus.NOT_STARTED
    progress: int = Field(default=0, ge=0, le=100)
    start_date: date | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        return _require_non_blank_title(value)

    @field_validator("team_ids")
    @classmethod
    def teams_must_be_unique(cls, value: list[UUID]) -> list[UUID]:
        return _deduplicate(value, label="teams")

    @field_validator("owner_ids")
    @classmethod
    def owners_must_be_unique(cls, value: list[UUID]) -> list[UUID]:
        return _deduplicate(value, label="owners")

    @field_validator("task_ids")
    @classmethod
    def tasks_must_be_unique(cls, value: list[UUID]) -> list[UUID]:
        return _deduplicate(value, label="tasks")


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    team_ids: list[UUID] | None = None
    owner_ids: list[UUID] | None = None
    task_ids: list[UUID] | None = None
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

    @field_validator("team_ids")
    @classmethod
    def teams_must_be_unique(cls, value: list[UUID] | None) -> list[UUID] | None:
        return None if value is None else _deduplicate(value, label="teams")

    @field_validator("owner_ids")
    @classmethod
    def owners_must_be_unique(cls, value: list[UUID] | None) -> list[UUID] | None:
        return None if value is None else _deduplicate(value, label="owners")

    @field_validator("task_ids")
    @classmethod
    def tasks_must_be_unique(cls, value: list[UUID] | None) -> list[UUID] | None:
        return None if value is None else _deduplicate(value, label="tasks")


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    team_ids: list[UUID]
    owner_ids: list[UUID]
    task_ids: list[UUID]
    status: GoalStatus
    progress: int
    progress_is_derived: bool
    start_date: date | None
    due_date: date | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
