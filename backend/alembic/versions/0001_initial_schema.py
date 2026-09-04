"""Initial schema creation for HALOCAS.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-04 18:52:00

Creates core mining safety tables:
- workers: mine personnel, credentials, supervisor chain, face embeddings
- machines: heavy equipment inventory and telemetry zones
- incidents: near-miss proximity violations and incident clips
- alert_logs: automated emergency notification dispatches
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create workers table
    op.create_table(
        "workers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, comment="Operational role"),
        sa.Column("department", sa.String(length=50), nullable=False),
        sa.Column("supervisor_id", sa.Integer(), nullable=True),
        sa.Column("supervisor_email", sa.String(length=255), nullable=True),
        sa.Column(
            "face_embedding",
            sa.ARRAY(sa.Float()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
            comment="Facenet512 facial feature embedding vector (512 dimensions)",
        ),
        sa.Column("face_photo_url", sa.String(length=500), nullable=True),
        sa.Column("is_authorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["supervisor_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workers_name", "workers", ["name"], unique=False)
    op.create_index("ix_workers_supervisor_id", "workers", ["supervisor_id"], unique=False)

    # 2. Create machines table
    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, comment="Machinery category"),
        sa.Column("zone", sa.String(length=50), nullable=False, comment="Operating sector"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_machines_name", "machines", ["name"], unique=False)

    # 3. Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=True),
        sa.Column("worker_name", sa.String(length=100), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "WARNING", "CAUTION", name="incident_severity_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("closing_velocity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("clip_url", sa.String(length=500), nullable=True),
        sa.Column("clip_duration_sec", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("supervisor_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supervisor_email", sa.String(length=255), nullable=True),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("face_match_confidence", sa.Float(), nullable=True),
        sa.Column("zone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_timestamp", "incidents", ["timestamp"], unique=False)
    op.create_index("ix_incidents_machine_id", "incidents", ["machine_id"], unique=False)
    op.create_index("ix_incidents_worker_id", "incidents", ["worker_id"], unique=False)
    op.create_index("ix_incidents_severity", "incidents", ["severity"], unique=False)

    # 4. Create alert_logs table
    op.create_table(
        "alert_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column(
            "delivery_status",
            sa.Enum("PENDING", "SENT", "FAILED", "RETRYING", name="alert_delivery_status_enum", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_logs_incident_id", "alert_logs", ["incident_id"], unique=False)
    op.create_index("ix_alert_logs_delivery_status", "alert_logs", ["delivery_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_logs_delivery_status", table_name="alert_logs")
    op.drop_index("ix_alert_logs_incident_id", table_name="alert_logs")
    op.drop_table("alert_logs")

    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_worker_id", table_name="incidents")
    op.drop_index("ix_incidents_machine_id", table_name="incidents")
    op.drop_index("ix_incidents_timestamp", table_name="incidents")
    op.drop_table("incidents")

    op.drop_index("ix_machines_name", table_name="machines")
    op.drop_table("machines")

    op.drop_index("ix_workers_supervisor_id", table_name="workers")
    op.drop_index("ix_workers_name", table_name="workers")
    op.drop_table("workers")
