import pytest
from guardian.db import GuardianDB


def make_alert(**overrides):
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "severity": "WARNING",
        "confidence": 0.85,
        "reason_code": "TEST_ALERT",
        "reason_text": "Test alert.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    }
    base.update(overrides)
    return base


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
        "battery_voltage_v": 11.8,
        "low_power_flag": 0,
    }
    base.update(overrides)
    return base


def test_db_creates_file(tmp_path):
    db_path = tmp_path / "guardian.db"
    db = GuardianDB(path=db_path)
    db.close()
    assert db_path.exists()


def test_db_creates_parent_directories(tmp_path):
    db_path = tmp_path / "a" / "b" / "guardian.db"
    db = GuardianDB(path=db_path)
    db.close()
    assert db_path.exists()


def test_insert_telemetry_returns_id(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    row_id = db.insert_telemetry(make_row())
    db.close()
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_insert_telemetry_increments_ids(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    id1 = db.insert_telemetry(make_row(packet_id=1))
    id2 = db.insert_telemetry(make_row(packet_id=2))
    db.close()
    assert id2 > id1


def test_insert_alert_returns_id(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    alert_id = db.insert_alert(make_alert())
    db.close()
    assert isinstance(alert_id, int)
    assert alert_id >= 1


def test_insert_alert_ml_source_flag(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_alert(make_alert(reason_code="ML_ANOMALY"), ml_source=True)
    alerts = db.get_recent_alerts(limit=1)
    db.close()
    assert alerts[0]["ml_source"] == 1


def test_insert_alert_rule_source_flag(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_alert(make_alert(), ml_source=False)
    alerts = db.get_recent_alerts(limit=1)
    db.close()
    assert alerts[0]["ml_source"] == 0


def test_get_alert_by_id_returns_correct_record(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    alert_id = db.insert_alert(make_alert(reason_code="FIND_ME"))
    record = db.get_alert_by_id(alert_id)
    db.close()
    assert record is not None
    assert record["reason_code"] == "FIND_ME"


def test_get_alert_by_id_returns_none_for_missing(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    result = db.get_alert_by_id(99999)
    db.close()
    assert result is None


def test_update_alert_status(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    alert_id = db.insert_alert(make_alert())
    db.update_alert_status(alert_id, "acknowledged")
    record = db.get_alert_by_id(alert_id)
    db.close()
    assert record["alert_status"] == "acknowledged"


def test_get_recent_alerts_ordering(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_alert(make_alert(reason_code="FIRST"))
    db.insert_alert(make_alert(reason_code="SECOND"))
    db.insert_alert(make_alert(reason_code="THIRD"))
    alerts = db.get_recent_alerts(limit=3)
    db.close()
    assert alerts[0]["reason_code"] == "THIRD"


def test_get_recent_alerts_respects_limit(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    for i in range(10):
        db.insert_alert(make_alert(reason_code=f"CODE_{i}"))
    alerts = db.get_recent_alerts(limit=3)
    db.close()
    assert len(alerts) == 3


def test_get_recent_telemetry_returns_latest(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_telemetry(make_row(packet_id=1))
    db.insert_telemetry(make_row(packet_id=2))
    rows = db.get_recent_telemetry(limit=1)
    db.close()
    assert rows[0]["packet_id"] == 2


def test_insert_operator_action_returns_id(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    alert_id = db.insert_alert(make_alert())
    action_id = db.insert_operator_action(
        {"alert_id": alert_id, "action_type": "acknowledge", "operator_note": "OK"}
    )
    db.close()
    assert isinstance(action_id, int)
    assert action_id >= 1


def test_context_manager_closes_connection(tmp_path):
    with GuardianDB(path=tmp_path / "g.db") as db:
        db.insert_alert(make_alert())
    assert db._conn is None


def test_default_alert_status_is_active(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_alert(make_alert())
    alerts = db.get_recent_alerts(limit=1)
    db.close()
    assert alerts[0]["alert_status"] == "active"


def test_inserted_at_is_populated(tmp_path):
    db = GuardianDB(path=tmp_path / "g.db")
    db.insert_alert(make_alert())
    alerts = db.get_recent_alerts(limit=1)
    db.close()
    assert alerts[0]["inserted_at"] is not None
    assert "T" in alerts[0]["inserted_at"]
