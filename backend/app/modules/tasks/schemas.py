"""Task API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.tasks.models import TaskPriority, TaskStatus

MAX_TASK_ASSIGNEES = 25


def _require_non_blank_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _deduplicate_assignees(value: list[UUID]) -> list[UUID]:
    """Drop repeated ids so a task cannot list the same person twice."""
    unique = list(dict.fromkeys(value))
    if len(unique) > MAX_TASK_ASSIGNEES:
        raise ValueError(f"must not contain more than {MAX_TASK_ASSIGNEES} assignees")
    return unique


class TaskCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_ids: list[UUID] = Field(default_factory=list)
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        return _require_non_blank_title(value)

    @field_validator("assignee_ids")
    @classmethod
    def assignees_must_be_unique(cls, value: list[UUID]) -> list[UUID]:
        return _deduplicate_assignees(value)


class TaskUpdate(BaseModel):
    project_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_ids: list[UUID] | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_blank_title(value)

    @field_validator("assignee_ids")
    @classmethod
    def assignees_must_be_unique(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is None:
            return value
        return _deduplicate_assignees(value)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_ids: list[UUID]
    due_date: date | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
