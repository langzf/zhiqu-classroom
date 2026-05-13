"""add voice profiles and user voice settings

Revision ID: a8d6e2f4c901
Revises: f2b7c9d1e4a6
Create Date: 2026-05-13 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a8d6e2f4c901"
down_revision: Union[str, None] = "f2b7c9d1e4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="tts"),
        sa.Column("voice_key", sa.String(length=100), nullable=False, server_default="af_heart"),
        sa.Column("reference_filename", sa.String(length=255), nullable=True),
        sa.Column("reference_content_type", sa.String(length=100), nullable=True),
        sa.Column("reference_audio", sa.LargeBinary(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_voice_profiles_active", "voice_profiles", ["is_active", "sort_order"], unique=False)

    op.create_table(
        "user_voice_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("voice_profile_id", sa.Uuid(), nullable=True),
        sa.Column("auto_play", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute(
        """
        INSERT INTO voice_profiles (id, name, description, provider, voice_key, is_active, sort_order)
        VALUES
          ('019e2f00-1111-7111-8111-111111111111', '默认女声', 'Kokoro 默认播报音色', 'tts', 'af_heart', true, 0),
          ('019e2f00-2222-7222-8222-222222222222', '默认男声', 'Kokoro 备用播报音色', 'tts', 'am_adam', true, 10)
        """
    )


def downgrade() -> None:
    op.drop_table("user_voice_settings")
    op.drop_index("idx_voice_profiles_active", table_name="voice_profiles")
    op.drop_table("voice_profiles")
