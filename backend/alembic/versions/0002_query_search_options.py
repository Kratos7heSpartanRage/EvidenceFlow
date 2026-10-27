"""Persist search scope and the frozen source preview.

Revision ID: 0002_query_options
Revises: 0001_initial
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_query_options"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_versions",
        sa.Column("title_abstract_only", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("query_versions", sa.Column("preview_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("query_versions") as batch:
        batch.drop_column("preview_payload")
        batch.drop_column("title_abstract_only")
