"""Safety State Machine for HALOCAS.

Evaluates monocular spatial proximity and trajectory vectors between heavy mining machinery
and workers on foot. Implements debounce filtering, boundary hysteresis, alert cooldown suppression,
biometric authorization overrides, and observability telemetry.
"""

import enum
import math
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Severity(enum.StrEnum):
    """Proximity hazard classifications."""

    SAFE = "SAFE"                          # Spatial buffer > warning distance (> 10m)
    WARNING = "WARNING"                    # Caution zone between critical and warning distance
    CRITICAL = "CRITICAL"                  # Immediate collision danger (< 3m or closing vector)
    CRITICAL_ALERT = "CRITICAL"            # Alias for CRITICAL compatibility
    AUTHORIZED_OVERRIDE = "AUTHORIZED_OVERRIDE"  # Critical alert suppressed for authorized mechanics


class SafetyEvent(BaseModel):
    """Structured telemetry event generated for worker-machinery proximity interactions."""

    timestamp: float = Field(..., description="Epoch or stream timestamp in seconds")
    machine_id: int = Field(..., description="Unique machinery identifier")
    worker_id: int = Field(..., description="Unique worker tracking identifier")
    distance_meters: float = Field(..., ge=0.0, description="Estimated Euclidean distance in meters")
    severity: Severity = Field(..., description="Hazard classification severity")
    closing_velocity: float = Field(default=0.0, description="Rate of distance reduction in meters/second")
    machine_speed: float = Field(default=0.0, ge=0.0, description="Estimated ground speed of equipment in meters/second")
    alert_suppressed: bool = Field(default=False, description="True if alert emission was suppressed by cooldown window")


class SafetyStateMachine:
    """State machine governing proximity transitions, debounce, cooldown, and hysteresis."""

    def __init__(
        self,
        critical_distance: float | None = None,
        warning_distance: float | None = None,
        pixels_per_meter: float | None = None,
        cooldown_seconds: int | None = None,
        debounce_frames: int = 3,
        hysteresis_m: float = 1.0,
    ) -> None:
        """Initialize SafetyStateMachine parameters from settings and arguments.

        Args:
            critical_distance: Critical threshold in meters (default from config: 3.0m).
            warning_distance: Warning threshold in meters (default from config: 10.0m).
            pixels_per_meter: Calibration constant (default from config: 20.0 px/m).
            cooldown_seconds: Cooldown window in seconds (default from config: 60s).
            debounce_frames: Number of consecutive critical frames required before triggering (default: 3).
            hysteresis_m: Distance buffer in meters required to drop from CRITICAL back to WARNING (default: 1.0m).
        """
        settings = get_settings()
        self.critical_distance: float = (
            critical_distance if critical_distance is not None else settings.SAFETY_CRITICAL_DISTANCE
        )
        self.warning_distance: float = (
            warning_distance if warning_distance is not None else settings.SAFETY_WARNING_DISTANCE
        )
        self.pixels_per_meter: float = (
            pixels_per_meter if pixels_per_meter is not None else settings.PIXELS_PER_METER
        )
        self.cooldown_seconds: float = float(
            cooldown_seconds if cooldown_seconds is not None else settings.ALERT_COOLDOWN_SECONDS
        )
        self.debounce_frames: int = max(1, debounce_frames)
        self.hysteresis_m: float = max(0.0, hysteresis_m)

        # Spatial tracking memory
        # previous_machine_boxes: machine_id -> (center_x, center_y, timestamp)
        self.previous_machine_boxes: dict[int, tuple[float, float, float]] = {}

        # previous_distances: (machine_id, worker_id) -> (distance_meters, timestamp)
        self.previous_distances: dict[tuple[int, int], tuple[float, float]] = {}

        # State tracking: (machine_id, worker_id) -> current Severity
        self.pair_states: dict[tuple[int, int], Severity] = {}

        # Debounce tracking: (machine_id, worker_id) -> consecutive critical frames count
        self.critical_frame_counts: dict[tuple[int, int], int] = {}

        # Cooldown tracking: (machine_id, worker_id) -> timestamp of last dispatched critical alert
        self.last_alert_times: dict[tuple[int, int], float] = {}

        # Observability metrics
        self.total_events_generated: int = 0
        self.last_critical_time: float | None = None

        logger.info(
            "Initialized SafetyStateMachine: critical=%.1fm, warning=%.1fm, ppm=%.1f, "
            "cooldown=%.1fs, debounce=%d frames, hysteresis=%.1fm",
            self.critical_distance,
            self.warning_distance,
            self.pixels_per_meter,
            self.cooldown_seconds,
            self.debounce_frames,
            self.hysteresis_m,
        )

    @staticmethod
    def _get_bottom_center(bbox: list[float] | tuple[float, ...]) -> tuple[float, float]:
        """Compute the ground-level bottom-center coordinate from [x1, y1, x2, y2]."""
        try:
            x1, _y1, x2, y2 = bbox[:4]
            return ((float(x1) + float(x2)) / 2.0, float(y2))
        except (ValueError, TypeError, IndexError):
            return (0.0, 0.0)

    @staticmethod
    def _get_center(bbox: list[float] | tuple[float, ...]) -> tuple[float, float]:
        """Compute spatial midpoint coordinate from [x1, y1, x2, y2]."""
        try:
            x1, y1, x2, y2 = bbox[:4]
            return ((float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0)
        except (ValueError, TypeError, IndexError):
            return (0.0, 0.0)

    def is_in_cooldown(self, machine_id: int, worker_id: int, timestamp: float) -> bool:
        """Check whether an alert for a given machine-worker pair is currently within cooldown."""
        pair_id = (machine_id, worker_id)
        last_alert = self.last_alert_times.get(pair_id)
        if last_alert is None:
            return False
        return (timestamp - last_alert) < self.cooldown_seconds

    def update(
        self,
        timestamp: float,
        machines: list[dict[str, Any]],
        workers: list[dict[str, Any]],
        frame: Any | None = None,
        face_verifier: Any | None = None,
        db_manager: Any | None = None,
    ) -> list[SafetyEvent]:
        """Process spatial updates for all detected machines and workers in the current frame.

        Calculates ground contact Euclidean distances, trajectory closing velocities,
        evaluates debounce state filters, checks boundary hysteresis, and issues SafetyEvents.

        Args:
            timestamp: Frame capture timestamp in seconds.
            machines: List of machine records containing 'id' and 'bbox' ([x1, y1, x2, y2]).
            workers: List of worker records containing 'id' and 'bbox' ([x1, y1, x2, y2]).
            frame: Optional video frame for facial biometric verification during critical events.
            face_verifier: Optional FaceVerifier instance for mechanic authorization checks.
            db_manager: Optional database manager interface retrieving registered worker embeddings.

        Returns:
            List[SafetyEvent]: List of generated safety evaluations for every active machine-worker pair.
        """
        events: list[SafetyEvent] = []

        if not machines or not workers:
            return events

        current_machine_ids: set[int] = set()
        current_pair_ids: set[tuple[int, int]] = set()

        for machine in machines:
            try:
                machine_id = int(machine.get("id", -1))
            except (ValueError, TypeError):
                continue

            m_bbox = machine.get("bbox")
            if machine_id < 0 or not m_bbox or len(m_bbox) < 4:
                continue

            current_machine_ids.add(machine_id)
            m_center = self._get_center(m_bbox)
            m_bottom_center = self._get_bottom_center(m_bbox)

            # 1. Compute machine speed in meters per second
            machine_speed_mps = 0.0
            if machine_id in self.previous_machine_boxes:
                prev_x, prev_y, prev_ts = self.previous_machine_boxes[machine_id]
                dt = timestamp - prev_ts
                if dt > 0.0:
                    pixel_dist = math.hypot(m_center[0] - prev_x, m_center[1] - prev_y)
                    dist_meters = pixel_dist / self.pixels_per_meter
                    machine_speed_mps = dist_meters / dt

            self.previous_machine_boxes[machine_id] = (m_center[0], m_center[1], timestamp)

            for worker in workers:
                try:
                    worker_id = int(worker.get("id", -1))
                except (ValueError, TypeError):
                    continue

                w_bbox = worker.get("bbox")
                if worker_id < 0 or not w_bbox or len(w_bbox) < 4:
                    continue

                pair_id = (machine_id, worker_id)
                current_pair_ids.add(pair_id)

                w_bottom_center = self._get_bottom_center(w_bbox)

                # 2. Monocular Euclidean ground-distance estimation
                pixel_dist = math.hypot(
                    m_bottom_center[0] - w_bottom_center[0],
                    m_bottom_center[1] - w_bottom_center[1],
                )
                current_distance_m = pixel_dist / self.pixels_per_meter

                # 3. Trajectory closing velocity (positive indicates convergence)
                closing_velocity = 0.0
                if pair_id in self.previous_distances:
                    prev_dist, prev_ts = self.previous_distances[pair_id]
                    dt = timestamp - prev_ts
                    if dt > 0.0:
                        closing_velocity = (prev_dist - current_distance_m) / dt

                self.previous_distances[pair_id] = (current_distance_m, timestamp)

                # 4. Evaluate Raw State Condition with Hysteresis
                prev_state = self.pair_states.get(pair_id, Severity.SAFE)
                raw_is_critical = False

                if prev_state == Severity.CRITICAL:
                    # HYSTERESIS: Once in CRITICAL, only drop back to WARNING if distance > critical + hysteresis
                    exit_threshold = self.critical_distance + self.hysteresis_m
                    if current_distance_m <= exit_threshold or (
                        current_distance_m < self.warning_distance and closing_velocity > 0.0
                    ):
                        raw_is_critical = True
                else:
                    # Normal entry into CRITICAL
                    if current_distance_m < self.critical_distance or (
                        current_distance_m < self.warning_distance and closing_velocity > 0.0
                    ):
                        raw_is_critical = True

                # 5. Apply Debounce Logic
                severity = Severity.SAFE
                if raw_is_critical:
                    count = self.critical_frame_counts.get(pair_id, 0) + 1
                    self.critical_frame_counts[pair_id] = count

                    if count >= self.debounce_frames:
                        severity = Severity.CRITICAL
                    else:
                        # Debounce pending: hold at WARNING if inside warning distance
                        severity = (
                            Severity.WARNING
                            if current_distance_m < self.warning_distance
                            else Severity.SAFE
                        )
                else:
                    # Reset debounce counter when condition clears
                    self.critical_frame_counts[pair_id] = 0
                    if current_distance_m < self.warning_distance:
                        severity = Severity.WARNING
                    else:
                        severity = Severity.SAFE

                # 6. Biometric Authorization Override for Critical Situations
                if (
                    severity == Severity.CRITICAL
                    and frame is not None
                    and face_verifier is not None
                    and db_manager is not None
                ):
                    try:
                        db_workers = (
                            db_manager.get_all_workers_with_embeddings()
                            if hasattr(db_manager, "get_all_workers_with_embeddings")
                            else []
                        )
                        matched_worker = face_verifier.verify(frame, w_bbox, db_workers)
                        if matched_worker and matched_worker.get("role") == "Authorized Mechanic":
                            severity = Severity.AUTHORIZED_OVERRIDE
                            logger.info(
                                "Authorized mechanic %s verified at machine %d. Suppressing critical alarm.",
                                matched_worker.get("name"),
                                machine_id,
                            )
                    except Exception as exc:
                        logger.error("Facial override verification encountered an error: %s", exc)

                # 7. Apply Cooldown Suppression on Critical Alerts
                alert_suppressed = False
                if severity == Severity.CRITICAL:
                    last_alert = self.last_alert_times.get(pair_id)
                    if last_alert is not None and (timestamp - last_alert) < self.cooldown_seconds:
                        alert_suppressed = True
                        logger.debug(
                            "Critical alert for pair %s suppressed under cooldown (%.1fs remaining)",
                            pair_id,
                            self.cooldown_seconds - (timestamp - last_alert),
                        )
                    else:
                        self.last_alert_times[pair_id] = timestamp
                        self.last_critical_time = timestamp

                self.pair_states[pair_id] = severity

                # 8. Produce Event and Increment Telemetry
                event = SafetyEvent(
                    timestamp=timestamp,
                    machine_id=machine_id,
                    worker_id=worker_id,
                    distance_meters=round(current_distance_m, 2),
                    severity=severity,
                    closing_velocity=round(closing_velocity, 2),
                    machine_speed=round(machine_speed_mps, 2),
                    alert_suppressed=alert_suppressed,
                )
                events.append(event)
                self.total_events_generated += 1

        # 9. Clean up stale tracking entries
        self.previous_machine_boxes = {
            k: v for k, v in self.previous_machine_boxes.items() if k in current_machine_ids
        }
        self.previous_distances = {
            k: v for k, v in self.previous_distances.items() if k in current_pair_ids
        }
        self.pair_states = {
            k: v for k, v in self.pair_states.items() if k in current_pair_ids
        }
        self.critical_frame_counts = {
            k: v for k, v in self.critical_frame_counts.items() if k in current_pair_ids
        }

        return events

    def reset(self) -> None:
        """Reset all internal state, tracking buffers, and debounce counters."""
        self.previous_machine_boxes.clear()
        self.previous_distances.clear()
        self.pair_states.clear()
        self.critical_frame_counts.clear()
        self.last_alert_times.clear()
        self.total_events_generated = 0
        self.last_critical_time = None
