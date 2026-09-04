"""Unit tests for the SafetyStateMachine proximity and trajectory engine."""

from typing import Any
from unittest.mock import MagicMock

from app.core.state_machine import SafetyStateMachine, Severity


def test_state_safe_distance() -> None:
    """Verify worker outside warning boundary (> 10m) returns SAFE state."""
    sm = SafetyStateMachine(critical_distance=3.0, warning_distance=10.0, pixels_per_meter=100.0)

    # Machine bottom-center: (50.0, 100.0)
    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    # Worker bottom-center: (1550.0, 100.0) -> Distance: 15.0 meters
    workers = [{"id": 2, "bbox": [1500.0, 0.0, 1600.0, 100.0]}]

    events = sm.update(timestamp=1.0, machines=machines, workers=workers)
    assert len(events) == 1
    assert events[0].severity == Severity.SAFE
    assert events[0].distance_meters == 15.0
    assert events[0].alert_suppressed is False


def test_state_warning_distance() -> None:
    """Verify stationary worker in caution zone (3m to 10m) returns WARNING state."""
    sm = SafetyStateMachine(critical_distance=3.0, warning_distance=10.0, pixels_per_meter=100.0)

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    # Distance: (550.0 - 50.0) / 100.0 = 5.0 meters
    workers = [{"id": 2, "bbox": [500.0, 0.0, 600.0, 100.0]}]

    events = sm.update(timestamp=1.0, machines=machines, workers=workers)
    assert len(events) == 1
    assert events[0].severity == Severity.WARNING
    assert events[0].distance_meters == 5.0
    assert events[0].alert_suppressed is False


def test_debounce_logic() -> None:
    """Verify debounce requires N consecutive critical frames before escalating to CRITICAL."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        debounce_frames=3,
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    # Distance: (250.0 - 50.0) / 100.0 = 2.0 meters (< 3.0m critical)
    workers = [{"id": 2, "bbox": [200.0, 0.0, 300.0, 100.0]}]

    # Frame 1: First detection at 2.0m (held in WARNING during debounce)
    e1 = sm.update(timestamp=1.0, machines=machines, workers=workers)
    assert e1[0].severity == Severity.WARNING

    # Frame 2: Second consecutive critical frame (still held in WARNING)
    e2 = sm.update(timestamp=1.1, machines=machines, workers=workers)
    assert e2[0].severity == Severity.WARNING

    # Frame 3: Third consecutive critical frame -> Triggers CRITICAL!
    e3 = sm.update(timestamp=1.2, machines=machines, workers=workers)
    assert e3[0].severity == Severity.CRITICAL
    assert e3[0].alert_suppressed is False


def test_debounce_reset_on_cleared_condition() -> None:
    """Verify debounce counter resets to 0 if a safe frame intervenes."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        debounce_frames=3,
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    crit_workers = [{"id": 2, "bbox": [200.0, 0.0, 300.0, 100.0]}]  # 2.0m
    safe_workers = [{"id": 2, "bbox": [1500.0, 0.0, 1600.0, 100.0]}]  # 15.0m

    # Frame 1 & 2: Critical proximity
    sm.update(timestamp=1.0, machines=machines, workers=crit_workers)
    sm.update(timestamp=1.1, machines=machines, workers=crit_workers)
    assert sm.critical_frame_counts.get((1, 2)) == 2

    # Frame 3: Worker moves away to safe distance -> Clears debounce count
    e_safe = sm.update(timestamp=1.2, machines=machines, workers=safe_workers)
    assert e_safe[0].severity == Severity.SAFE
    assert sm.critical_frame_counts.get((1, 2)) == 0

    # Frame 4: Returns to 2.0m -> Must restart debounce cycle
    e_restart = sm.update(timestamp=1.3, machines=machines, workers=crit_workers)
    assert e_restart[0].severity == Severity.WARNING
    assert sm.critical_frame_counts.get((1, 2)) == 1


def test_cooldown_duplicate_suppression() -> None:
    """Verify alerts for the same machine-worker pair are suppressed during cooldown."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        cooldown_seconds=60,
        debounce_frames=1,
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    workers = [{"id": 2, "bbox": [200.0, 0.0, 300.0, 100.0]}]  # 2.0m

    # Initial Alert at t=10.0s
    e1 = sm.update(timestamp=10.0, machines=machines, workers=workers)
    assert e1[0].severity == Severity.CRITICAL
    assert e1[0].alert_suppressed is False
    assert sm.is_in_cooldown(1, 2, timestamp=10.0) is True

    # 15 seconds later (t=25.0s) -> Within 60s cooldown window -> Alert suppressed
    e2 = sm.update(timestamp=25.0, machines=machines, workers=workers)
    assert e2[0].severity == Severity.CRITICAL
    assert e2[0].alert_suppressed is True
    assert sm.is_in_cooldown(1, 2, timestamp=25.0) is True

    # 70 seconds later (t=80.0s) -> Cooldown expired -> New alert issued!
    e3 = sm.update(timestamp=80.0, machines=machines, workers=workers)
    assert e3[0].severity == Severity.CRITICAL
    assert e3[0].alert_suppressed is False


def test_hysteresis_boundary_stabilization() -> None:
    """Verify hysteresis prevents oscillation by requiring critical + 1.0m to exit CRITICAL."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        debounce_frames=1,
        hysteresis_m=1.0,  # Exit boundary is 3.0 + 1.0 = 4.0 meters
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]

    # Step 1: Enter CRITICAL at 2.5 meters
    w_2_5m = [{"id": 2, "bbox": [250.0, 0.0, 350.0, 100.0]}]
    e1 = sm.update(timestamp=1.0, machines=machines, workers=w_2_5m)
    assert e1[0].severity == Severity.CRITICAL
    assert e1[0].distance_meters == 2.5

    # Step 2: Distance increases to 3.5 meters (> 3.0m, but <= 4.0m hysteresis threshold)
    # Without hysteresis, this would oscillate to WARNING. With hysteresis, it remains CRITICAL.
    w_3_5m = [{"id": 2, "bbox": [350.0, 0.0, 450.0, 100.0]}]
    e2 = sm.update(timestamp=2.0, machines=machines, workers=w_3_5m)
    assert e2[0].severity == Severity.CRITICAL
    assert e2[0].distance_meters == 3.5

    # Step 3: Distance increases to 4.2 meters (> 4.0m hysteresis threshold)
    # Exits critical state into WARNING.
    w_4_2m = [{"id": 2, "bbox": [420.0, 0.0, 520.0, 100.0]}]
    e3 = sm.update(timestamp=3.0, machines=machines, workers=w_4_2m)
    assert e3[0].severity == Severity.WARNING
    assert e3[0].distance_meters == 4.2


def test_closing_trajectory_computation() -> None:
    """Verify closing velocity computation and early escalation for approaching personnel."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        debounce_frames=1,
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]

    # Frame 1 (t=1.0s): Worker at 5.0m
    w_frame1 = [{"id": 2, "bbox": [500.0, 0.0, 600.0, 100.0]}]
    e1 = sm.update(timestamp=1.0, machines=machines, workers=w_frame1)
    assert e1[0].severity == Severity.WARNING
    assert e1[0].closing_velocity == 0.0

    # Frame 2 (t=2.0s): Worker advances to 4.0m (dt=1.0s, delta_d=-1.0m -> closing_velocity = +1.0 m/s)
    # Moving closer inside the warning buffer triggers CRITICAL danger
    w_frame2 = [{"id": 2, "bbox": [400.0, 0.0, 500.0, 100.0]}]
    e2 = sm.update(timestamp=2.0, machines=machines, workers=w_frame2)
    assert e2[0].closing_velocity == 1.0
    assert e2[0].severity == Severity.CRITICAL


def test_authorized_override_state() -> None:
    """Verify critical alert is converted to AUTHORIZED_OVERRIDE for recognized mechanics."""
    sm = SafetyStateMachine(
        critical_distance=3.0,
        warning_distance=10.0,
        pixels_per_meter=100.0,
        debounce_frames=1,
    )

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    workers = [{"id": 2, "bbox": [200.0, 0.0, 300.0, 100.0]}]  # 2.0m

    mock_face_verifier = MagicMock()
    mock_face_verifier.verify.return_value = {
        "id": 2,
        "name": "Marcus Vance",
        "role": "Authorized Mechanic",
        "confidence": 0.98,
    }

    mock_db_manager = MagicMock()
    mock_db_manager.get_all_workers_with_embeddings.return_value = [{"id": 2, "name": "Marcus Vance"}]

    dummy_frame = MagicMock()

    events = sm.update(
        timestamp=1.0,
        machines=machines,
        workers=workers,
        frame=dummy_frame,
        face_verifier=mock_face_verifier,
        db_manager=mock_db_manager,
    )

    assert len(events) == 1
    assert events[0].severity == Severity.AUTHORIZED_OVERRIDE
    mock_face_verifier.verify.assert_called_once()


def test_edge_cases_empty_and_invalid_inputs() -> None:
    """Verify graceful handling of empty lists, missing keys, and invalid bounding boxes."""
    sm = SafetyStateMachine()

    # Empty inputs
    assert sm.update(timestamp=1.0, machines=[], workers=[]) == []
    assert sm.update(timestamp=1.0, machines=[{"id": 1, "bbox": [0, 0, 10, 10]}], workers=[]) == []
    assert sm.update(timestamp=1.0, machines=[], workers=[{"id": 1, "bbox": [0, 0, 10, 10]}]) == []

    # Corrupted / invalid bounding boxes
    bad_machines: list[dict[str, Any]] = [
        {"id": 1, "bbox": []},
        {"id": 2, "bbox": [0, 0]},
        {"id": 3, "bbox": "invalid"},
        {"id": "not_an_int", "bbox": [0, 0, 10, 10]},
    ]
    bad_workers: list[dict[str, Any]] = [
        {"id": 1, "bbox": None},
        {"id": 2, "bbox": [10, 20]},
    ]
    assert sm.update(timestamp=1.0, machines=bad_machines, workers=bad_workers) == []


def test_observability_and_reset() -> None:
    """Verify telemetry tracking of generated events and reset behavior."""
    sm = SafetyStateMachine(debounce_frames=1, pixels_per_meter=100.0)

    machines = [{"id": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}]
    workers = [{"id": 2, "bbox": [200.0, 0.0, 300.0, 100.0]}]

    assert sm.total_events_generated == 0
    assert sm.last_critical_time is None

    sm.update(timestamp=5.0, machines=machines, workers=workers)
    assert sm.total_events_generated == 1
    assert sm.last_critical_time == 5.0

    sm.reset()
    assert sm.total_events_generated == 0
    assert sm.last_critical_time is None
    assert len(sm.previous_distances) == 0
