"""add query indexes for dashboard, filters, and notification lists

Revision ID: 0009_add_query_indexes
Revises: 0008_create_notifications
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_add_query_indexes"
down_revision: str | Sequence[str] | None = "0008_create_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_tasks_organization_id_status",
        "tasks",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_organization_id_status_due_date",
        "tasks",
        ["organization_id", "status", "due_date"],
        unique=False,
    )
    op.create_index(
        "ix_projects_organization_id_status",
        "projects",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_goals_organization_id_updated_at",
        "goals",
        ["organization_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_checkins_organization_id_updated_at",
        "checkins",
        ["organization_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_index("ix_checkins_organization_id_updated_at", table_name="checkins")
    op.drop_index("ix_goals_organization_id_updated_at", table_name="goals")
    op.drop_index("ix_projects_organization_id_status", table_name="projects")
    op.drop_index("ix_tasks_organization_id_status_due_date", table_name="tasks")
    op.drop_index("ix_tasks_organization_id_status", table_name="tasks")
