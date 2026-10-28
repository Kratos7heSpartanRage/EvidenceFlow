"""Preserve PICO curation history, empty snapshots, and performance indexes.

Revision ID: 0003_review_integrity
Revises: 0002_query_options
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_review_integrity"
down_revision = "0002_query_options"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pico_annotations") as batch:
        batch.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="suggested")
        )
        batch.add_column(sa.Column("supersedes_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("reviewer", sa.String(255), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("algo_version", sa.String(50), nullable=True))
        batch.create_foreign_key(
            "fk_pico_supersedes", "pico_annotations", ["supersedes_id"], ["id"]
        )
    op.execute("UPDATE pico_annotations SET status = 'confirmed' WHERE is_confirmed = true")
    op.add_column(
        "query_versions",
        sa.Column("snapshot_captured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE query_versions SET snapshot_captured = true WHERE EXISTS (SELECT 1 FROM group_snapshots WHERE group_snapshots.query_version_id = query_versions.id)"
    )
    op.create_index(
        "idx_record_review_rep_hidden", "records", ["review_id", "is_representative", "is_hidden"]
    )
    op.create_index("idx_record_review_group", "records", ["review_id", "group_id"])
    op.create_index("idx_duplicate_pairs_review_tier", "duplicate_pairs", ["review_id", "tier"])
    op.create_index("idx_duplicate_pairs_review_status", "duplicate_pairs", ["review_id", "status"])


def downgrade():
    op.drop_index("idx_duplicate_pairs_review_status", table_name="duplicate_pairs")
    op.drop_index("idx_duplicate_pairs_review_tier", table_name="duplicate_pairs")
    op.drop_index("idx_record_review_group", table_name="records")
    op.drop_index("idx_record_review_rep_hidden", table_name="records")
    with op.batch_alter_table("query_versions") as batch:
        batch.drop_column("snapshot_captured")
    with op.batch_alter_table("pico_annotations") as batch:
        batch.drop_constraint("fk_pico_supersedes", type_="foreignkey")
        for name in ("algo_version", "content_hash", "reviewer", "supersedes_id", "status"):
            batch.drop_column(name)
