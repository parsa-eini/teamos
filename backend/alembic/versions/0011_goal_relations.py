"""replace goals.team_id and goals.user_id with join tables and link goals to tasks

Revision ID: 0011_goal_relations
Revises: 0010_task_assignees
Create Date: 2026-09-05
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0011_goal_relations"
down_revision: str | Sequence[str] | None = "0010_task_assignees"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_link_table(name: str, column: str, target_table: str, constraint: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column(column, sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint([column], [f"{target_table}.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", column, name=constraint),
    )
    op.create_index(op.f(f"ix_{name}_goal_id"), name, ["goal_id"], unique=False)
    op.create_index(op.f(f"ix_{name}_{column}"), name, [column], unique=False)


def _drop_link_table(name: str, column: str) -> None:
    op.drop_index(op.f(f"ix_{name}_{column}"), table_name=name)
    op.drop_index(op.f(f"ix_{name}_goal_id"), table_name=name)
    op.drop_table(name)


def upgrade() -> None:
    _create_link_table("goal_teams", "team_id", "teams", "uq_goal_teams_goal_team")
    _create_link_table("goal_owners", "user_id", "users", "uq_goal_owners_goal_user")
    _create_link_table("goal_tasks", "task_id", "tasks", "uq_goal_tasks_goal_task")

    _copy_scalar_assignments("goal_teams", "team_id")
    _copy_scalar_assignments("goal_owners", "user_id")

    op.drop_index(op.f("ix_goals_team_id"), table_name="goals")
    op.drop_index(op.f("ix_goals_user_id"), table_name="goals")
    op.drop_column("goals", "team_id")
    op.drop_column("goals", "user_id")


def _copy_scalar_assignments(table: str, column: str) -> None:
    """Move each goal's single team or owner into its join table before the column is dropped."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(f"SELECT id, {column} FROM goals WHERE {column} IS NOT NULL")  # noqa: S608
    ).all()
    if not rows:
        return
    connection.execute(
        sa.text(
            f"INSERT INTO {table} (id, goal_id, {column}) "  # noqa: S608
            f"VALUES (:id, :goal_id, :{column})"
        ),
        [{"id": uuid4(), "goal_id": goal_id, column: target_id} for goal_id, target_id in rows],
    )


def downgrade() -> None:
    op.add_column("goals", sa.Column("team_id", sa.Uuid(), nullable=True))
    op.add_column("goals", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_goals_team_id_teams", "goals", "teams", ["team_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_goals_user_id_users", "goals", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_goals_team_id"), "goals", ["team_id"], unique=False)
    op.create_index(op.f("ix_goals_user_id"), "goals", ["user_id"], unique=False)

    # Only one team and one owner survive the downgrade; keep the earliest of each.
    for table, column in (("goal_teams", "team_id"), ("goal_owners", "user_id")):
        op.execute(
            sa.text(
                f"""
                UPDATE goals SET {column} = (
                    SELECT {column} FROM {table}
                    WHERE {table}.goal_id = goals.id
                    ORDER BY created_at, id
                    LIMIT 1
                )
                """  # noqa: S608
            )
        )

    _drop_link_table("goal_tasks", "task_id")
    _drop_link_table("goal_owners", "user_id")
    _drop_link_table("goal_teams", "team_id")
