# Phase 6 — Dashboard & Operator Actions
**Fixes Gap 2 (no dashboard) and Gap 4 (no operator action loop)**

---

## What You Are Building

A web dashboard that an operator opens in a browser to:
- See the latest telemetry values (battery, altitude, GPS, link status)
- See active alerts with their severity, reason, and confidence
- Click a button to Acknowledge, Escalate, or Resolve any alert
- Browse alert history

The dashboard is built with **Flask** (Python web framework) and **plain HTML** templates with no JavaScript framework. A `<meta>` refresh tag auto-reloads the page every 5 seconds, giving near-real-time updates without the complexity of WebSockets.

The dashboard reads from and writes to the **SQLite database** built in Phase 3.

---

## Prerequisites

- Phase 1 (config) — dashboard reads db path from config
- Phase 3 (database) — `GuardianDB` provides all data
- Phase 4 (ML alerts) — ML_ANOMALY alerts will show up on the dashboard

---

## Files You Will Create

```
dashboard/__init__.py
dashboard/app.py
dashboard/routes.py
dashboard/templates/base.html
dashboard/templates/index.html
tests/test_dashboard.py
```

## Files You Will Modify

```
requirements.txt                 ← add Flask>=3.0
```

---

## Step 1 — Install Flask

```bash
pip install "Flask>=3.0"
```

Add to `requirements.txt`:
```
Flask>=3.0
```

---

## Step 2 — Create `dashboard/__init__.py`

This is an empty file that tells Python the `dashboard/` directory is a package.

```python
```
(create the file, leave it empty)

---

## Step 3 — Create `dashboard/app.py`

Create the file `dashboard/app.py` with the following content.

```python
from flask import Flask
from pathlib import Path


def create_app(db_path=None, config_path=None):
    """Flask application factory.

    Parameters
    ----------
    db_path : str or Path, optional
        Path to the SQLite database. If None, reads from guardian config.
    config_path : str or Path, optional
        Path to a guardian config YAML. If None, uses the default config.

    Returns
    -------
    Flask
        A configured Flask application instance.
    """
    import guardian.config as cfg

    # Load guardian config if a custom path was given
    if config_path is not None:
        cfg.reload_config(config_path)

    # Resolve the database path
    if db_path is None:
        guardian_cfg = cfg.get_config()
        db_path = guardian_cfg.get("database", {}).get("path", "results/guardian.db")

    # Resolve the db_path relative to the project root
    project_root = Path(__file__).resolve().parent.parent
    if not Path(db_path).is_absolute():
        db_path = str(project_root / db_path)

    from guardian.db import GuardianDB

    app = Flask(__name__, template_folder="templates")

    # Store the DB instance on the app so routes can access it via current_app
    app.guardian_db = GuardianDB(db_path)
    app.config["DB_PATH"] = db_path

    # Register the routes blueprint
    from dashboard.routes import bp
    app.register_blueprint(bp)

    return app


def run_dashboard(host="0.0.0.0", port=5000, debug=False):
    """Start the Flask development server.

    Call this from __main__ or from guardian.main with --dashboard flag.
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(debug=True)
```

---

## Step 4 — Create `dashboard/routes.py`

Create the file `dashboard/routes.py` with the following content.

```python
from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    current_app,
    abort,
)

bp = Blueprint("guardian", __name__)

# Valid operator action types. Any other value returns HTTP 400.
VALID_ACTIONS = {"acknowledge", "escalate", "resolve"}


def get_db():
    """Return the GuardianDB instance stored on the current Flask app."""
    return current_app.guardian_db


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------

@bp.route("/")
def index():
    """Render the main dashboard page.

    Passes the latest telemetry row and the 50 most recent alerts to the
    template so it can render without JavaScript.
    """
    db = get_db()
    telemetry_rows = db.get_recent_telemetry(limit=1)
    latest_telemetry = telemetry_rows[0] if telemetry_rows else None
    recent_alerts = db.get_recent_alerts(limit=50)
    active_alerts = db.get_all_active_alerts()

    return render_template(
        "index.html",
        telemetry=latest_telemetry,
        active_alerts=active_alerts,
        recent_alerts=recent_alerts,
    )


# ---------------------------------------------------------------------------
# JSON API routes
# ---------------------------------------------------------------------------

@bp.route("/api/alerts")
def api_alerts():
    """Return the 50 most recent alerts as a JSON array.

    Query parameters:
        limit (int): How many alerts to return. Default 50, max 200.
    """
    db = get_db()
    limit = min(int(request.args.get("limit", 50)), 200)
    alerts = db.get_recent_alerts(limit=limit)
    return jsonify(alerts)


@bp.route("/api/telemetry")
def api_telemetry():
    """Return the most recent telemetry row as a JSON object."""
    db = get_db()
    rows = db.get_recent_telemetry(limit=1)
    if not rows:
        return jsonify(None)
    return jsonify(rows[0])


@bp.route("/api/alerts/<int:alert_id>")
def api_alert_by_id(alert_id):
    """Return a single alert by its database ID.

    Returns HTTP 404 if the alert does not exist.
    """
    db = get_db()
    alert = db.get_alert_by_id(alert_id)
    if alert is None:
        abort(404, description=f"Alert {alert_id} not found.")
    return jsonify(alert)


@bp.route("/api/alerts/<int:alert_id>/action", methods=["POST"])
def api_alert_action(alert_id):
    """Perform an operator action on an alert.

    Request body (JSON):
        action_type (str): One of "acknowledge", "escalate", "resolve".
        operator_note (str, optional): Free-text note from the operator.

    Returns HTTP 400 if action_type is missing or invalid.
    Returns HTTP 404 if the alert does not exist.
    Returns HTTP 200 with {"status": "ok"} on success.
    """
    db = get_db()

    # Verify the alert exists
    alert = db.get_alert_by_id(alert_id)
    if alert is None:
        abort(404, description=f"Alert {alert_id} not found.")

    # Parse request body
    data = request.get_json(silent=True) or {}
    action_type = data.get("action_type", "").lower().strip()

    if not action_type:
        abort(400, description="Missing required field: action_type.")
    if action_type not in VALID_ACTIONS:
        abort(
            400,
            description=f"Invalid action_type '{action_type}'. "
                        f"Must be one of: {sorted(VALID_ACTIONS)}.",
        )

    operator_note = data.get("operator_note", "")

    # Map action_type to a new alert_status
    status_map = {
        "acknowledge": "acknowledged",
        "escalate": "escalated",
        "resolve": "resolved",
    }
    new_status = status_map[action_type]

    # Update the alert status in the database
    db.update_alert_status(alert_id, new_status)

    # Record the operator action
    db.insert_operator_action({
        "alert_id": alert_id,
        "timestamp_ms": alert.get("timestamp_ms"),
        "packet_id": alert.get("packet_id"),
        "node_id": alert.get("node_id"),
        "reason_code": alert.get("reason_code"),
        "action_type": action_type,
        "operator_note": operator_note,
    })

    return jsonify({"status": "ok", "alert_id": alert_id, "new_status": new_status})


@bp.route("/api/metrics")
def api_metrics():
    """Return scenario metrics from the CSV file as a JSON array."""
    import csv
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    metrics_path = project_root / "results" / "metrics" / "scenario_metrics.csv"

    if not metrics_path.exists():
        return jsonify([])

    with open(metrics_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return jsonify(rows)
```

---

## Step 5 — Create `dashboard/templates/base.html`

Create the file `dashboard/templates/base.html` with the following content.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Auto-refresh every 5 seconds for near-real-time updates -->
    <meta http-equiv="refresh" content="5">
    <title>FYI26 AI Guardian — Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Courier New', monospace;
            background: #0a0f1e;
            color: #c8d8f0;
            padding: 20px;
        }

        header {
            border-bottom: 2px solid #1e3a5f;
            padding-bottom: 12px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        header h1 { color: #4fc3f7; font-size: 1.4rem; letter-spacing: 2px; }
        header .subtitle { color: #5c8ab8; font-size: 0.8rem; }

        .panel {
            background: #0d1b2e;
            border: 1px solid #1e3a5f;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
        }

        .panel h2 {
            color: #4fc3f7;
            font-size: 0.9rem;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 12px;
            border-bottom: 1px solid #1e3a5f;
            padding-bottom: 8px;
        }

        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        th { color: #5c8ab8; text-align: left; padding: 6px 10px; border-bottom: 1px solid #1e3a5f; font-weight: normal; }
        td { padding: 6px 10px; border-bottom: 1px solid #0f1e30; vertical-align: top; }
        tr:last-child td { border-bottom: none; }

        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: bold;
            letter-spacing: 0.5px;
        }

        .badge-warning  { background: #7b4a00; color: #ffb74d; }
        .badge-critical { background: #7b0000; color: #ef9a9a; }
        .badge-active       { background: #003d6b; color: #64b5f6; }
        .badge-acknowledged { background: #1b4620; color: #81c784; }
        .badge-escalated    { background: #4a1e00; color: #ffcc80; }
        .badge-resolved     { background: #1b2a20; color: #a5d6a7; }

        .action-form { display: inline; }
        .btn {
            background: transparent;
            border: 1px solid;
            border-radius: 3px;
            padding: 2px 8px;
            font-size: 0.72rem;
            cursor: pointer;
            font-family: inherit;
            margin-right: 4px;
        }
        .btn-ack      { border-color: #4fc3f7; color: #4fc3f7; }
        .btn-ack:hover { background: #4fc3f7; color: #0a0f1e; }
        .btn-esc      { border-color: #ffb74d; color: #ffb74d; }
        .btn-esc:hover { background: #ffb74d; color: #0a0f1e; }
        .btn-res      { border-color: #81c784; color: #81c784; }
        .btn-res:hover { background: #81c784; color: #0a0f1e; }

        .no-data { color: #3a5a7a; font-style: italic; padding: 12px 0; }

        .tele-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }

        .tele-cell { background: #0a1520; border: 1px solid #1e3a5f; border-radius: 4px; padding: 10px; }
        .tele-label { color: #5c8ab8; font-size: 0.7rem; text-transform: uppercase; margin-bottom: 4px; }
        .tele-value { color: #e1f0ff; font-size: 1.1rem; }
        .tele-value.warn { color: #ffb74d; }
        .tele-value.crit { color: #ef9a9a; }

        footer { color: #2a4a6a; font-size: 0.72rem; margin-top: 24px; text-align: center; }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>FYI26 AI GUARDIAN</h1>
            <div class="subtitle">AIRBUS FLY YOUR IDEAS 2026 — HUMAN-IN-THE-LOOP ANOMALY DETECTION</div>
        </div>
        <div class="subtitle" id="ts">{{ now }}</div>
    </header>

    {% block content %}{% endblock %}

    <footer>Guardian Phase 2 Dashboard — Auto-refresh every 5 seconds</footer>
</body>
</html>
```

---

## Step 6 — Create `dashboard/templates/index.html`

Create the file `dashboard/templates/index.html` with the following content.

```html
{% extends "base.html" %}

{% block content %}

<!-- ======================================================= -->
<!-- PANEL 1: LIVE TELEMETRY                                  -->
<!-- ======================================================= -->
<div class="panel">
    <h2>Live Telemetry</h2>

    {% if telemetry %}
    <div class="tele-grid">
        <div class="tele-cell">
            <div class="tele-label">Packet ID</div>
            <div class="tele-value">{{ telemetry.packet_id }}</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Battery Voltage</div>
            <div class="tele-value {% if telemetry.battery_voltage_v < 10.2 %}crit{% elif telemetry.battery_voltage_v < 10.5 %}warn{% endif %}">
                {{ "%.2f"|format(telemetry.battery_voltage_v) }} V
            </div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Altitude</div>
            <div class="tele-value">{{ "%.1f"|format(telemetry.altitude_est_m) }} m</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">GPS Speed</div>
            <div class="tele-value">{{ "%.1f"|format(telemetry.gps_speed_mps) }} m/s</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">GPS Fix</div>
            <div class="tele-value {% if telemetry.gps_fix_status == 0 %}crit{% endif %}">
                {% if telemetry.gps_fix_status == 1 %}LOCKED{% else %}NO FIX{% endif %}
            </div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Satellites</div>
            <div class="tele-value {% if telemetry.satellite_count < 4 %}warn{% endif %}">
                {{ telemetry.satellite_count }}
            </div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Link Status</div>
            <div class="tele-value">{{ telemetry.link_status }}</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Mode</div>
            <div class="tele-value">{{ telemetry.mode_state }}</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">Temperature</div>
            <div class="tele-value">{{ "%.1f"|format(telemetry.temperature_c) }} °C</div>
        </div>
        <div class="tele-cell">
            <div class="tele-label">ML Score</div>
            <div class="tele-value">
                {% if telemetry.ml_anomaly_score is not none %}
                    {{ "%.4f"|format(telemetry.ml_anomaly_score) }}
                {% else %}
                    —
                {% endif %}
            </div>
        </div>
    </div>
    {% else %}
    <p class="no-data">No telemetry data available. Run a scenario to populate the database.</p>
    {% endif %}
</div>


<!-- ======================================================= -->
<!-- PANEL 2: ACTIVE ALERTS (with operator action buttons)   -->
<!-- ======================================================= -->
<div class="panel">
    <h2>Active Alerts ({{ active_alerts|length }})</h2>

    {% if active_alerts %}
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Severity</th>
                <th>Reason</th>
                <th>Description</th>
                <th>Confidence</th>
                <th>Action</th>
                <th>Operator</th>
            </tr>
        </thead>
        <tbody>
        {% for alert in active_alerts %}
            <tr>
                <td>{{ alert.id }}</td>
                <td>
                    <span class="badge badge-{{ alert.severity|lower }}">
                        {{ alert.severity }}
                    </span>
                </td>
                <td>{{ alert.reason_code }}</td>
                <td style="max-width:280px; color:#8ab4d4;">{{ alert.reason_text }}</td>
                <td>{{ "%.0f"|format(alert.confidence * 100) }}%</td>
                <td>{{ alert.recommended_action }}</td>
                <td>
                    <!-- Acknowledge button -->
                    <form class="action-form" method="POST"
                          action="/api/alerts/{{ alert.id }}/action">
                        <input type="hidden" name="action_type" value="acknowledge">
                        <button type="submit" class="btn btn-ack">ACK</button>
                    </form>
                    <!-- Escalate button -->
                    <form class="action-form" method="POST"
                          action="/api/alerts/{{ alert.id }}/action">
                        <input type="hidden" name="action_type" value="escalate">
                        <button type="submit" class="btn btn-esc">ESC</button>
                    </form>
                    <!-- Resolve button -->
                    <form class="action-form" method="POST"
                          action="/api/alerts/{{ alert.id }}/action">
                        <input type="hidden" name="action_type" value="resolve">
                        <button type="submit" class="btn btn-res">RES</button>
                    </form>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="no-data">No active alerts. System nominal.</p>
    {% endif %}
</div>


<!-- ======================================================= -->
<!-- PANEL 3: ALERT HISTORY                                   -->
<!-- ======================================================= -->
<div class="panel">
    <h2>Alert History (last 50)</h2>

    {% if recent_alerts %}
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Severity</th>
                <th>Reason</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Packet</th>
                <th>Created</th>
            </tr>
        </thead>
        <tbody>
        {% for alert in recent_alerts %}
            <tr>
                <td>{{ alert.id }}</td>
                <td>
                    <span class="badge badge-{{ alert.severity|lower }}">
                        {{ alert.severity }}
                    </span>
                </td>
                <td>{{ alert.reason_code }}</td>
                <td>{{ "%.0f"|format(alert.confidence * 100) }}%</td>
                <td>
                    <span class="badge badge-{{ alert.alert_status|lower }}">
                        {{ alert.alert_status }}
                    </span>
                </td>
                <td>{{ alert.packet_id }}</td>
                <td style="color:#3a6a8a; font-size:0.75rem;">{{ alert.created_at }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="no-data">No alert history. Run a scenario to generate alerts.</p>
    {% endif %}
</div>

{% endblock %}
```

---

## Step 7 — Fix the operator action form handling

The operator action buttons use HTML forms posting to the API. However, since the API expects JSON but the HTML form sends `application/x-www-form-urlencoded`, you need to handle both in `routes.py`. Update the `api_alert_action` route to accept form data as well:

```python
@bp.route("/api/alerts/<int:alert_id>/action", methods=["POST"])
def api_alert_action(alert_id):
    db = get_db()
    alert = db.get_alert_by_id(alert_id)
    if alert is None:
        abort(404, description=f"Alert {alert_id} not found.")

    # Accept both JSON and HTML form submissions
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    action_type = data.get("action_type", "").lower().strip()

    if not action_type:
        abort(400, description="Missing required field: action_type.")
    if action_type not in VALID_ACTIONS:
        abort(400, description=f"Invalid action_type '{action_type}'.")

    operator_note = data.get("operator_note", "")
    status_map = {"acknowledge": "acknowledged", "escalate": "escalated", "resolve": "resolved"}
    new_status = status_map[action_type]

    db.update_alert_status(alert_id, new_status)
    db.insert_operator_action({
        "alert_id": alert_id,
        "timestamp_ms": alert.get("timestamp_ms"),
        "packet_id": alert.get("packet_id"),
        "node_id": alert.get("node_id"),
        "reason_code": alert.get("reason_code"),
        "action_type": action_type,
        "operator_note": operator_note,
    })

    # If this was a form submission, redirect back to the dashboard
    if not request.is_json:
        from flask import redirect, url_for
        return redirect(url_for("guardian.index"))

    return jsonify({"status": "ok", "alert_id": alert_id, "new_status": new_status})
```

Also add a `now` variable to the index route so the template can display the current time:

```python
from datetime import datetime

@bp.route("/")
def index():
    db = get_db()
    telemetry_rows = db.get_recent_telemetry(limit=1)
    latest_telemetry = telemetry_rows[0] if telemetry_rows else None
    recent_alerts = db.get_recent_alerts(limit=50)
    active_alerts = db.get_all_active_alerts()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return render_template(
        "index.html",
        telemetry=latest_telemetry,
        active_alerts=active_alerts,
        recent_alerts=recent_alerts,
        now=now,
    )
```

---

## Step 8 — Create `tests/test_dashboard.py`

Create the file `tests/test_dashboard.py` with the following content.

```python
import pytest
import json
from dashboard.app import create_app


@pytest.fixture
def app(tmp_path):
    """Create a Flask test app backed by a temporary database."""
    # Pre-populate the database with one telemetry row and two alerts
    from guardian.db import GuardianDB
    db_path = tmp_path / "test.db"
    db = GuardianDB(db_path)

    db.insert_telemetry({
        "timestamp_ms": 1000, "packet_id": 1, "node_id": "node_01",
        "accel_x_g": 0.01, "accel_y_g": 0.02, "accel_z_g": 1.0,
        "gyro_x_dps": 0.1, "gyro_y_dps": 0.2, "gyro_z_dps": 0.3,
        "temperature_c": 25.0, "pressure_hpa": 1013.0, "altitude_est_m": 10.0,
        "battery_voltage_v": 11.8, "low_power_flag": 0,
        "gps_lat_deg": 43.5, "gps_lon_deg": -79.3, "gps_alt_m": 10.0,
        "gps_speed_mps": 5.0, "gps_fix_status": 1, "satellite_count": 8,
        "link_status": "ok", "mode_state": "AUTO",
    })
    db.insert_alert({
        "timestamp_ms": 1000, "packet_id": 1, "node_id": "node_01",
        "severity": "WARNING", "confidence": 0.85,
        "reason_code": "LOW_BATTERY", "reason_text": "Battery low.",
        "recommended_action": "ENTER_SAFE_MODE", "alert_status": "active",
    })
    db.insert_alert({
        "timestamp_ms": 2000, "packet_id": 2, "node_id": "node_01",
        "severity": "CRITICAL", "confidence": 0.97,
        "reason_code": "GPS_FIX_LOSS", "reason_text": "GPS lost.",
        "recommended_action": "VERIFY_OPERATOR", "alert_status": "active",
    })
    db.close()

    flask_app = create_app(db_path=str(db_path))
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Return a Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# HTML route tests
# ---------------------------------------------------------------------------

def test_index_returns_200(client):
    """GET / must return HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_alert_reason_code(client):
    """The index page HTML must contain the reason code of an active alert."""
    response = client.get("/")
    html = response.data.decode("utf-8")
    assert "LOW_BATTERY" in html or "GPS_FIX_LOSS" in html


# ---------------------------------------------------------------------------
# JSON API tests
# ---------------------------------------------------------------------------

def test_api_alerts_returns_json_list(client):
    """GET /api/alerts must return a JSON array."""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2


def test_api_alerts_limit_parameter(client):
    """GET /api/alerts?limit=1 must return at most 1 alert."""
    response = client.get("/api/alerts?limit=1")
    data = json.loads(response.data)
    assert len(data) == 1


def test_api_telemetry_returns_json_object(client):
    """GET /api/telemetry must return a JSON object with telemetry fields."""
    response = client.get("/api/telemetry")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data is not None
    assert "packet_id" in data
    assert "battery_voltage_v" in data


def test_api_alert_by_id_returns_correct_alert(client, app):
    """GET /api/alerts/<id> must return the alert with that id."""
    # First get all alerts to find a valid id
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    alert_id = alerts[0]["id"]

    response = client.get(f"/api/alerts/{alert_id}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["id"] == alert_id


def test_api_alert_by_id_returns_404_for_missing(client):
    """GET /api/alerts/99999 must return HTTP 404."""
    response = client.get("/api/alerts/99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Operator action tests
# ---------------------------------------------------------------------------

def test_operator_action_acknowledge_updates_status(client):
    """POST /api/alerts/<id>/action with acknowledge must set status to acknowledged."""
    # Get all alerts
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    alert_id = alerts[0]["id"]

    # Acknowledge the alert
    response = client.post(
        f"/api/alerts/{alert_id}/action",
        json={"action_type": "acknowledge", "operator_note": "Reviewed."},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert data["new_status"] == "acknowledged"

    # Verify the status was updated
    response = client.get(f"/api/alerts/{alert_id}")
    updated = json.loads(response.data)
    assert updated["alert_status"] == "acknowledged"


def test_operator_action_escalate_updates_status(client):
    """POST with escalate must set status to escalated."""
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    alert_id = alerts[1]["id"]

    response = client.post(
        f"/api/alerts/{alert_id}/action",
        json={"action_type": "escalate"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["new_status"] == "escalated"


def test_operator_action_invalid_type_returns_400(client):
    """POST with an invalid action_type must return HTTP 400."""
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    alert_id = alerts[0]["id"]

    response = client.post(
        f"/api/alerts/{alert_id}/action",
        json={"action_type": "invalid_action"},
    )
    assert response.status_code == 400


def test_operator_action_missing_type_returns_400(client):
    """POST with no action_type must return HTTP 400."""
    response = client.get("/api/alerts")
    alerts = json.loads(response.data)
    alert_id = alerts[0]["id"]

    response = client.post(
        f"/api/alerts/{alert_id}/action",
        json={"operator_note": "no action type given"},
    )
    assert response.status_code == 400


def test_operator_action_on_nonexistent_alert_returns_404(client):
    """POST to /api/alerts/99999/action must return HTTP 404."""
    response = client.post(
        "/api/alerts/99999/action",
        json={"action_type": "acknowledge"},
    )
    assert response.status_code == 404
```

---

## Step 9 — Run Tests

```bash
pytest tests/test_dashboard.py -v
```

Expected: all tests pass.

```bash
pytest -q
```

Expected: zero failures.

---

## Step 10 — Run the Dashboard Manually

**Terminal 1:** Populate the database:
```bash
# Make sure database.enabled: true in config/guardian_config.yaml
python -m guardian.main data/scenarios/combined_fault.csv
```

**Terminal 2:** Start the dashboard:
```bash
python -m dashboard.app
```

Open your browser at: **`http://localhost:5000`**

You should see:
- Live Telemetry panel with battery, altitude, GPS, link status values
- Active Alerts panel with ACK / ESC / RES buttons
- Alert History showing all 50 recent alerts

Click **ACK** on an alert. The page refreshes and the alert moves from Active to History with status `acknowledged`.

---

## Checklist — Phase 6 Complete When:

- [ ] `dashboard/__init__.py` exists (empty file)
- [ ] `dashboard/app.py` exists with `create_app()` and `run_dashboard()`
- [ ] `dashboard/routes.py` exists with all 5 route handlers
- [ ] `dashboard/templates/base.html` exists with auto-refresh meta tag
- [ ] `dashboard/templates/index.html` exists with all 3 panels
- [ ] `tests/test_dashboard.py` exists with all 12 tests passing
- [ ] `requirements.txt` includes `Flask>=3.0`
- [ ] `http://localhost:5000` loads with no errors
- [ ] Clicking ACK changes alert status to `acknowledged`
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
dashboard/                       ← NEW package
├── __init__.py
├── app.py
├── routes.py
└── templates/
    ├── base.html
    └── index.html

tests/
└── test_dashboard.py            ← NEW — 12 dashboard tests

requirements.txt                 ← MODIFIED — added Flask>=3.0
```

---

## Proceed to Phase 7 →

Phase 7 replaces CSV replay with live telemetry over a UDP socket. The dashboard will then show real-time data from an actual network source rather than a pre-recorded scenario file.
