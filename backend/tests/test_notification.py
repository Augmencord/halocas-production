"""Unit and integration tests for the HALOCAS NotificationService.

Validates Resend API integration, HTML template generation, exponential backoff retries,
supervisor rate limiting (max 10 emails/minute), background task dispatching,
and alert_log database persistence.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from resend.exceptions import ResendError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    AlertLog,
    Base,
    DeliveryStatus,
    Incident,
    IncidentSeverity,
    Machine,
    Worker,
)
from app.services.notification import NotificationService


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_incident(db_session: AsyncSession) -> Incident:
    """Create and commit a baseline machine, worker, and incident in the test DB."""
    machine = Machine(
        name="Komatsu 930E",
        type="Haul Truck",
        zone="Haul Road East",
        status="ACTIVE",
    )
    worker = Worker(
        name="Alex Chen",
        role="Field Engineer",
        department="Operations",
        supervisor_email="supervisor@mine.example",
        face_embedding=[0.0] * 512,
        is_authorized=False,
    )
    db_session.add_all([machine, worker])
    await db_session.flush()

    incident = Incident(
        machine_id=machine.id,
        worker_id=worker.id,
        worker_name="Alex Chen",
        distance_meters=2.15,
        severity=IncidentSeverity.CRITICAL,
        closing_velocity=1.8,
        clip_url="https://r2.halocas.safety/clips/incident_101.mp4",
        clip_duration_sec=5.0,
        supervisor_email="supervisor@mine.example",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    return incident


def test_render_proximity_alert_html() -> None:
    """Verify HTML template contents, branding accents, and dynamic placeholders."""
    service = NotificationService(
        api_key="re_test_key",
        sender_email="alerts@halocas.safety",
    )
    html_out = service.render_proximity_alert_html(
        worker_name="John Doe <Mechanic>",
        distance=2.456,
        clip_url="https://r2.halocas.safety/clip.mp4",
        incident_id=42,
        timestamp=datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC),
    )

    # Brand checks
    assert "#0B0F19" in html_out
    assert "#00F0FF" in html_out
    assert "HALOCAS" in html_out
    assert "CRITICAL ALERT" in html_out

    # Content and safety escaping checks
    assert "John Doe &lt;Mechanic&gt;" in html_out
    assert "2.46 meters" in html_out
    assert "#42" in html_out
    assert "https://r2.halocas.safety/clip.mp4" in html_out
    assert "REVIEW INCIDENT CLIP &amp; TELEMETRY" in html_out or "REVIEW INCIDENT CLIP" in html_out


@pytest.mark.asyncio
async def test_send_proximity_alert_success(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify successful email delivery through mock Resend API and database logging."""
    service = NotificationService(
        api_key="re_test_mock_123",
        sender_email="alerts@halocas.safety",
        base_backoff_sec=0.01,
    )

    mock_resend_response = {"id": "resend_msg_abc123"}
    with patch("resend.Emails.send", return_value=mock_resend_response) as mock_send:
        success = await service.send_proximity_alert(
            supervisor_email="supervisor@mine.example",
            worker_name="Alex Chen",
            distance=2.15,
            clip_url="https://r2.halocas.safety/clips/incident_101.mp4",
            incident_id=sample_incident.id,
            db_session=db_session,
        )

        assert success is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["supervisor@mine.example"]
        assert call_args["from"] == "alerts@halocas.safety"
        assert "[HALOCAS] Proximity Alert — Alex Chen" in call_args["subject"]

    # Verify AlertLog written to database
    stmt = select(AlertLog).where(AlertLog.incident_id == sample_incident.id)
    result = await db_session.execute(stmt)
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].delivery_status == DeliveryStatus.SENT
    assert logs[0].retry_count == 0
    assert logs[0].recipient_email == "supervisor@mine.example"
    assert logs[0].sent_at is not None
    assert logs[0].error_message is None


@pytest.mark.asyncio
async def test_send_proximity_alert_retry_and_eventual_success(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify exponential backoff retries when encountering transient failures."""
    service = NotificationService(
        api_key="re_test_mock_123",
        max_retries=3,
        base_backoff_sec=0.01,  # Speed up tests
    )

    # Fail on first 2 attempts with ConnectionError, succeed on 3rd attempt
    mock_send = MagicMock(
        side_effect=[
            ConnectionError("Network timeout to api.resend.com"),
            ConnectionError("Socket reset"),
            {"id": "resend_msg_retry_success"},
        ]
    )

    with patch("resend.Emails.send", mock_send):
        success = await service.send_proximity_alert(
            supervisor_email="supervisor@mine.example",
            worker_name="Alex Chen",
            distance=1.85,
            clip_url=None,
            incident_id=sample_incident.id,
            db_session=db_session,
        )

        assert success is True
        assert mock_send.call_count == 3

    # Verify DB recorded retry_count=2 and status=SENT
    stmt = select(AlertLog).where(AlertLog.incident_id == sample_incident.id)
    result = await db_session.execute(stmt)
    log = result.scalars().first()
    assert log is not None
    assert log.delivery_status == DeliveryStatus.SENT
    assert log.retry_count == 2
    assert log.sent_at is not None


@pytest.mark.asyncio
async def test_send_proximity_alert_all_retries_exhausted_fallback(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify fallback handling when Resend consistently fails across all retries."""
    service = NotificationService(
        api_key="re_test_mock_123",
        max_retries=2,
        base_backoff_sec=0.01,
    )

    mock_send = MagicMock(
        side_effect=ResendError(
            code="internal_server_error",
            error_type="api_error",
            message="Resend internal gateway error",
            suggested_action="Check Resend service status or contact support",
        )
    )

    with patch("resend.Emails.send", mock_send):
        success = await service.send_proximity_alert(
            supervisor_email="supervisor@mine.example",
            worker_name="Alex Chen",
            distance=0.95,
            clip_url="https://r2.halocas.safety/clip.mp4",
            incident_id=sample_incident.id,
            db_session=db_session,
        )

        assert success is False
        # 1 initial attempt + 2 retries = 3 total attempts
        assert mock_send.call_count == 3

    # Verify DB log marked FAILED with retry count and diagnostic message
    stmt = select(AlertLog).where(AlertLog.incident_id == sample_incident.id)
    result = await db_session.execute(stmt)
    log = result.scalars().first()
    assert log is not None
    assert log.delivery_status == DeliveryStatus.FAILED
    assert log.retry_count == 2
    assert "Delivery failed after 2 retries" in (log.error_message or "")
    assert log.sent_at is None


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify strict supervisor rate limit cap (10 emails/minute)."""
    service = NotificationService(
        api_key="re_test_mock_123",
        rate_limit_per_minute=10,
        base_backoff_sec=0.01,
    )

    with patch("resend.Emails.send", return_value={"id": "mock_id"}) as mock_send:
        # First 10 alerts should succeed
        for i in range(10):
            allowed = await service.send_proximity_alert(
                supervisor_email="supervisor@mine.example",
                worker_name=f"Worker #{i}",
                distance=2.0,
                clip_url=None,
                incident_id=sample_incident.id,
                db_session=db_session,
            )
            assert allowed is True

        assert mock_send.call_count == 10

        # 11th alert within the same minute should be rejected by rate limiter
        blocked = await service.send_proximity_alert(
            supervisor_email="supervisor@mine.example",
            worker_name="Worker #11",
            distance=1.5,
            clip_url=None,
            incident_id=sample_incident.id,
            db_session=db_session,
        )
        assert blocked is False
        # Resend API should NOT have been called for 11th alert
        assert mock_send.call_count == 10

    # Verify that the 11th attempt logged a FAILED status with rate limit reason
    stmt = (
        select(AlertLog)
        .where(AlertLog.incident_id == sample_incident.id)
        .order_by(AlertLog.id.desc())
    )
    result = await db_session.execute(stmt)
    logs = list(result.scalars().all())
    assert len(logs) == 11
    latest_log = logs[0]
    assert latest_log.delivery_status == DeliveryStatus.FAILED
    assert "Rate limit exceeded" in (latest_log.error_message or "")


@pytest.mark.asyncio
async def test_dispatch_alert_background(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify non-blocking background task runner using asyncio.create_task."""
    service = NotificationService(
        api_key="re_test_mock_123",
        base_backoff_sec=0.01,
    )

    with patch("resend.Emails.send", return_value={"id": "async_task_id"}):
        task = service.dispatch_alert_background(
            supervisor_email="supervisor@mine.example",
            worker_name="Alex Chen",
            distance=2.3,
            clip_url=None,
            incident_id=sample_incident.id,
            db_session=db_session,
        )

        assert isinstance(task, asyncio.Task)
        res = await task
        assert res is True


@pytest.mark.asyncio
async def test_invalid_email_handling(
    db_session: AsyncSession, sample_incident: Incident
) -> None:
    """Verify rejection of invalid recipient emails without invoking Resend."""
    service = NotificationService(api_key="re_test_mock_123")

    with patch("resend.Emails.send") as mock_send:
        # Malformed email
        res = await service.send_proximity_alert(
            supervisor_email="not-an-email",
            worker_name="Alex Chen",
            distance=2.0,
            clip_url=None,
            incident_id=sample_incident.id,
            db_session=db_session,
        )
        assert res is False
        mock_send.assert_not_called()

    stmt = select(AlertLog).where(AlertLog.recipient_email == "not-an-email")
    result = await db_session.execute(stmt)
    log = result.scalars().first()
    assert log is not None
    assert log.delivery_status == DeliveryStatus.FAILED
    assert "Invalid recipient email" in (log.error_message or "")
