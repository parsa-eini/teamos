"""add a reporting line to organization memberships

Revision ID: 0013_org_hierarchy
Revises: 0012_meetings
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_org_hierarchy"
down_revision: str | Sequence[str] | None = "0012_meetings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_memberships",
        sa.Column("reports_to_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_organization_memberships_reports_to_user_id_users",
        "organization_memberships",
        "users",
        ["reports_to_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_organization_memberships_reports_to_user_id"),
        "organization_memberships",
        ["reports_to_user_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_organization_memberships_reports_to_not_self",
        "organization_memberships",
        "reports_to_user_id IS NULL OR reports_to_user_id <> user_id",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_organization_memberships_reports_to_not_self",
        "organization_memberships",
        type_="check",
    )
    op.drop_index(
        op.f("ix_organization_memberships_reports_to_user_id"),
        table_name="organization_memberships",
    )
    op.drop_constraint(
        "fk_organization_memberships_reports_to_user_id_users",
        "organization_memberships",
        type_="foreignkey",
    )
    op.drop_column("organization_memberships", "reports_to_user_id")
