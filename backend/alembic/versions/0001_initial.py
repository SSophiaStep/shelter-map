"""initial: places, users, reports

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "type", sa.Enum("SHELTER", "HEATING", name="placetype"), nullable=False
        ),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT", srid=4326, spatial_index=False
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_places_type", "places", ["type"])
    op.create_index(
        "idx_places_location", "places", ["location"], postgresql_using="gist"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "place_id",
            sa.Integer(),
            sa.ForeignKey("places.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reports_place_id", "reports", ["place_id"])
    op.create_index("ix_reports_author_id", "reports", ["author_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("users")
    op.drop_table("places")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="placetype").drop(op.get_bind(), checkfirst=True)
