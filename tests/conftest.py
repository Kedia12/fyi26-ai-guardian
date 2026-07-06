import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest

from dashboard.app import create_app
from guardian.db import GuardianDB

TEST_ADMIN_USER = "admin"
TEST_ADMIN_PASS = "adminpass123"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_ADMIN_USERNAME", TEST_ADMIN_USER)
    monkeypatch.setenv("GUARDIAN_ADMIN_PASSWORD", TEST_ADMIN_PASS)

    db_path = tmp_path / "test_guardian.db"
    db = GuardianDB(path=db_path)
    db.insert_alert({
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "severity": "WARNING",
        "confidence": 0.85,
        "reason_code": "PACKET_LOSS",
        "reason_text": "Test alert.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    })
    db.insert_alert({
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "severity": "CRITICAL",
        "confidence": 0.85,
        "reason_code": "LOW_BATTERY",
        "reason_text": "Test alert.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    })
    db.insert_telemetry({
        "timestamp_ms": 1000,
        "packet_id": 5,
        "node_id": "node_01",
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 1.0,
        "battery_voltage_v": 10.1,
        "low_power_flag": 0,
    })
    db.close()

    flask_app = create_app(db_path=str(db_path))
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Test client already logged in as the bootstrap admin."""
    c = app.test_client()
    c.post(
        "/api/login",
        json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS},
    )
    return c


@pytest.fixture
def anon_client(app):
    """Test client with no session — for testing unauthenticated access."""
    return app.test_client()
