"""generalize checkins into meetings with a type and a single scheduled date

Revision ID: 0012_meetings
Revises: 0011_goal_relations
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_meetings"
down_revision: str | Sequence[str] | None = "0011_goal_relations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPES = "('CHECK_IN', 'ONE_ON_ONE', 'PERFORMANCE_REVIEW')"


def upgrade() -> None:
    op.rename_table("checkins", "meetings")

    op.add_column(
        "meetings",
        sa.Column("type", sa.String(length=20), nullable=False, server_default="CHECK_IN"),
    )
    op.add_column("meetings", sa.Column("scheduled_on", sa.Date(), nullable=True))
    # A weekly check-in is now recorded on the day its period closed.
    op.execute(sa.text("UPDATE meetings SET scheduled_on = period_end"))
    op.alter_column("meetings", "scheduled_on", nullable=False)

    op.drop_constraint("ck_checkins_period", "meetings", type_="check")
    op.drop_column("meetings", "period_start")
    op.drop_column("meetings", "period_end")

    op.drop_constraint("ck_checkins_status", "meetings", type_="check")
    op.drop_constraint("ck_checkins_distinct_participants", "meetings", type_="check")
    op.create_check_constraint(
        "ck_meetings_status", "meetings", "status IN ('DRAFT', 'SUBMITTED', 'REVIEWED')"
    )
    op.create_check_constraint(
        "ck_meetings_distinct_participants", "meetings", "manager_id <> member_id"
    )
    op.create_check_constraint("ck_meetings_type", "meetings", f"type IN {_TYPES}")

    op.drop_index("ix_checkins_organization_id_updated_at", table_name="meetings")
    op.create_index(
        "ix_meetings_organization_id_updated_at",
        "meetings",
        ["organization_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_meetings_organization_id_type_scheduled_on",
        "meetings",
        ["organization_id", "type", "scheduled_on"],
        unique=False,
    )
    for column in ("organization_id", "manager_id", "member_id"):
        op.drop_index(f"ix_checkins_{column}", table_name="meetings")
        op.create_index(f"ix_meetings_{column}", "meetings", [column], unique=False)

    _rename_notification_types("CHECKIN", "MEETING")


def _rename_notification_types(before: str, after: str) -> None:
    """Notification types are free-text codes, so renaming them is a data update."""
    for event in ("CREATED", "SUBMITTED", "REVIEWED"):
        op.execute(
            sa.text("UPDATE notifications SET type = :after WHERE type = :before").bindparams(
                before=f"{before}_{event}",
                after=f"{after}_{event}",
            )
        )


def downgrade() -> None:
    _rename_notification_types("MEETING", "CHECKIN")

    for column in ("member_id", "manager_id", "organization_id"):
        op.drop_index(f"ix_meetings_{column}", table_name="meetings")
        op.create_index(f"ix_checkins_{column}", "meetings", [column], unique=False)
    op.drop_index("ix_meetings_organization_id_type_scheduled_on", table_name="meetings")
    op.drop_index("ix_meetings_organization_id_updated_at", table_name="meetings")
    op.create_index(
        "ix_checkins_organization_id_updated_at",
        "meetings",
        ["organization_id", "updated_at"],
        unique=False,
    )

    op.drop_constraint("ck_meetings_type", "meetings", type_="check")
    op.drop_constraint("ck_meetings_distinct_participants", "meetings", type_="check")
    op.drop_constraint("ck_meetings_status", "meetings", type_="check")
    op.create_check_constraint(
        "ck_checkins_status", "meetings", "status IN ('DRAFT', 'SUBMITTED', 'REVIEWED')"
    )
    op.create_check_constraint(
        "ck_checkins_distinct_participants", "meetings", "manager_id <> member_id"
    )

    # Meetings that are not check-ins have no period to restore; they collapse to a single day.
    op.add_column("meetings", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("meetings", sa.Column("period_end", sa.Date(), nullable=True))
    op.execute(
        sa.text("UPDATE meetings SET period_start = scheduled_on, period_end = scheduled_on")
    )
    op.alter_column("meetings", "period_start", nullable=False)
    op.alter_column("meetings", "period_end", nullable=False)
    op.create_check_constraint("ck_checkins_period", "meetings", "period_end >= period_start")

    op.drop_column("meetings", "scheduled_on")
    op.drop_column("meetings", "type")

    op.rename_table("meetings", "checkins")
