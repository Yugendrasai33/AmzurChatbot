"""Add google_id, avatar_url, auth_provider to profiles

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-05-02

Adds three nullable columns to public.profiles:
  - google_id      (TEXT, unique) – stores Google's "sub" claim
  - avatar_url     (TEXT)         – profile picture URL from Google
  - auth_provider  (VARCHAR 50)   – 'email' for password users, 'google' for OAuth users
                                    defaults to 'email' so existing rows are unaffected.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "public"


def upgrade() -> None:
    # google_id – nullable, unique (NULL values are not considered duplicates in PG)
    op.add_column(
        "profiles",
        sa.Column("google_id", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_profiles_google_id",
        "profiles",
        ["google_id"],
        schema=SCHEMA,
    )

    # avatar_url – nullable, no uniqueness required
    op.add_column(
        "profiles",
        sa.Column("avatar_url", sa.Text(), nullable=True),
        schema=SCHEMA,
    )

    # auth_provider – nullable, defaults to 'email' for backward compatibility
    op.add_column(
        "profiles",
        sa.Column(
            "auth_provider",
            sa.String(50),
            nullable=True,
            server_default=sa.text("'email'"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_profiles_google_id",
        "profiles",
        schema=SCHEMA,
        type_="unique",
    )
    op.drop_column("profiles", "google_id", schema=SCHEMA)
    op.drop_column("profiles", "avatar_url", schema=SCHEMA)
    op.drop_column("profiles", "auth_provider", schema=SCHEMA)
