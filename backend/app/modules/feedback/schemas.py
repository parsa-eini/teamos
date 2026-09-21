"""Feedback API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.feedback.models import FeedbackSentiment


def _require_non_blank_body(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class FeedbackCreate(BaseModel):
    subject_id: UUID
    sentiment: FeedbackSentiment
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def body_must_not_be_blank(cls, value: str) -> str:
        return _require_non_blank_body(value)


class FeedbackUpdate(BaseModel):
    sentiment: FeedbackSentiment | None = None
    body: str | None = Field(default=None, min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def body_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_non_blank_body(value)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_id: UUID
    author_id: UUID
    sentiment: FeedbackSentiment
    body: str
    created_at: datetime
    updated_at: datetime
