"""create the feedback table

Revision ID: 0014_create_feedback
Revises: 0013_org_hierarchy
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_create_feedback"
down_revision: str | Sequence[str] | None = "0013_org_hierarchy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
            "sentiment IN ('POSITIVE', 'NEGATIVE')",
            name="ck_feedback_sentiment",
        ),
        sa.CheckConstraint("author_id <> subject_id", name="ck_feedback_distinct_participants"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_organization_id"), "feedback", ["organization_id"])
    op.create_index(op.f("ix_feedback_subject_id"), "feedback", ["subject_id"])
    op.create_index(op.f("ix_feedback_author_id"), "feedback", ["author_id"])
    op.create_index(
        "ix_feedback_organization_id_subject_id_created_at",
        "feedback",
        ["organization_id", "subject_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_organization_id_subject_id_created_at", table_name="feedback")
    op.drop_index(op.f("ix_feedback_author_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_subject_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_organization_id"), table_name="feedback")
    op.drop_table("feedback")
