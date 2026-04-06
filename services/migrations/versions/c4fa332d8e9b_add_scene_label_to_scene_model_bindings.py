"""sync model_config tables with ORM

Revision ID: c4fa332d8e9b
Revises: 1a38d69b2344
Create Date: 2026-04-06 21:41:15.030405

Adds missing columns that ORM expects but original migration omitted:
 - scene_model_bindings.scene_label
 - model_configs.capabilities (JSONB, replaces single-string capability)
 - model_configs.sort_order
 - model_providers.sort_order
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c4fa332d8e9b'
down_revision: Union[str, None] = '1a38d69b2344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) scene_model_bindings: add scene_label
    op.add_column(
        'scene_model_bindings',
        sa.Column('scene_label', sa.String(200), nullable=True, comment='场景中文描述'),
    )

    # 2) model_configs: add capabilities JSONB column
    #    (old 'capability' string column stays for now — no data loss)
    op.add_column(
        'model_configs',
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True, server_default=sa.text("'[\"chat\"]'"),
                  comment='能力标签 JSON array'),
    )

    # 3) model_configs: add sort_order
    op.add_column(
        'model_configs',
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default=sa.text('0')),
    )

    # 4) model_providers: add sort_order
    op.add_column(
        'model_providers',
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default=sa.text('0')),
    )


def downgrade() -> None:
    op.drop_column('model_providers', 'sort_order')
    op.drop_column('model_configs', 'sort_order')
    op.drop_column('model_configs', 'capabilities')
    op.drop_column('scene_model_bindings', 'scene_label')
