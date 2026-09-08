"""Add persistent ride matching attempts.

Revision ID: 20260908_0005
Revises: 20260906_0004
Create Date: 2026-09-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0005"
down_revision: str | None = "20260906_0004"
branch_labels: str | None = None
depends_on: str | None = None

match_attempt_outcome = postgresql.ENUM(
    "OFFERED",
    "REJECTED",
    "TIMED_OUT",
    "ACCEPTED",
    "CANCELLED",
    name="match_attempt_outcome",
    create_type=False,
)


def upgrade() -> None:
    match_attempt_outcome.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "ride_match_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ride_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column(
            "outcome",
            match_attempt_outcome,
            server_default="OFFERED",
            nullable=False,
        ),
        sa.Column("distance_m", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "distance_m >= 0",
            name=op.f("ck_ride_match_attempts_nonnegative_distance"),
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name=op.f("fk_ride_match_attempts_driver_id_driver_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ride_id"],
            ["rides.id"],
            name=op.f("fk_ride_match_attempts_ride_id_rides"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ride_match_attempts")),
        sa.UniqueConstraint(
            "ride_id",
            "driver_id",
            name=op.f("uq_ride_match_attempts_ride_id"),
        ),
    )
    op.create_index(
        op.f("ix_ride_match_attempts_driver_id"),
        "ride_match_attempts",
        ["driver_id"],
    )
    op.create_index(
        op.f("ix_ride_match_attempts_expires_at"),
        "ride_match_attempts",
        ["expires_at"],
    )
    op.create_index(
        op.f("ix_ride_match_attempts_ride_id"),
        "ride_match_attempts",
        ["ride_id"],
    )
    op.create_index(
        "ix_ride_match_attempts_ride_outcome",
        "ride_match_attempts",
        ["ride_id", "outcome"],
    )
    op.create_index(
        "uq_ride_match_attempts_one_offered_per_ride",
        "ride_match_attempts",
        ["ride_id"],
        unique=True,
        postgresql_where=sa.text("outcome = 'OFFERED'"),
    )
    op.create_index(
        "uq_ride_match_attempts_one_offer_per_driver",
        "ride_match_attempts",
        ["driver_id"],
        unique=True,
        postgresql_where=sa.text("outcome = 'OFFERED'"),
    )


def downgrade() -> None:
    op.drop_table("ride_match_attempts")
    match_attempt_outcome.drop(op.get_bind(), checkfirst=True)
