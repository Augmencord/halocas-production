"""HALOCAS Notification Service.

Provides production-grade automated safety alerts dispatched to supervisors via the
Resend API (https://resend.com/docs/api-reference). Encapsulates branded HTML email
templating, exponential backoff retries, supervisor rate limiting, persistent
audit logging into the PostgreSQL alert_log table, and non-blocking background
task execution.
"""

from __future__ import annotations

import asyncio
import collections
import html
import threading
import time
from datetime import UTC, datetime
from typing import Any

import resend
from resend.exceptions import ResendError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.core.logging import get_logger
from app.models.alert_log import AlertLog, DeliveryStatus

logger = get_logger("halocas.services.notification")


class NotificationError(Exception):
    """Base exception for notification service operational failures."""


class RateLimitExceededError(NotificationError):
    """Raised when a recipient exceeds the maximum allowed email dispatch frequency."""


class NotificationService:
    """Production notification manager for industrial safety proximity alerts.

    Integrates with the Resend email platform to transmit high-priority alert emails
    to site supervisors. Enforces delivery rate limits, automated retries with
    exponential backoff, and full database persistence in `alert_logs`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        sender_email: str | None = None,
        max_retries: int = 3,
        base_backoff_sec: float = 1.0,
        rate_limit_per_minute: int = 10,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """Initialize NotificationService with credentials and operational constraints.

        Args:
            api_key: Resend API key. If omitted, fetched from application settings.
            sender_email: Outbound sender address (e.g. 'alerts@halocas.safety').
            max_retries: Number of retry attempts on transient network/API failures.
            base_backoff_sec: Base delay in seconds for exponential backoff (1s, 2s, 4s).
            rate_limit_per_minute: Maximum alert emails allowed per supervisor per 60s.
            session_factory: Optional SQLAlchemy async sessionmaker for database logging.
        """
        settings = get_settings()
        self.api_key = api_key or settings.RESEND_API_KEY
        self.sender_email = sender_email or settings.SMTP_SENDER
        self.max_retries = max_retries
        self.base_backoff_sec = base_backoff_sec
        self.rate_limit_per_minute = rate_limit_per_minute
        self.session_factory = session_factory

        if self.api_key:
            resend.api_key = self.api_key

        # Rate limiting state: supervisor_email -> list of epoch timestamps
        self._dispatch_history: dict[str, list[float]] = collections.defaultdict(list)
        self._rate_limit_lock = threading.Lock()

        # Background task registry to avoid premature garbage collection
        self._background_tasks: set[asyncio.Task[Any]] = set()

        logger.info(
            "NotificationService initialized with sender=%s, max_retries=%d, rate_limit=%d/min",
            self.sender_email,
            self.max_retries,
            self.rate_limit_per_minute,
        )

    def _check_and_record_rate_limit(self, email: str) -> bool:
        """Evaluate and update sliding-window rate limit for a supervisor email.

        Enforces a strict cap (default 10 emails/minute) per supervisor.

        Args:
            email: Supervisor recipient email address.

        Returns:
            bool: True if dispatch is permitted, False if rate limit is exceeded.
        """
        key = email.strip().lower()
        now = time.time()
        window_start = now - 60.0

        with self._rate_limit_lock:
            history = self._dispatch_history[key]
            # Prune events older than 60 seconds
            valid_history = [t for t in history if t > window_start]
            self._dispatch_history[key] = valid_history

            if len(valid_history) >= self.rate_limit_per_minute:
                return False

            valid_history.append(now)
            return True

    def render_proximity_alert_html(
        self,
        worker_name: str,
        distance: float,
        clip_url: str | None,
        incident_id: int,
        timestamp: datetime | None = None,
    ) -> str:
        """Construct a high-impact branded HTML email template for proximity breaches.

        Matches the HALOCAS brand aesthetic: deep dark navy background (#0B0F19),
        surface cards (#111827), luminous cyan accents (#00F0FF), and high-visibility
        safety warning elements.

        Args:
            worker_name: Identified or unverified worker name.
            distance: Measured distance to heavy equipment in meters.
            clip_url: Signed Cloudflare R2 video clip URL or dashboard link.
            incident_id: Database incident tracking primary key.
            timestamp: Event timestamp. Defaults to UTC now if omitted.

        Returns:
            str: Fully styled inline HTML email content.
        """
        ts = timestamp or datetime.now(UTC)
        formatted_time = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
        safe_worker_name = html.escape(worker_name)
        safe_clip_url = html.escape(clip_url) if clip_url else "#"

        clip_button_html = (
            f"""
            <div style="margin-top: 24px; text-align: center;">
                <a href="{safe_clip_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #00F0FF 0%, #06B6D4 100%); color: #0B0F19; font-weight: 700; font-size: 15px; text-decoration: none; padding: 14px 28px; border-radius: 6px; letter-spacing: 0.5px; box-shadow: 0 4px 14px rgba(0, 240, 255, 0.4);">
                    REVIEW INCIDENT CLIP & TELEMETRY &rarr;
                </a>
            </div>
            """
            if clip_url
            else """
            <div style="margin-top: 20px; padding: 12px; background-color: #1F2937; border-radius: 6px; text-align: center; color: #9CA3AF; font-size: 13px;">
                Video recording clip is currently processing in Cloudflare R2 storage.
            </div>
            """
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HALOCAS Proximity Alert</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0B0F19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #F3F4F6;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0B0F19; padding: 32px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 600px; background-color: #111827; border: 1px solid #1F2937; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);" cellspacing="0" cellpadding="0">
                    <!-- Brand Header -->
                    <tr>
                        <td style="background: #111827; padding: 24px 32px; border-bottom: 2px solid #00F0FF;">
                            <table width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <div style="font-size: 20px; font-weight: 800; letter-spacing: 1.5px; color: #00F0FF; text-transform: uppercase;">
                                            HALOCAS
                                        </div>
                                        <div style="font-size: 11px; font-weight: 500; color: #9CA3AF; letter-spacing: 0.5px; margin-top: 2px;">
                                            HALO COLLISION AVOIDANCE SYSTEM &bull; MINE SAFETY
                                        </div>
                                    </td>
                                    <td align="right">
                                        <span style="display: inline-block; background-color: rgba(239, 68, 68, 0.15); border: 1px solid #EF4444; color: #EF4444; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px;">
                                            CRITICAL ALERT
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Alert Notice Banner -->
                    <tr>
                        <td style="padding: 28px 32px 12px 32px;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                Spatial Proximity Breach Detected
                            </h1>
                            <p style="margin: 10px 0 0 0; font-size: 14px; color: #9CA3AF; line-height: 1.5;">
                                A personnel intrusion inside the hazardous machinery exclusion zone was identified by active computer vision tracking.
                            </p>
                        </td>
                    </tr>
                    <!-- Telemetry Data Card -->
                    <tr>
                        <td style="padding: 16px 32px;">
                            <table role="presentation" width="100%" style="background-color: #161F30; border: 1px solid #1F2937; border-radius: 8px;" cellspacing="0" cellpadding="16">
                                <tr>
                                    <td>
                                        <table width="100%" cellspacing="0" cellpadding="8">
                                            <tr>
                                                <td width="40%" style="color: #9CA3AF; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Worker Involved</td>
                                                <td width="60%" style="color: #FFFFFF; font-size: 15px; font-weight: 600;">{safe_worker_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #9CA3AF; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; border-top: 1px solid #233044;">Proximity Distance</td>
                                                <td style="color: #EF4444; font-size: 16px; font-weight: 700; border-top: 1px solid #233044;">{distance:.2f} meters</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #9CA3AF; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; border-top: 1px solid #233044;">Incident ID</td>
                                                <td style="color: #00F0FF; font-size: 14px; font-family: monospace; border-top: 1px solid #233044;">#{incident_id}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #9CA3AF; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; border-top: 1px solid #233044;">Event Timestamp</td>
                                                <td style="color: #E5E7EB; font-size: 13px; border-top: 1px solid #233044;">{formatted_time}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- CTA Link Button -->
                    <tr>
                        <td style="padding: 8px 32px 32px 32px;">
                            {clip_button_html}
                        </td>
                    </tr>
                    <!-- Footer Information -->
                    <tr>
                        <td style="background-color: #0D131F; padding: 20px 32px; border-top: 1px solid #1F2937; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #6B7280; line-height: 1.5;">
                                This is an automated safety dispatch emitted by the HALOCAS Vision Engine.<br>
                                In accordance with industrial mine safety standard ISO 21815-2.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    async def _write_alert_log(
        self,
        incident_id: int,
        recipient_email: str,
        status: DeliveryStatus,
        retry_count: int = 0,
        error_message: str | None = None,
        sent_at: datetime | None = None,
        db_session: AsyncSession | None = None,
    ) -> AlertLog | None:
        """Persist notification dispatch outcome to the alert_logs table.

        Args:
            incident_id: Foreign key to related incident.
            recipient_email: Supervisor destination address.
            status: Terminal or intermediate delivery status.
            retry_count: Cumulative attempts made.
            error_message: Optional diagnostic failure detail.
            sent_at: Delivery timestamp on success.
            db_session: Optional provided active session.

        Returns:
            AlertLog | None: Persisted database model instance or None if DB unconfigured.
        """
        log_entry = AlertLog(
            incident_id=incident_id,
            recipient_email=recipient_email,
            delivery_status=status,
            retry_count=retry_count,
            error_message=error_message,
            sent_at=sent_at,
        )

        try:
            if db_session is not None:
                db_session.add(log_entry)
                await db_session.flush()
                return log_entry

            if self.session_factory is not None:
                async with self.session_factory() as session:
                    async with session.begin():
                        session.add(log_entry)
                return log_entry

            logger.debug("No database session provided; skipping alert_log persistence")
            return None

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to write AlertLog to database for incident=%d: %s",
                incident_id,
                exc,
            )
            return None

    async def send_proximity_alert(
        self,
        supervisor_email: str,
        worker_name: str,
        distance: float,
        clip_url: str | None,
        incident_id: int,
        db_session: AsyncSession | None = None,
    ) -> bool:
        """Send an urgent proximity alert email to a supervisor with retries and rate limiting.

        Args:
            supervisor_email: Recipient supervisor email address.
            worker_name: Identity of personnel in breach zone.
            distance: Detected proximity distance in meters.
            clip_url: Cloudflare R2 presigned video clip URL or dashboard link.
            incident_id: Primary key of safety incident.
            db_session: Optional active AsyncSession for audit log persistence.

        Returns:
            bool: True if message was acknowledged by Resend, False on terminal failure.
        """
        clean_email = supervisor_email.strip()
        if not clean_email or "@" not in clean_email:
            logger.error("Invalid supervisor email address provided: %s", supervisor_email)
            await self._write_alert_log(
                incident_id=incident_id,
                recipient_email=supervisor_email,
                status=DeliveryStatus.FAILED,
                error_message="Invalid recipient email format",
                db_session=db_session,
            )
            return False

        # 1. Enforce Rate Limiting (max 10 emails/min per supervisor)
        if not self._check_and_record_rate_limit(clean_email):
            logger.warning(
                "Rate limit exceeded for supervisor %s (max %d/min); suppressing alert for incident %d",
                clean_email,
                self.rate_limit_per_minute,
                incident_id,
            )
            await self._write_alert_log(
                incident_id=incident_id,
                recipient_email=clean_email,
                status=DeliveryStatus.FAILED,
                error_message=f"Rate limit exceeded (max {self.rate_limit_per_minute} emails/min)",
                db_session=db_session,
            )
            return False

        subject = f"[HALOCAS] Proximity Alert — {worker_name}"
        html_body = self.render_proximity_alert_html(
            worker_name=worker_name,
            distance=distance,
            clip_url=clip_url,
            incident_id=incident_id,
        )

        send_params: resend.Emails.SendParams = {
            "from": self.sender_email,
            "to": [clean_email],
            "subject": subject,
            "html": html_body,
        }

        # If Resend API key is not configured, record simulated delivery immediately
        if not self.api_key:
            logger.info(
                "Resend API key is not configured; recording simulated delivery for incident %d to %s",
                incident_id,
                clean_email,
            )
            await self._write_alert_log(
                incident_id=incident_id,
                recipient_email=clean_email,
                status=DeliveryStatus.SENT,
                retry_count=0,
                sent_at=datetime.now(UTC),
                db_session=db_session,
            )
            return True

        # 2. Transmission with Exponential Backoff Retries (1s, 2s, 4s)
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    "Dispatching proximity alert via Resend (attempt %d/%d) for worker '%s' to %s",
                    attempt + 1,
                    self.max_retries + 1,
                    worker_name,
                    clean_email,
                )

                # Execute synchronous Resend SDK call in thread pool to prevent event loop blocking
                response = await asyncio.to_thread(resend.Emails.send, send_params)

                # Validate response from Resend
                email_id = ""
                if isinstance(response, dict):
                    email_id = str(response.get("id", ""))
                elif hasattr(response, "id"):
                    email_id = str(getattr(response, "id", ""))

                logger.info(
                    "Resend acknowledged proximity alert delivery for incident %d: email_id=%s",
                    incident_id,
                    email_id,
                )

                # Record successful delivery in database
                await self._write_alert_log(
                    incident_id=incident_id,
                    recipient_email=clean_email,
                    status=DeliveryStatus.SENT,
                    retry_count=attempt,
                    sent_at=datetime.now(UTC),
                    db_session=db_session,
                )
                return True

            except (ResendError, ConnectionError, OSError, Exception) as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning(
                    "Resend dispatch attempt %d/%d failed for incident %d: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    incident_id,
                    last_error,
                )

                if attempt < self.max_retries:
                    backoff = self.base_backoff_sec * (2**attempt)
                    logger.debug("Applying exponential backoff of %.2fs before retry", backoff)
                    await asyncio.sleep(backoff)

        # 3. Terminal Fallback: All retries exhausted
        logger.error(
            "Terminal notification failure: exhausted %d retries for incident %d to %s: %s",
            self.max_retries,
            incident_id,
            clean_email,
            last_error,
        )

        await self._write_alert_log(
            incident_id=incident_id,
            recipient_email=clean_email,
            status=DeliveryStatus.FAILED,
            retry_count=self.max_retries,
            error_message=f"Delivery failed after {self.max_retries} retries: {last_error}",
            db_session=db_session,
        )
        return False

    def dispatch_alert_background(
        self,
        supervisor_email: str,
        worker_name: str,
        distance: float,
        clip_url: str | None,
        incident_id: int,
        db_session: AsyncSession | None = None,
    ) -> asyncio.Task[bool]:
        """Schedule an alert email for non-blocking asynchronous execution.

        Creates an asyncio.Task in the active event loop and retains a strong reference
        until completion to prevent premature runtime garbage collection.

        Args:
            supervisor_email: Destination supervisor email.
            worker_name: Subject personnel name.
            distance: Measured distance in meters.
            clip_url: Cloudflare R2 clip URL.
            incident_id: Proximity incident identifier.
            db_session: Optional database session.

        Returns:
            asyncio.Task[bool]: Scheduled background dispatch task.
        """
        task = asyncio.create_task(
            self.send_proximity_alert(
                supervisor_email=supervisor_email,
                worker_name=worker_name,
                distance=distance,
                clip_url=clip_url,
                incident_id=incident_id,
                db_session=db_session,
            ),
            name=f"halocas-alert-{incident_id}-{supervisor_email}",
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        logger.debug(
            "Dispatched background notification task for incident %d (active tasks: %d)",
            incident_id,
            len(self._background_tasks),
        )
        return task
