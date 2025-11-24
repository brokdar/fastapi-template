"""Create API Keys Table

Revision ID: d53baa2d1ef4
Revises: 2782954157ee
Create Date: 2025-11-23 18:01:26.198729

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = "d53baa2d1ef4"
down_revision: str | Sequence[str] | None = "2782954157ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create api_key table for storing hashed API keys.

    Creates the api_key table with indexes for efficient lookup by:
    - user_id (foreign key to user table)
    - key_prefix (unique, for key identification during authentication)
    """
    op.create_table(
        "api_key",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # BCrypt hashes are 60 chars; 255 provides headroom for algorithm changes
        sa.Column(
            "key_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False
        ),
        sa.Column(
            "key_prefix", sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False
        ),
        sa.Column(
            "name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_key_user_id"), "api_key", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_api_key_key_prefix"), "api_key", ["key_prefix"], unique=True
    )


def downgrade() -> None:
    """Drop api_key table and all associated indexes."""
    op.drop_index(op.f("ix_api_key_key_prefix"), table_name="api_key")
    op.drop_index(op.f("ix_api_key_user_id"), table_name="api_key")
    op.drop_table("api_key")
