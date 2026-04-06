"""add model_config tables

Revision ID: 1a38d69b2344
Revises: 979e05fcad6b
Create Date: 2026-04-06 20:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1a38d69b2344'
down_revision: Union[str, None] = '979e05fcad6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- model_providers ---
    op.create_table('model_providers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('extra_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_providers_provider_type'), 'model_providers', ['provider_type'], unique=False)

    # --- model_configs ---
    op.create_table('model_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provider_id', sa.Uuid(), nullable=False),
        sa.Column('model_name', sa.String(length=200), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('capability', sa.String(length=50), nullable=False),
        sa.Column('default_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['model_providers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_configs_capability'), 'model_configs', ['capability'], unique=False)

    # --- scene_model_bindings ---
    op.create_table('scene_model_bindings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('scene_key', sa.String(length=100), nullable=False),
        sa.Column('model_config_id', sa.Uuid(), nullable=False),
        sa.Column('param_overrides', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['model_config_id'], ['model_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scene_model_bindings_scene_key'), 'scene_model_bindings', ['scene_key'], unique=True)


def downgrade() -> None:
    op.drop_table('scene_model_bindings')
    op.drop_table('model_configs')
    op.drop_table('model_providers')
