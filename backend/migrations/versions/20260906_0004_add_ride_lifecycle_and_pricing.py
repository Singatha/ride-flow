"""Add configurable pricing and the ride lifecycle.

Revision ID: 20260906_0004
Revises: 20260906_0003
Create Date: 2026-09-06
"""

import uuid
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0004"
down_revision: str | None = "20260906_0003"
branch_labels: str | None = None
depends_on: str | None = None

ride_type = postgresql.ENUM("STANDARD", "PREMIUM", "XL", name="ride_type", create_type=False)
ride_status = postgresql.ENUM(
    "REQUESTED",
    "SEARCHING",
    "DRIVER_ASSIGNED",
    "DRIVER_ARRIVING",
    "DRIVER_ARRIVED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    name="ride_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ride_type.create(bind, checkfirst=True)
    ride_status.create(bind, checkfirst=True)

    pricing_rules = op.create_table(
        "pricing_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ride_type", ride_type, nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="ZAR", nullable=False),
        sa.Column("base_fare", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cost_per_km", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cost_per_minute", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("average_speed_kph", sa.Numeric(precision=6, scale=2), nullable=False),
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
        sa.CheckConstraint(
            "average_speed_kph > 0", name=op.f("ck_pricing_rules_positive_average_speed")
        ),
        sa.CheckConstraint("base_fare >= 0", name=op.f("ck_pricing_rules_nonnegative_base_fare")),
        sa.CheckConstraint(
            "cost_per_km >= 0", name=op.f("ck_pricing_rules_nonnegative_cost_per_km")
        ),
        sa.CheckConstraint(
            "cost_per_minute >= 0",
            name=op.f("ck_pricing_rules_nonnegative_cost_per_minute"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pricing_rules")),
    )
    op.create_index(op.f("ix_pricing_rules_ride_type"), "pricing_rules", ["ride_type"])
    op.create_index(
        "uq_pricing_rules_one_active_per_type",
        "pricing_rules",
        ["ride_type"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.bulk_insert(
        pricing_rules,
        [
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
                "ride_type": "STANDARD",
                "currency": "ZAR",
                "base_fare": Decimal("20.00"),
                "cost_per_km": Decimal("12.00"),
                "cost_per_minute": Decimal("1.50"),
                "average_speed_kph": Decimal("35.00"),
                "is_active": True,
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
                "ride_type": "PREMIUM",
                "currency": "ZAR",
                "base_fare": Decimal("35.00"),
                "cost_per_km": Decimal("18.00"),
                "cost_per_minute": Decimal("2.00"),
                "average_speed_kph": Decimal("35.00"),
                "is_active": True,
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
                "ride_type": "XL",
                "currency": "ZAR",
                "base_fare": Decimal("30.00"),
                "cost_per_km": Decimal("16.00"),
                "cost_per_minute": Decimal("1.80"),
                "average_speed_kph": Decimal("30.00"),
                "is_active": True,
            },
        ],
    )

    op.create_table(
        "rides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rider_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("pricing_rule_id", sa.Uuid(), nullable=False),
        sa.Column("status", ride_status, server_default="REQUESTED", nullable=False),
        sa.Column("ride_type", ride_type, nullable=False),
        sa.Column(
            "pickup_location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "destination_location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("estimated_distance_km", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("estimated_fare", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("final_fare", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arriving_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            "estimated_distance_km >= 0", name=op.f("ck_rides_nonnegative_distance")
        ),
        sa.CheckConstraint(
            "estimated_duration_minutes >= 0",
            name=op.f("ck_rides_nonnegative_duration"),
        ),
        sa.CheckConstraint("estimated_fare >= 0", name=op.f("ck_rides_nonnegative_estimated_fare")),
        sa.CheckConstraint(
            "final_fare IS NULL OR final_fare >= 0",
            name=op.f("ck_rides_nonnegative_final_fare"),
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["driver_profiles.id"],
            name=op.f("fk_rides_driver_id_driver_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pricing_rule_id"],
            ["pricing_rules.id"],
            name=op.f("fk_rides_pricing_rule_id_pricing_rules"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name=op.f("fk_rides_vehicle_id_vehicles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rider_id"],
            ["users.id"],
            name=op.f("fk_rides_rider_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rides")),
    )
    op.create_index(op.f("ix_rides_rider_id"), "rides", ["rider_id"])
    op.create_index("ix_rides_rider_requested", "rides", ["rider_id", "requested_at"])
    op.create_index("ix_rides_driver_status", "rides", ["driver_id", "status"])
    op.create_index("ix_rides_status_requested", "rides", ["status", "requested_at"])
    op.create_index(
        "ix_rides_pickup_location_gist",
        "rides",
        ["pickup_location"],
        postgresql_using="gist",
    )
    op.create_index(
        "uq_rides_one_active_per_rider",
        "rides",
        ["rider_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('COMPLETED', 'CANCELLED')"),
    )
    op.create_index(
        "uq_rides_one_active_per_driver",
        "rides",
        ["driver_id"],
        unique=True,
        postgresql_where=sa.text(
            "driver_id IS NOT NULL AND status NOT IN ('COMPLETED', 'CANCELLED')"
        ),
    )


def downgrade() -> None:
    op.drop_table("rides")
    op.drop_table("pricing_rules")
    ride_status.drop(op.get_bind(), checkfirst=True)
    ride_type.drop(op.get_bind(), checkfirst=True)
