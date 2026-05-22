import json
import pytest
from dashboard.app import create_app
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
        "battery_voltage_v": 11.8,
        "low_power_flag": 0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test_guardian.db"
    db = GuardianDB(path=db_path)
    db.insert_alert(make_alert(reason_code="PACKET_LOSS", severity="WARNING"))
    db.insert_alert(make_alert(reason_code="LOW_BATTERY", severity="CRITICAL"))
    db.insert_telemetry(make_row(packet_id=5, battery_voltage_v=10.1))
    db.close()

    flask_app = create_app(db_path=str(db_path))
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── index page ────────────────────────────────────────────────────────────────

def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_active_alerts(client):
    response = client.get("/")
    assert b"PACKET_LOSS" in response.data or b"LOW_BATTERY" in response.data


def test_index_shows_telemetry_panel(client):
    response = client.get("/")
    assert b"Live Telemetry" in response.data


def test_index_shows_alert_panels(client):
    response = client.get("/")
    assert b"Active Alerts" in response.data
    assert b"Alert History" in response.data


# ── /api/alerts ───────────────────────────────────────────────────────────────

def test_api_alerts_returns_200(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200


def test_api_alerts_returns_json_list(client):
    response = client.get("/api/alerts")
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_api_alerts_contains_expected_fields(client):
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    assert len(alerts) >= 1
    for field in ("id", "severity", "reason_code", "alert_status"):
        assert field in alerts[0]


def test_api_alerts_limit_param(client):
    response = client.get("/api/alerts?limit=1")
    alerts = json.loads(response.data)
    assert len(alerts) <= 1


# ── /api/telemetry ────────────────────────────────────────────────────────────

def test_api_telemetry_returns_200(client):
    response = client.get("/api/telemetry")
    assert response.status_code == 200


def test_api_telemetry_returns_latest_row(client):
    response = client.get("/api/telemetry")
    data = json.loads(response.data)
    assert data is not None
    assert data["packet_id"] == 5


# ── /api/alerts/<id> ──────────────────────────────────────────────────────────

def test_api_alert_by_id_returns_200(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    response = client.get(f"/api/alerts/{alert_id}")
    assert response.status_code == 200


def test_api_alert_by_id_returns_correct_record(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert = alerts[0]
    response = client.get(f"/api/alerts/{alert['id']}")
    data = json.loads(response.data)
    assert data["id"] == alert["id"]


def test_api_alert_by_id_returns_404_for_missing(client):
    response = client.get("/api/alerts/99999")
    assert response.status_code == 404


# ── /api/alerts/<id>/action ───────────────────────────────────────────────────

def test_action_acknowledge_returns_ok(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    response = client.post(
        f"/api/alerts/{alert_id}/action",
        data=json.dumps({"action_type": "acknowledge"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert data["new_status"] == "acknowledged"


def test_action_resolve_updates_status(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    client.post(
        f"/api/alerts/{alert_id}/action",
        data=json.dumps({"action_type": "resolve"}),
        content_type="application/json",
    )
    record = json.loads(client.get(f"/api/alerts/{alert_id}").data)
    assert record["alert_status"] == "resolved"


def test_action_escalate_updates_status(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    client.post(
        f"/api/alerts/{alert_id}/action",
        data=json.dumps({"action_type": "escalate"}),
        content_type="application/json",
    )
    record = json.loads(client.get(f"/api/alerts/{alert_id}").data)
    assert record["alert_status"] == "escalated"


def test_action_invalid_type_returns_400(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    response = client.post(
        f"/api/alerts/{alert_id}/action",
        data=json.dumps({"action_type": "delete"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_action_missing_alert_returns_404(client):
    response = client.post(
        "/api/alerts/99999/action",
        data=json.dumps({"action_type": "acknowledge"}),
        content_type="application/json",
    )
    assert response.status_code == 404


def test_form_action_redirects_to_index(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]
    response = client.post(
        f"/api/alerts/{alert_id}/action",
        data={"action_type": "acknowledge"},
    )
    assert response.status_code in (301, 302)


def test_api_telemetry_returns_null_when_empty(tmp_path):
    db_path = tmp_path / "empty.db"
    flask_app = create_app(db_path=str(db_path))
    flask_app.config["TESTING"] = True
    c = flask_app.test_client()
    response = c.get("/api/telemetry")
    assert response.status_code == 200
    assert json.loads(response.data) is None
