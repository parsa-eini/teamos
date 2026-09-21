"""create checkins

Revision ID: 0007_create_checkins
Revises: 0006_create_goals
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_create_checkins"
down_revision: str | Sequence[str] | None = "0006_create_goals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checkins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("manager_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("wins", sa.Text(), nullable=True),
        sa.Column("challenges", sa.Text(), nullable=True),
        sa.Column("next_steps", sa.Text(), nullable=True),
        sa.Column("manager_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'REVIEWED')",
            name="ck_checkins_status",
        ),
        sa.CheckConstraint("period_end >= period_start", name="ck_checkins_period"),
        sa.CheckConstraint("manager_id <> member_id", name="ck_checkins_distinct_participants"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_checkins_organization_id"), "checkins", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_checkins_manager_id"), "checkins", ["manager_id"], unique=False)
    op.create_index(op.f("ix_checkins_member_id"), "checkins", ["member_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_checkins_member_id"), table_name="checkins")
    op.drop_index(op.f("ix_checkins_manager_id"), table_name="checkins")
    op.drop_index(op.f("ix_checkins_organization_id"), table_name="checkins")
    op.drop_table("checkins")
