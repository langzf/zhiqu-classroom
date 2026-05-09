"""align tutor conversation and message constraints

Revision ID: f2b7c9d1e4a6
Revises: c4fa332d8e9b
Create Date: 2026-05-09 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "f2b7c9d1e4a6"
down_revision: Union[str, None] = "c4fa332d8e9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_conversations_scene", "conversations", type_="check")
    op.create_check_constraint(
        "ck_conversations_scene",
        "conversations",
        "scene IN ('free_chat','general','homework_help','review','quiz','exploration','concept_explain','review_guide','error_analysis')",
    )

    op.drop_constraint("ck_messages_role", "messages", type_="check")
    op.create_check_constraint(
        "ck_messages_role",
        "messages",
        "role IN ('user','assistant','system','student','tutor')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_messages_role", "messages", type_="check")
    op.create_check_constraint(
        "ck_messages_role",
        "messages",
        "role IN ('student','tutor','system')",
    )

    op.drop_constraint("ck_conversations_scene", "conversations", type_="check")
    op.create_check_constraint(
        "ck_conversations_scene",
        "conversations",
        "scene IN ('free_chat','homework_help','review','quiz','exploration')",
    )
