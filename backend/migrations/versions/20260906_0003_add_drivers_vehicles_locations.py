"""Add driver profiles, vehicles, and PostGIS locations.

Revision ID: 20260906_0003
Revises: 20260906_0002
Create Date: 2026-09-06
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0003"
down_revision: str | None = "20260906_0002"
branch_labels: str | None = None
depends_on: str | None = None

verification_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "SUSPENDED",
    name="driver_verification_status",
    create_type=False,
)
driver_status = postgresql.ENUM(
    "OFFLINE",
    "AVAILABLE",
    "RESERVED",
    "ON_TRIP",
    name="driver_status",
    create_type=False,
)
vehicle_category = postgresql.ENUM(
    "STANDARD", "PREMIUM", "XL", name="vehicle_category", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    verification_status.create(bind, checkfirst=True)
    driver_status.create(bind, checkfirst=True)
    vehicle_category.create(bind, checkfirst=True)

    op.create_table(
        "driver_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("license_number", sa.String(length=64), nullable=False),
        sa.Column("license_expiry", sa.Date(), nullable=False),
        sa.Column(
            "verification_status",
            verification_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("status", driver_status, server_default="OFFLINE", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_driver_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_driver_profiles")),
        sa.UniqueConstraint("license_number", name=op.f("uq_driver_profiles_license_number")),
        sa.UniqueConstraint("user_id", name=op.f("uq_driver_profiles_user_id")),
    )
    op.create_index(
        op.f("ix_driver_profiles_verification_status"),
        "driver_profiles",
        ["verification_status"],
    )
    op.create_index(op.f("ix_driver_profiles_status"), "driver_profiles", ["status"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("color", sa.String(length=40), nullable=False),
        sa.Column("license_plate", sa.String(length=32), nullable=False),
        sa.Column("category", vehicle_category, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("year BETWEEN 1980 AND 2100", name=op.f("ck_vehicles_valid_year")),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name=op.f("fk_vehicles_driver_id_driver_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
        sa.UniqueConstraint("license_plate", name=op.f("uq_vehicles_license_plate")),
    )
    op.create_index(op.f("ix_vehicles_driver_id"), "vehicles", ["driver_id"])
    op.create_index(
        "uq_vehicles_one_active_per_driver",
        "vehicles",
        ["driver_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "driver_locations",
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("speed_kph", sa.Float(), nullable=True),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
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
            "accuracy_m IS NULL OR accuracy_m >= 0",
            name=op.f("ck_driver_locations_nonnegative_accuracy"),
        ),
        sa.CheckConstraint(
            "heading IS NULL OR (heading >= 0 AND heading < 360)",
            name=op.f("ck_driver_locations_valid_heading"),
        ),
        sa.CheckConstraint(
            "speed_kph IS NULL OR speed_kph >= 0",
            name=op.f("ck_driver_locations_nonnegative_speed"),
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name=op.f("fk_driver_locations_driver_id_driver_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("driver_id", name=op.f("pk_driver_locations")),
    )
    op.create_index(
        "ix_driver_locations_location_gist",
        "driver_locations",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(op.f("ix_driver_locations_recorded_at"), "driver_locations", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("driver_locations")
    op.drop_table("vehicles")
    op.drop_table("driver_profiles")
    vehicle_category.drop(op.get_bind(), checkfirst=True)
    driver_status.drop(op.get_bind(), checkfirst=True)
    verification_status.drop(op.get_bind(), checkfirst=True)
