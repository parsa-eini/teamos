"""replace tasks.assignee_id with a task_assignees join table

Revision ID: 0010_task_assignees
Revises: 0009_add_query_indexes
Create Date: 2026-09-05
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0010_task_assignees"
down_revision: str | Sequence[str] | None = "0009_add_query_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_assignees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignees_task_user"),
    )
    op.create_index(
        op.f("ix_task_assignees_task_id"),
        "task_assignees",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_assignees_user_id"),
        "task_assignees",
        ["user_id"],
        unique=False,
    )

    _copy_existing_assignees()

    op.drop_index(op.f("ix_tasks_assignee_id"), table_name="tasks")
    op.drop_column("tasks", "assignee_id")


def _copy_existing_assignees() -> None:
    """Move each task's single assignee into the join table before the column is dropped."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, assignee_id FROM tasks WHERE assignee_id IS NOT NULL")
    ).all()
    if not rows:
        return
    connection.execute(
        sa.text(
            "INSERT INTO task_assignees (id, task_id, user_id) VALUES (:id, :task_id, :user_id)"
        ),
        [
            {"id": uuid4(), "task_id": task_id, "user_id": assignee_id}
            for task_id, assignee_id in rows
        ],
    )


def downgrade() -> None:
    op.add_column("tasks", sa.Column("assignee_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_assignee_id_users",
        "tasks",
        "users",
        ["assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_tasks_assignee_id"), "tasks", ["assignee_id"], unique=False)

    # Only one assignee survives the downgrade; keep the earliest assignment.
    op.execute(
        sa.text(
            """
            UPDATE tasks SET assignee_id = (
                SELECT user_id FROM task_assignees
                WHERE task_assignees.task_id = tasks.id
                ORDER BY created_at, id
                LIMIT 1
            )
            """
        )
    )

    op.drop_index(op.f("ix_task_assignees_user_id"), table_name="task_assignees")
    op.drop_index(op.f("ix_task_assignees_task_id"), table_name="task_assignees")
    op.drop_table("task_assignees")
