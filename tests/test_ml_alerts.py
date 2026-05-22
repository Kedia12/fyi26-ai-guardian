import pytest
from unittest.mock import patch
from guardian.engine import GuardianEngine
from guardian.config import reload_config


def make_row(**overrides):
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 1.0,
        "gyro_x_dps": 0.1,
        "gyro_y_dps": 0.2,
        "gyro_z_dps": 0.3,
        "altitude_est_m": 50.0,
        "gps_lat_deg": 48.8566,
        "gps_lon_deg": 2.3522,
        "gps_speed_mps": 5.0,
        "satellite_count": 8,
        "gps_fix_status": 1,
        "battery_voltage_v": 11.8,
        "low_power_flag": 0,
        "temperature_c": 25.0,
        "pressure_hpa": 1013.0,
    }
    base.update(overrides)
    return base


def engine_with_score(score):
    """Return a GuardianEngine whose ML model always returns `score`."""
    engine = GuardianEngine()
    engine.ml_ready = True
    engine.ml.score_row = lambda row: score
    return engine


def test_ml_alert_generated_when_score_exceeds_threshold():
    engine = engine_with_score(0.5)
    alerts, anomaly_score = engine.process_row(make_row())
    ml_alerts = [a for a in alerts if a.get("reason_code") == "ML_ANOMALY"]
    assert len(ml_alerts) == 1


def test_ml_alert_not_generated_when_score_below_threshold():
    engine = engine_with_score(0.05)
    alerts, _ = engine.process_row(make_row())
    ml_alerts = [a for a in alerts if a.get("reason_code") == "ML_ANOMALY"]
    assert len(ml_alerts) == 0


def test_ml_alert_not_generated_when_score_equals_threshold():
    engine = engine_with_score(0.1)
    alerts, _ = engine.process_row(make_row())
    ml_alerts = [a for a in alerts if a.get("reason_code") == "ML_ANOMALY"]
    assert len(ml_alerts) == 0


def test_ml_alert_has_required_fields():
    engine = engine_with_score(0.5)
    alerts, _ = engine.process_row(make_row())
    ml_alert = next(a for a in alerts if a.get("reason_code") == "ML_ANOMALY")
    for field in ("timestamp_ms", "packet_id", "node_id", "severity",
                  "confidence", "reason_code", "reason_text",
                  "recommended_action", "alert_status"):
        assert field in ml_alert, f"Missing field: {field}"


def test_ml_alert_reason_code_is_ml_anomaly():
    engine = engine_with_score(0.5)
    alerts, _ = engine.process_row(make_row())
    ml_alert = next(a for a in alerts if a.get("reason_code") == "ML_ANOMALY")
    assert ml_alert["reason_code"] == "ML_ANOMALY"


def test_ml_alert_recommended_action():
    engine = engine_with_score(0.5)
    alerts, _ = engine.process_row(make_row())
    ml_alert = next(a for a in alerts if a.get("reason_code") == "ML_ANOMALY")
    assert ml_alert["recommended_action"] == "VERIFY_OPERATOR"


def test_ml_alert_confidence_is_between_zero_and_one():
    engine = engine_with_score(0.9)
    alerts, _ = engine.process_row(make_row())
    ml_alert = next(a for a in alerts if a.get("reason_code") == "ML_ANOMALY")
    assert 0.0 < ml_alert["confidence"] <= 0.99


def test_ml_alert_confidence_increases_with_higher_score():
    engine_low = engine_with_score(0.2)
    engine_high = engine_with_score(0.8)
    alerts_low, _ = engine_low.process_row(make_row())
    alerts_high, _ = engine_high.process_row(make_row())
    conf_low = next(a["confidence"] for a in alerts_low if a.get("reason_code") == "ML_ANOMALY")
    conf_high = next(a["confidence"] for a in alerts_high if a.get("reason_code") == "ML_ANOMALY")
    assert conf_high > conf_low


def test_ml_alert_severity_from_config():
    engine = engine_with_score(0.5)
    alerts, _ = engine.process_row(make_row())
    ml_alert = next(a for a in alerts if a.get("reason_code") == "ML_ANOMALY")
    assert ml_alert["severity"] in ("WARNING", "CRITICAL", "INFO")


def test_anomaly_score_returned_when_ml_ready():
    engine = engine_with_score(0.5)
    _, anomaly_score = engine.process_row(make_row())
    assert anomaly_score == pytest.approx(0.5)


def test_no_ml_alert_when_ml_not_ready():
    engine = GuardianEngine()
    engine.ml_ready = False
    alerts, anomaly_score = engine.process_row(make_row())
    ml_alerts = [a for a in alerts if a.get("reason_code") == "ML_ANOMALY"]
    assert len(ml_alerts) == 0
    assert anomaly_score is None


def test_ml_score_stored_in_row():
    engine = engine_with_score(0.5)
    row = make_row()
    engine.process_row(row)
    assert "ml_anomaly_score" in row
    assert row["ml_anomaly_score"] == pytest.approx(0.5)
