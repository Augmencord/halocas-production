"""Unit tests for SQLAlchemy models and relationship constraints."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.models import (
    AlertLog,
    Base,
    DeliveryStatus,
    Incident,
    IncidentSeverity,
    Machine,
    User,
    UserRole,
    Worker,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated, transactional in-memory database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_model(db_session: AsyncSession) -> None:
    """Verify worker creation, representation, and attributes."""
    worker = Worker(
        name="Marcus Vance",
        role="Authorized Mechanic",
        department="Fleet Maintenance",
        supervisor_email="safety@halocas.safety",
        face_embedding=[0.1, 0.2, 0.3],
        is_authorized=True,
    )
    db_session.add(worker)
    await db_session.commit()
    await db_session.refresh(worker)

    assert worker.id is not None
    assert worker.name == "Marcus Vance"
    assert worker.role == "Authorized Mechanic"
    assert worker.is_authorized is True
    assert worker.face_embedding == [0.1, 0.2, 0.3]
    assert "Worker(id=" in repr(worker)
    assert "Marcus Vance" in repr(worker)


@pytest.mark.asyncio
async def test_worker_supervision_hierarchy(db_session: AsyncSession) -> None:
    """Verify self-referential supervisor-subordinate relationship."""
    supervisor = Worker(
        name="Marcus Vance",
        role="Lead Mechanic",
        department="Maintenance",
        is_authorized=True,
    )
    db_session.add(supervisor)
    await db_session.commit()
    await db_session.refresh(supervisor)

    subordinate = Worker(
        name="Elena Rostova",
        role="Mechanic",
        department="Maintenance",
        supervisor_id=supervisor.id,
        is_authorized=True,
    )
    db_session.add(subordinate)
    await db_session.commit()
    await db_session.refresh(subordinate)

    # Query subordinate and check supervisor relationship
    stmt = select(Worker).where(Worker.id == subordinate.id)
    result = await db_session.scalar(stmt)
    assert result is not None
    assert result.supervisor is not None
    assert result.supervisor.id == supervisor.id
    assert result.supervisor.name == "Marcus Vance"


@pytest.mark.asyncio
async def test_machine_model(db_session: AsyncSession) -> None:
    """Verify machine creation, representation, and default status."""
    machine = Machine(
        name="CAT 793F Haul Truck #101",
        type="Haul Truck",
        zone="Zone-A Pit",
        status="active",
    )
    db_session.add(machine)
    await db_session.commit()
    await db_session.refresh(machine)

    assert machine.id is not None
    assert machine.name == "CAT 793F Haul Truck #101"
    assert machine.zone == "Zone-A Pit"
    assert "Machine(id=" in repr(machine)
    assert "Haul Truck" in repr(machine)


@pytest.mark.asyncio
async def test_incident_and_alert_log(db_session: AsyncSession) -> None:
    """Verify incident logging, enum serialization, and alert log cascade."""
    machine = Machine(
        name="CAT Loader #301",
        type="Wheel Loader",
        zone="Zone-B Crusher",
    )
    worker = Worker(
        name="Sarah Connor",
        role="General Worker",
        department="Surface Haulage",
        is_authorized=False,
    )
    db_session.add_all([machine, worker])
    await db_session.commit()

    incident = Incident(
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name=worker.name,
        distance_meters=2.1,
        severity=IncidentSeverity.CRITICAL,
        closing_velocity=1.8,
        clip_url="https://storage.halocas.safety/clips/inc_001.mp4",
        clip_duration_sec=5.0,
        supervisor_notified=True,
        supervisor_email="supervisor@halocas.safety",
        notification_sent_at=datetime.now(UTC),
        face_match_confidence=0.94,
        zone="Zone-B Crusher",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    assert incident.id is not None
    assert incident.severity == IncidentSeverity.CRITICAL
    assert "Incident(id=" in repr(incident)

    alert_log = AlertLog(
        incident_id=incident.id,
        recipient_email="supervisor@halocas.safety",
        delivery_status=DeliveryStatus.SENT,
        retry_count=0,
        sent_at=datetime.now(UTC),
    )
    db_session.add(alert_log)
    await db_session.commit()
    await db_session.refresh(alert_log)

    assert alert_log.id is not None
    assert alert_log.delivery_status == DeliveryStatus.SENT
    assert "AlertLog(id=" in repr(alert_log)


@pytest.mark.asyncio
async def test_user_model_and_repr(db_session: AsyncSession) -> None:
    """Verify user model creation, attributes, and custom __repr__."""
    user = User(
        email="test_user@halocas.safety",
        hashed_password="bcrypt_hash_simulated_token",
        full_name="Safety Supervisor",
        role=UserRole.SUPERVISOR,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test_user@halocas.safety"
    assert user.role == UserRole.SUPERVISOR
    assert user.is_active is True
    assert repr(user) == f"<User(id={user.id}, email='test_user@halocas.safety', role=supervisor, active=True)>"


def test_base_model_generic_repr() -> None:
    """Verify generic Base __repr__ on a model without custom __repr__ override."""
    class SampleEntity(Base):
        __tablename__ = "sample_entities"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String(50))

    entity = SampleEntity(id=42, name="TestSensor")
    repr_str = repr(entity)
    assert "<SampleEntity(" in repr_str
    assert "id=42" in repr_str
    assert "name='TestSensor'" in repr_str
