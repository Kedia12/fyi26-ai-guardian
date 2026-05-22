# Phase 4 — ML Alert Integration
**Fixes Gap 5: The Isolation Forest score is computed but never creates a structured alert**

---

## Why This Is a Problem

Right now the engine calls `self.ml.score_row(row)`, gets back a float like `0.23`, and prints it to the console as raw text. That float is never wrapped into an alert dict, never exported to JSON, never saved to the database, and never shown on the dashboard. It is a dead-end number.

This phase closes that gap. When the ML score exceeds a configurable threshold, the engine builds a proper `ML_ANOMALY` alert using the same `build_alert()` function that every other alert uses. From that point on, the ML alert flows through all the same pipelines: JSON export, database persistence, dashboard display, and operator actions.

---

## Prerequisites

- Phase 1 (config) — the threshold and severity come from `guardian_config.yaml`
- Phase 2 (JSON export) — ML alerts will be automatically exported
- Phase 3 (database) — ML alerts will be automatically persisted

---

## Files You Will Modify

```
guardian/engine.py               ← add ML alert generation logic (~15 lines)
```

## Files You Will Create

```
tests/test_ml_alerts.py          ← 5 tests verifying ML alert behaviour
```

---

## Step 1 — Understand the Current `engine.py` Flow

Open `guardian/engine.py` and find the `process_row()` method. After your changes from Phase 2 and 3, it currently looks roughly like this:

```python
def process_row(self, row):
    alerts = []

    # Rule checks (9 checks)
    alerts += check_packet_loss(self.prev_row, row)
    alerts += check_out_of_order_packet(self.prev_row, row)
    # ... all other rule checks ...

    # ML scoring
    anomaly_score = self.ml.score_row(row)

    # Update previous row
    self.prev_row = row

    # DB persistence
    if self.db is not None:
        self.db.insert_telemetry(row)
        for alert in alerts:
            self.db.insert_alert(alert, ...)

    # JSON export
    if self.exporter:
        self.exporter.write_batch(alerts, row)

    return alerts, anomaly_score
```

The problem is the line `anomaly_score = self.ml.score_row(row)`. The score is computed but nothing happens with it.

---

## Step 2 — Understand the Confidence Formula

When the ML model produces a score of, say, `0.45`, what confidence value should the alert have?

The formula used is:

```
confidence = score / (score + 1.0)
```

This maps any positive score into the range `(0.0, 1.0)`:
- Score `0.0` → confidence `0.0`
- Score `0.1` → confidence `0.091`
- Score `0.5` → confidence `0.333`
- Score `1.0` → confidence `0.500`
- Score `9.0` → confidence `0.900`
- Score `∞` → confidence approaches `1.0`

It is bounded (never reaches 1.0), monotonically increasing (higher score = higher confidence), and does not require any additional parameters. The `min(..., 0.99)` cap ensures the value stays strictly below 1.0.

---

## Step 3 — Add Imports to `guardian/engine.py`

Open `guardian/engine.py`. At the top of the file, check whether these imports are already present. If not, add them:

```python
from guardian.alerts import build_alert
from guardian.config import get_ml_param
```

---

## Step 4 — Add ML Alert Logic to `process_row()`

Find the line in `process_row()` where the ML score is computed:

```python
    anomaly_score = self.ml.score_row(row)
```

Directly after this line, add the following block. Do not change anything else:

```python
    # If the ML score exceeds the configured threshold, convert it into a
    # structured ML_ANOMALY alert using the same build_alert() function that
    # all other alerts use. This ensures ML alerts flow through all downstream
    # pipelines (JSON export, database, dashboard) automatically.
    if anomaly_score is not None:
        threshold = get_ml_param("alert_threshold", 0.1)
        if anomaly_score > threshold:
            # Map the raw score to a (0, 1) confidence value.
            # score / (score + 1) is monotonically increasing and always < 1.
            confidence = min(anomaly_score / (anomaly_score + 1.0), 0.99)

            ml_alert = build_alert(
                row=row,
                severity=get_ml_param("alert_severity", "WARNING"),
                confidence=round(confidence, 4),
                reason_code="ML_ANOMALY",
                reason_text=(
                    f"Isolation Forest anomaly score {anomaly_score:.4f} "
                    f"exceeded threshold {threshold:.4f}. "
                    f"Row is statistically inconsistent with normal flight data."
                ),
                recommended_action="VERIFY_OPERATOR",
            )
            alerts.append(ml_alert)
```

That is the entire change to `engine.py`. The alert is appended to the `alerts` list before the DB and export calls, so it will be persisted and exported automatically.

---

## Step 5 — Create `tests/test_ml_alerts.py`

Create the file `tests/test_ml_alerts.py` with the following content.

```python
import pytest
from pathlib import Path
from guardian.engine import GuardianEngine
from guardian.schemas import validate_alert
import guardian.config as cfg


# ---------------------------------------------------------------------------
# Helper: a complete telemetry row for testing
# ---------------------------------------------------------------------------

def make_row(**overrides):
    """Return a complete valid telemetry row dict."""
    row = {
        "timestamp_ms": 1000, "packet_id": 1, "node_id": "node_01",
        "accel_x_g": 0.01, "accel_y_g": 0.02, "accel_z_g": 1.0,
        "gyro_x_dps": 0.1, "gyro_y_dps": 0.2, "gyro_z_dps": 0.3,
        "temperature_c": 25.0, "pressure_hpa": 1013.0, "altitude_est_m": 10.0,
        "battery_voltage_v": 11.8, "low_power_flag": 0,
        "gps_lat_deg": 43.5, "gps_lon_deg": -79.3, "gps_alt_m": 10.0,
        "gps_speed_mps": 5.0, "gps_fix_status": 1, "satellite_count": 8,
        "link_status": "ok", "mode_state": "AUTO",
    }
    row.update(overrides)
    return row


def make_extreme_row():
    """Return a row with extreme values that should always trigger ML_ANOMALY."""
    return make_row(
        accel_x_g=100.0,      # extremely high acceleration
        accel_y_g=-100.0,
        accel_z_g=100.0,
        gyro_x_dps=5000.0,    # extremely high rotation
        battery_voltage_v=1.0, # extremely low battery
        gps_speed_mps=999.0,  # impossible speed
        altitude_est_m=50000.0, # stratospheric altitude
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ml_alert_appears_in_process_row_when_score_exceeds_threshold(tmp_path):
    """process_row() must include an ML_ANOMALY alert for extreme rows.

    We use a very low threshold (0.0) via a temporary config so that even
    modest ML scores trigger an alert, making the test deterministic.
    """
    # Write a temp config with threshold=0.0 so any positive score fires
    config_content = """
rules:
  packet_loss_gap_ms: 200
  battery_warning_v: 10.5
  battery_critical_v: 10.2
  gps_jump_threshold_deg: 0.001
  gps_speed_jump_mps: 15.0
  min_satellites: 4
  gps_imu_accel_mag_threshold: 0.2
  gps_imu_gyro_mag_threshold: 3.0
ml:
  n_estimators: 100
  contamination: 0.05
  random_state: 42
  alert_threshold: 0.0
  alert_severity: WARNING
  alert_confidence: 0.75
logging:
  json_export_enabled: false
database:
  enabled: false
ingestion:
  mode: replay
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content, encoding="utf-8")
    cfg.reload_config(config_file)

    engine = GuardianEngine()

    # Feed a normal row first so the ML model has a prior_row reference
    engine.process_row(make_row(packet_id=1))

    # Now feed the extreme row — ML score should be very high
    alerts, score = engine.process_row(make_extreme_row())

    reason_codes = [a["reason_code"] for a in alerts]
    assert "ML_ANOMALY" in reason_codes, (
        f"Expected ML_ANOMALY in alerts but got: {reason_codes}. "
        f"ML score was: {score}"
    )


def test_ml_alert_passes_schema_validation(tmp_path):
    """The ML_ANOMALY alert dict must pass validate_alert()."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rules:\n  packet_loss_gap_ms: 200\n"
        "  battery_warning_v: 10.5\n  battery_critical_v: 10.2\n"
        "  gps_jump_threshold_deg: 0.001\n  gps_speed_jump_mps: 15.0\n"
        "  min_satellites: 4\n  gps_imu_accel_mag_threshold: 0.2\n"
        "  gps_imu_gyro_mag_threshold: 3.0\n"
        "ml:\n  n_estimators: 100\n  contamination: 0.05\n"
        "  random_state: 42\n  alert_threshold: 0.0\n"
        "  alert_severity: WARNING\n  alert_confidence: 0.75\n"
        "logging:\n  json_export_enabled: false\n"
        "database:\n  enabled: false\n"
        "ingestion:\n  mode: replay\n",
        encoding="utf-8",
    )
    cfg.reload_config(config_file)

    engine = GuardianEngine()
    engine.process_row(make_row(packet_id=1))
    alerts, _ = engine.process_row(make_extreme_row())

    ml_alerts = [a for a in alerts if a["reason_code"] == "ML_ANOMALY"]
    assert len(ml_alerts) > 0, "No ML_ANOMALY alert was generated."

    for alert in ml_alerts:
        assert validate_alert(alert), (
            f"ML_ANOMALY alert failed schema validation: {alert}"
        )


def test_ml_alert_not_generated_when_score_below_threshold(tmp_path):
    """No ML_ANOMALY alert when the threshold is set very high."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rules:\n  packet_loss_gap_ms: 200\n"
        "  battery_warning_v: 10.5\n  battery_critical_v: 10.2\n"
        "  gps_jump_threshold_deg: 0.001\n  gps_speed_jump_mps: 15.0\n"
        "  min_satellites: 4\n  gps_imu_accel_mag_threshold: 0.2\n"
        "  gps_imu_gyro_mag_threshold: 3.0\n"
        "ml:\n  n_estimators: 100\n  contamination: 0.05\n"
        "  random_state: 42\n  alert_threshold: 9999.0\n"  # impossibly high
        "  alert_severity: WARNING\n  alert_confidence: 0.75\n"
        "logging:\n  json_export_enabled: false\n"
        "database:\n  enabled: false\n"
        "ingestion:\n  mode: replay\n",
        encoding="utf-8",
    )
    cfg.reload_config(config_file)

    engine = GuardianEngine()
    engine.process_row(make_row(packet_id=1))
    alerts, _ = engine.process_row(make_extreme_row())

    reason_codes = [a["reason_code"] for a in alerts]
    assert "ML_ANOMALY" not in reason_codes, (
        "ML_ANOMALY alert must not be generated when threshold is 9999."
    )


def test_ml_alert_severity_comes_from_config(tmp_path):
    """The ML_ANOMALY alert severity must match the config value."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rules:\n  packet_loss_gap_ms: 200\n"
        "  battery_warning_v: 10.5\n  battery_critical_v: 10.2\n"
        "  gps_jump_threshold_deg: 0.001\n  gps_speed_jump_mps: 15.0\n"
        "  min_satellites: 4\n  gps_imu_accel_mag_threshold: 0.2\n"
        "  gps_imu_gyro_mag_threshold: 3.0\n"
        "ml:\n  n_estimators: 100\n  contamination: 0.05\n"
        "  random_state: 42\n  alert_threshold: 0.0\n"
        "  alert_severity: CRITICAL\n"  # <-- set to CRITICAL
        "  alert_confidence: 0.75\n"
        "logging:\n  json_export_enabled: false\n"
        "database:\n  enabled: false\n"
        "ingestion:\n  mode: replay\n",
        encoding="utf-8",
    )
    cfg.reload_config(config_file)

    engine = GuardianEngine()
    engine.process_row(make_row(packet_id=1))
    alerts, _ = engine.process_row(make_extreme_row())

    ml_alerts = [a for a in alerts if a["reason_code"] == "ML_ANOMALY"]
    assert len(ml_alerts) > 0, "No ML_ANOMALY alert was generated."
    assert ml_alerts[0]["severity"] == "CRITICAL"


def test_ml_alert_confidence_is_between_zero_and_one(tmp_path):
    """The ML_ANOMALY confidence value must be in the range [0.0, 1.0)."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rules:\n  packet_loss_gap_ms: 200\n"
        "  battery_warning_v: 10.5\n  battery_critical_v: 10.2\n"
        "  gps_jump_threshold_deg: 0.001\n  gps_speed_jump_mps: 15.0\n"
        "  min_satellites: 4\n  gps_imu_accel_mag_threshold: 0.2\n"
        "  gps_imu_gyro_mag_threshold: 3.0\n"
        "ml:\n  n_estimators: 100\n  contamination: 0.05\n"
        "  random_state: 42\n  alert_threshold: 0.0\n"
        "  alert_severity: WARNING\n  alert_confidence: 0.75\n"
        "logging:\n  json_export_enabled: false\n"
        "database:\n  enabled: false\n"
        "ingestion:\n  mode: replay\n",
        encoding="utf-8",
    )
    cfg.reload_config(config_file)

    engine = GuardianEngine()
    engine.process_row(make_row(packet_id=1))
    alerts, _ = engine.process_row(make_extreme_row())

    ml_alerts = [a for a in alerts if a["reason_code"] == "ML_ANOMALY"]
    assert len(ml_alerts) > 0

    confidence = ml_alerts[0]["confidence"]
    assert 0.0 <= confidence < 1.0, (
        f"Confidence {confidence} is outside the valid range [0.0, 1.0)."
    )
```

---

## Step 6 — Run Tests

```bash
# Run the new ML alert tests
pytest tests/test_ml_alerts.py -v
```

Expected: all 5 tests pass.

```bash
# Run the full suite
pytest -q
```

Expected: zero failures.

---

## Step 7 — Verify End-to-End in Console

```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

You should now see `ML_ANOMALY` alerts appearing in the output:
```
[WARNING] ML_ANOMALY | confidence=0.4321 | action=VERIFY_OPERATOR | status=active
```

---

## Step 8 — Verify ML Alerts Appear in Metrics

```bash
python -m guardian.metrics
```

Open `results/metrics/scenario_metrics.csv`. In the `observed_reason_codes` column for `combined_fault.csv`, you should see `ML_ANOMALY` listed among the other reason codes.

---

## Checklist — Phase 4 Complete When:

- [ ] `guardian/engine.py` imports `build_alert` from `guardian.alerts`
- [ ] `guardian/engine.py` imports `get_ml_param` from `guardian.config`
- [ ] `guardian/engine.py` `process_row()` has the ML_ANOMALY alert generation block
- [ ] The confidence formula `min(score / (score + 1.0), 0.99)` is used
- [ ] `tests/test_ml_alerts.py` exists with 5 tests, all passing
- [ ] `python -m guardian.main data/scenarios/combined_fault.csv` shows `[WARNING] ML_ANOMALY`
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
guardian/
└── engine.py                    ← MODIFIED — ~15 lines added in process_row()

tests/
└── test_ml_alerts.py            ← NEW — 5 ML alert tests
```

---

## Proceed to Phase 5 →

Phase 5 adds ground-truth labels per scenario and computes precision, recall, F1, and detection latency. Now that ML_ANOMALY is a real alert, Phase 5 metrics will include ML performance automatically.
