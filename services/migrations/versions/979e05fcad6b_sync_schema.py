"""sync schema - align DB with ORM models

Revision ID: 979e05fcad6b
Revises: 05c4047cd0e7
Create Date: 2026-04-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '979e05fcad6b'
down_revision: Union[str, None] = '05c4047cd0e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_not_exists(table: str, column: sa.Column):
    """Add column only if it doesn't already exist."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column.name})
    if result.fetchone() is None:
        op.add_column(table, column)


def _create_check_if_not_exists(name: str, table: str, condition: str):
    """Create CHECK constraint only if it doesn't already exist."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname=:n"
    ), {"n": name})
    if result.fetchone() is None:
        op.create_check_constraint(name, table, condition)


def _create_index_if_not_exists(name: str, table: str, columns: list, **kw):
    """Create index only if it doesn't already exist."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:n"
    ), {"n": name})
    if result.fetchone() is None:
        op.create_index(name, table, columns, **kw)


def upgrade() -> None:
    # -- textbooks --
    _add_column_if_not_exists('textbooks',
        sa.Column('file_url', sa.String(length=1024), nullable=True))

    # -- knowledge_points --
    _add_column_if_not_exists('knowledge_points',
        sa.Column('bloom_level', sa.String(length=32), nullable=True))
    _add_column_if_not_exists('knowledge_points',
        sa.Column('prerequisites', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # -- generated_resources --
    _add_column_if_not_exists('generated_resources',
        sa.Column('model_used', sa.String(length=64), nullable=True))
    _add_column_if_not_exists('generated_resources',
        sa.Column('prompt_used', sa.Text(), nullable=True))
    _create_check_if_not_exists(
        'ck_generated_resources_resource_type', 'generated_resources',
        "resource_type IN ('explanation','exercise','quiz','summary','mindmap')")

    # -- conversations --
    _add_column_if_not_exists('conversations',
        sa.Column('student_profile_id', sa.Uuid(), nullable=True))
    _add_column_if_not_exists('conversations',
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _add_column_if_not_exists('conversations',
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True))
    _create_check_if_not_exists(
        'ck_conversations_scene', 'conversations',
        "scene IN ('free_chat','homework_help','review','quiz','exploration')")
    _create_check_if_not_exists(
        'ck_conversations_status', 'conversations',
        "status IN ('active','ended','archived')")

    # -- messages --
    _add_column_if_not_exists('messages',
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _add_column_if_not_exists('messages',
        sa.Column('tokens_used', sa.Integer(), nullable=True))
    _create_check_if_not_exists(
        'ck_messages_role', 'messages',
        "role IN ('student','tutor','system')")

    # -- prompt_templates --
    _add_column_if_not_exists('prompt_templates',
        sa.Column('model_name', sa.String(length=64), nullable=True))
    _add_column_if_not_exists('prompt_templates',
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _add_column_if_not_exists('prompt_templates',
        sa.Column('max_tokens', sa.Integer(), nullable=True))
    _add_column_if_not_exists('prompt_templates',
        sa.Column('temperature', sa.Float(), nullable=True))
    _create_index_if_not_exists(
        'idx_prompt_templates_active', 'prompt_templates', ['is_active'])

    # -- student_profiles --
    _add_column_if_not_exists('student_profiles',
        sa.Column('weak_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    _add_column_if_not_exists('student_profiles',
        sa.Column('preferred_difficulty', sa.Integer(), nullable=True))
    _add_column_if_not_exists('student_profiles',
        sa.Column('total_study_minutes', sa.Integer(), server_default='0', nullable=True))
    _add_column_if_not_exists('student_profiles',
        sa.Column('streak_days', sa.Integer(), server_default='0', nullable=True))

    # -- mastery_records --
    _add_column_if_not_exists('mastery_records',
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=True))
    _add_column_if_not_exists('mastery_records',
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_not_exists('mastery_records',
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True))

    # -- tasks --
    _add_column_if_not_exists('tasks',
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    _create_check_if_not_exists(
        'ck_tasks_task_type', 'tasks',
        "task_type IN ('homework','review','practice','exploration')")
    _create_check_if_not_exists(
        'ck_tasks_status', 'tasks',
        "status IN ('draft','published','archived')")
    _create_index_if_not_exists(
        'idx_tasks_publish', 'tasks', ['published_at'])

    # -- task_items --
    _create_check_if_not_exists(
        'ck_task_items_item_type', 'task_items',
        "item_type IN ('exercise','reading','video','quiz')")

    # -- study_sessions --
    # NOTE: study_sessions uses 'activity_type', not 'session_type'; skipped
    # _create_check_if_not_exists(
    #     'ck_study_sessions_session_type', 'study_sessions',
    #     "session_type IN ('free_chat','homework_help','review','quiz','exploration')")


def downgrade() -> None:
    # Reverse in order
    # NOTE: session_type constraint was skipped in upgrade; skip here too
    # op.drop_constraint('ck_study_sessions_session_type', 'study_sessions', type_='check')
    op.drop_constraint('ck_task_items_item_type', 'task_items', type_='check')

    op.drop_index('idx_tasks_publish', 'tasks')
    op.drop_constraint('ck_tasks_status', 'tasks', type_='check')
    op.drop_constraint('ck_tasks_task_type', 'tasks', type_='check')
    op.drop_column('tasks', 'published_at')

    op.drop_column('mastery_records', 'next_review_at')
    op.drop_column('mastery_records', 'last_reviewed_at')
    op.drop_column('mastery_records', 'attempt_count')

    op.drop_column('student_profiles', 'streak_days')
    op.drop_column('student_profiles', 'total_study_minutes')
    op.drop_column('student_profiles', 'preferred_difficulty')
    op.drop_column('student_profiles', 'weak_topics')

    op.drop_index('idx_prompt_templates_active', 'prompt_templates')
    op.drop_column('prompt_templates', 'temperature')
    op.drop_column('prompt_templates', 'max_tokens')
    op.drop_column('prompt_templates', 'tags')
    op.drop_column('prompt_templates', 'model_name')

    op.drop_constraint('ck_messages_role', 'messages', type_='check')
    op.drop_column('messages', 'tokens_used')
    op.drop_column('messages', 'metadata')

    op.drop_constraint('ck_conversations_status', 'conversations', type_='check')
    op.drop_constraint('ck_conversations_scene', 'conversations', type_='check')
    op.drop_column('conversations', 'ended_at')
    op.drop_column('conversations', 'metadata')
    op.drop_column('conversations', 'student_profile_id')

    op.drop_constraint('ck_generated_resources_resource_type', 'generated_resources', type_='check')
    op.drop_column('generated_resources', 'prompt_used')
    op.drop_column('generated_resources', 'model_used')

    op.drop_column('knowledge_points', 'prerequisites')
    op.drop_column('knowledge_points', 'bloom_level')

    op.drop_column('textbooks', 'file_url')
