"""Seed initial sample workers and machinery for HALOCAS.

Revision ID: 0002_seed_data
Revises: 0001_initial_schema
Create Date: 2026-09-04 18:52:30

Seeds:
- 3 heavy mining machines (Haul Truck, Excavator, Wheel Loader)
- 5 mine personnel (2 Authorized Mechanics, 3 General Workers) with supervision hierarchy
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_data"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

now_utc = datetime.now(UTC)

# 512-dimensional sample face embedding vector generator
def _generate_embedding(seed_val: float) -> list[float]:
    return [round(seed_val + (i * 0.001), 4) for i in range(512)]


def upgrade() -> None:
    # Bind metadata table references for bulk insertion
    machines_table = sa.table(
        "machines",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        sa.column("zone", sa.String),
        sa.column("status", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    workers_table = sa.table(
        "workers",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("role", sa.String),
        sa.column("department", sa.String),
        sa.column("supervisor_id", sa.Integer),
        sa.column("supervisor_email", sa.String),
        sa.column("face_embedding", sa.ARRAY(sa.Float()).with_variant(sa.JSON(), "sqlite")),
        sa.column("face_photo_url", sa.String),
        sa.column("is_authorized", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    # 1. Insert 3 Heavy Mining Machines
    op.bulk_insert(
        machines_table,
        [
            {
                "id": 1,
                "name": "CAT 793F Haul Truck #101",
                "type": "Haul Truck",
                "zone": "Zone-A Pit",
                "status": "active",
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            {
                "id": 2,
                "name": "Komatsu PC2000-8 Excavator #204",
                "type": "Excavator",
                "zone": "Zone-A Pit",
                "status": "active",
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            {
                "id": 3,
                "name": "CAT 992K Wheel Loader #305",
                "type": "Wheel Loader",
                "zone": "Zone-B Crusher",
                "status": "active",
                "created_at": now_utc,
                "updated_at": now_utc,
            },
        ],
    )

    # 2. Insert 5 Sample Workers (2 Authorized Mechanics, 3 General Workers)
    op.bulk_insert(
        workers_table,
        [
            # Lead Authorized Mechanic (Supervisor)
            {
                "id": 1,
                "name": "Marcus Vance",
                "role": "Authorized Mechanic",
                "department": "Heavy Fleet Maintenance",
                "supervisor_id": None,
                "supervisor_email": "chief.safety@halocas.safety",
                "face_embedding": _generate_embedding(0.12),
                "face_photo_url": "https://storage.halocas.safety/workers/marcus_vance.jpg",
                "is_authorized": True,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            # Authorized Field Mechanic
            {
                "id": 2,
                "name": "Elena Rostova",
                "role": "Authorized Mechanic",
                "department": "Hydraulics & Electrical",
                "supervisor_id": 1,
                "supervisor_email": "marcus.vance@halocas.safety",
                "face_embedding": _generate_embedding(0.25),
                "face_photo_url": "https://storage.halocas.safety/workers/elena_rostova.jpg",
                "is_authorized": True,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            # General Worker 1
            {
                "id": 3,
                "name": "Sarah Connor",
                "role": "General Worker",
                "department": "Surface Haulage",
                "supervisor_id": 1,
                "supervisor_email": "marcus.vance@halocas.safety",
                "face_embedding": _generate_embedding(0.38),
                "face_photo_url": "https://storage.halocas.safety/workers/sarah_connor.jpg",
                "is_authorized": False,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            # General Worker 2
            {
                "id": 4,
                "name": "David Chen",
                "role": "General Worker",
                "department": "Drill & Blast Operations",
                "supervisor_id": 1,
                "supervisor_email": "marcus.vance@halocas.safety",
                "face_embedding": _generate_embedding(0.49),
                "face_photo_url": "https://storage.halocas.safety/workers/david_chen.jpg",
                "is_authorized": False,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
            # General Worker 3
            {
                "id": 5,
                "name": "Carlos Mendoza",
                "role": "General Worker",
                "department": "Crusher & Processing",
                "supervisor_id": 2,
                "supervisor_email": "elena.rostova@halocas.safety",
                "face_embedding": _generate_embedding(0.61),
                "face_photo_url": "https://storage.halocas.safety/workers/carlos_mendoza.jpg",
                "is_authorized": False,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM workers WHERE id IN (1, 2, 3, 4, 5)")
    op.execute("DELETE FROM machines WHERE id IN (1, 2, 3)")
