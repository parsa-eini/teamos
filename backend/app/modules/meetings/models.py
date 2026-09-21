"""Meeting ORM model.

A meeting is a recorded conversation between a manager and a member. The type distinguishes a
recurring check-in from a one-on-one or a performance review; the workflow is the same for all.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MeetingType(StrEnum):
    CHECK_IN = "CHECK_IN"
    ONE_ON_ONE = "ONE_ON_ONE"
    PERFORMANCE_REVIEW = "PERFORMANCE_REVIEW"


class MeetingStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'REVIEWED')",
            name="ck_meetings_status",
        ),
        CheckConstraint(
            "type IN ('CHECK_IN', 'ONE_ON_ONE', 'PERFORMANCE_REVIEW')",
            name="ck_meetings_type",
        ),
        CheckConstraint("manager_id <> member_id", name="ck_meetings_distinct_participants"),
        Index("ix_meetings_organization_id_updated_at", "organization_id", "updated_at"),
        Index(
            "ix_meetings_organization_id_type_scheduled_on",
            "organization_id",
            "type",
            "scheduled_on",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[MeetingType] = mapped_column(
        Enum(
            MeetingType,
            native_enum=False,
            length=20,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
    )
    scheduled_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(
            MeetingStatus,
            native_enum=False,
            length=20,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
    )
    wins: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
