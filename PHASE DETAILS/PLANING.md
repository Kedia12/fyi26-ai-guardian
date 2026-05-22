# FYI26 AI Guardian — Step-by-Step Build Plan

> Phase 1 (detection rules, 11 scenarios, validation, documentation) is **complete**.
> This document is your roadmap for completing the remaining 10 gaps.

---

## Dependency Order (Must Follow This Sequence)

```
Phase 1: Config System
    ↓
Phase 2: JSON Export & Logging
    ↓
Phase 3: Database Persistence
    ↓
Phase 4: ML Alert Integration
    ↓
Phase 5: Precision / Recall Metrics
    ↓
Phase 6: Dashboard + Operator Actions
    ↓
Phase 7: Live Telemetry Ingestion
    ↓
Phase 8: Deployment & Packaging
    ↓
Phase 9: Hardware (MAVLink)
```

**Rule:** Every existing test must keep passing after each phase. New parameters are always optional with defaults.

---

## Phase 1 — Configuration System
**Fixes Gap 8 — No configuration system (all thresholds hardcoded)**

### What to build

**New file: `config/guardian_config.yaml`**
```yaml
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
  alert_threshold: 0.1
  alert_severity: WARNING
  alert_confidence: 0.75

logging:
  json_export_enabled: true
  json_export_path: results/logs/alerts.jsonl

database:
  enabled: false
  path: results/guardian.db

ingestion:
  mode: replay
  udp_host: 0.0.0.0
  udp_port: 14550
  serial_port: /dev/ttyUSB0
  serial_baud: 57600
```

**New file: `guardian/config.py`**

Implement these functions:
- `load_config(path=None)` — reads YAML, anchors path to project root via `Path(__file__).resolve().parent.parent`; caches result in a module-level `_config` variable
- `get_config()` — returns cached config, calls `load_config()` on first access
- `get_rule_threshold(key, default=None)` — shortcut for `config["rules"][key]`
- `get_ml_param(key, default=None)` — shortcut for `config["ml"][key]`
- `reload_config(path=None)` — clears cache and reloads (needed for tests)

**New file: `tests/test_config.py`**

Write tests for:
- `load_config()` returns a dict with `rules` and `ml` keys
- `get_rule_threshold("packet_loss_gap_ms")` returns `200`
- Changing the YAML and calling `reload_config()` returns the new value
- Missing YAML falls back to defaults gracefully

### Modify existing files

**`guardian/rules.py`** — Replace every bare literal:

| Old literal | Replace with |
|---|---|
| `time_gap > 200` | `time_gap > get_rule_threshold("packet_loss_gap_ms", 200)` |
| `voltage < 10.5` | `voltage < get_rule_threshold("battery_warning_v", 10.5)` |
| `voltage < 10.2` | `voltage < get_rule_threshold("battery_critical_v", 10.2)` |
| `satellites < 4` | `satellites < get_rule_threshold("min_satellites", 4)` |
| `lat/lon > 0.001` | `> get_rule_threshold("gps_jump_threshold_deg", 0.001)` |
| `speed_jump > 15` | `> get_rule_threshold("gps_speed_jump_mps", 15.0)` |
| `accel_mag < 0.2` | `< get_rule_threshold("gps_imu_accel_mag_threshold", 0.2)` |
| `gyro_mag < 3.0` | `< get_rule_threshold("gps_imu_gyro_mag_threshold", 3.0)` |

**`guardian/ml_model.py`** — Replace `IsolationForest(n_estimators=100, contamination=0.05, random_state=42)` with `get_ml_param(...)` calls.

**`requirements.txt`** — Add `PyYAML>=6.0`

### Install
```bash
pip install PyYAML>=6.0
```

### Verify
```bash
pytest -q                          # all existing tests still pass
python -m guardian.main            # runs unchanged
```

**Complexity: Low**

---

## Phase 2 — JSON Export & Structured Logging
**Fixes Gap 6 — No JSON or structured log export**

### What to build

**New file: `guardian/export.py`**

Implement `AlertExporter` class:
```python
class AlertExporter:
    def __init__(self, path, enabled=True)   # creates parent dirs, opens file in append mode
    def write_alert(self, alert, telemetry_row=None)   # writes one JSON line
    def write_batch(self, alerts, telemetry_row=None)  # calls write_alert for each
    def flush(self)
    def close(self)
    def __enter__(self) / __exit__(self, ...)           # context manager
```

Each line written to `.jsonl` looks like:
```json
{"alert": {...}, "telemetry": {...}, "exported_at": "2026-04-29T10:00:00Z"}
```

**New file: `tests/test_export.py`**

Write tests for:
- Write one alert → file exists and line is valid JSON
- Write batch of 3 → 3 lines in file
- `enabled=False` → file not created or empty
- `telemetry` key present in output when row is passed

### Modify existing files

**`guardian/engine.py`**

In `GuardianEngine.__init__()`:
- Read `config["logging"]["json_export_enabled"]` and `config["logging"]["json_export_path"]`
- If enabled, instantiate `AlertExporter` and store as `self.exporter`

In `process_row()`:
- After collecting all alerts: `if self.exporter: self.exporter.write_batch(alerts, row)`

**`guardian/main.py`** — After replay loop ends, print the export path if exporting is active.

### No new pip dependencies (stdlib `json`)

### Verify
```bash
python -m guardian.main data/scenarios/low_battery.csv
# results/logs/alerts.jsonl must exist

python -c "import json; [json.loads(l) for l in open('results/logs/alerts.jsonl')]"
# must print nothing (no errors)

pytest tests/test_export.py -v
```

**Complexity: Low**

---

## Phase 3 — Database Persistence
**Fixes Gap 3 — No database persistence**

### What to build

**New file: `guardian/db.py`**

Implement `GuardianDB` class with these methods:

```python
class GuardianDB:
    def __init__(self, path)                              # connects SQLite, WAL mode, creates tables
    def insert_telemetry(self, row) -> int                # returns lastrowid
    def insert_alert(self, alert, ml_source=False) -> int # returns lastrowid
    def insert_operator_action(self, action) -> int
    def insert_validation_metric(self, metric) -> int
    def update_alert_status(self, alert_id, new_status)   # used by operator loop
    def get_recent_alerts(self, limit=50) -> list[dict]
    def get_recent_telemetry(self, limit=1) -> list[dict]
    def get_alert_by_id(self, alert_id) -> dict | None
    def close(self)
```

**4 SQLite tables** (exact schema from `docs/database_contract.md`):

```sql
CREATE TABLE IF NOT EXISTS Telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms INTEGER, packet_id INTEGER, node_id TEXT,
    accel_x_g REAL, accel_y_g REAL, accel_z_g REAL,
    gyro_x_dps REAL, gyro_y_dps REAL, gyro_z_dps REAL,
    temperature_c REAL, pressure_hpa REAL, altitude_est_m REAL,
    battery_voltage_v REAL, low_power_flag INTEGER,
    gps_lat_deg REAL, gps_lon_deg REAL, gps_alt_m REAL,
    gps_speed_mps REAL, gps_fix_status INTEGER, satellite_count INTEGER,
    link_status TEXT, mode_state TEXT, ml_anomaly_score REAL,
    ingested_at TEXT
);

CREATE TABLE IF NOT EXISTS Alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms INTEGER, packet_id INTEGER, node_id TEXT,
    severity TEXT, confidence REAL, reason_code TEXT,
    reason_text TEXT, recommended_action TEXT,
    alert_status TEXT DEFAULT 'active',
    ml_source INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS Operator_Actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER REFERENCES Alerts(id),
    timestamp_ms INTEGER, packet_id INTEGER, node_id TEXT,
    reason_code TEXT, action_type TEXT, operator_note TEXT,
    acted_at TEXT
);

CREATE TABLE IF NOT EXISTS Validation_Metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario TEXT, rows_processed INTEGER,
    alerts_generated INTEGER, warning_alerts INTEGER,
    critical_alerts INTEGER, observed_reason_codes TEXT,
    expected_reason_codes TEXT, match TEXT,
    run_at TEXT
);
```

**New file: `tests/test_db.py`**

Write tests for:
- Init creates all 4 tables (query `sqlite_master`)
- `insert_telemetry` returns rowid > 0
- `insert_alert` returns rowid
- `get_recent_alerts(2)` returns max 2 rows when 3 exist
- `update_alert_status` changes the status field
- `insert_operator_action` stores the note field

### Modify existing files

**`guardian/engine.py`**

Add optional `db=None` to `GuardianEngine.__init__()`. In `process_row()`:
```python
if self.db:
    self.db.insert_telemetry(row)
    for alert in alerts:
        self.db.insert_alert(alert)
```

**`guardian/run_pipeline.py`** — Instantiate `GuardianDB` if `config["database"]["enabled"]` is true, pass to engine.

### No new pip dependencies (stdlib `sqlite3`)

### Verify
```bash
# In config/guardian_config.yaml: set database.enabled: true
python -m guardian.main data/scenarios/low_battery.csv

python3 -c "
import sqlite3
conn = sqlite3.connect('results/guardian.db')
print('Alerts:', conn.execute('SELECT COUNT(*) FROM Alerts').fetchone())
print('Telemetry:', conn.execute('SELECT COUNT(*) FROM Telemetry').fetchone())
"

pytest tests/test_db.py -v
```

**Complexity: Low-Medium**

---

## Phase 4 — ML Alert Integration
**Fixes Gap 5 — ML is minimally integrated**

### What to build

**Modify `guardian/engine.py`**

After the `score_row()` call, add this block:
```python
threshold = get_ml_param("alert_threshold", 0.1)
if anomaly_score is not None and anomaly_score > threshold:
    ml_alert = build_alert(
        row=row,
        severity=get_ml_param("alert_severity", "WARNING"),
        confidence=min(anomaly_score / (anomaly_score + 1.0), 0.99),
        reason_code="ML_ANOMALY",
        reason_text=f"ML anomaly score {anomaly_score:.4f} exceeded threshold {threshold:.4f}.",
        recommended_action="VERIFY_OPERATOR",
    )
    alerts.append(ml_alert)
```

Add imports at top of `engine.py`:
```python
from guardian.alerts import build_alert
from guardian.config import get_ml_param
```

**New file: `tests/test_ml_alerts.py`**

Write tests for:
- ML alert appears in `process_row()` output when score is high (use threshold=0.0 via temp config)
- ML alert dict passes `validate_alert()`
- No ML alert generated when score is below threshold
- Severity comes from config

### No other files modified

### Verify
```bash
python -m guardian.main data/scenarios/combined_fault.csv
# should show [WARNING] ML_ANOMALY lines

pytest tests/test_ml_alerts.py -v
python -m guardian.metrics   # ML_ANOMALY shows up in observed_reason_codes
```

**Complexity: Low**

---

## Phase 5 — Precision, Recall & Latency Metrics
**Fixes Gap 7 — No false-positive / false-negative metrics**

### What to build

**New directory: `data/labels/`** — 11 CSV files, one per scenario.

Each file has columns: `packet_id,expected_alert`
- `0` = normal row
- `1` = anomaly row

Files to create:
```
data/labels/normal_flight_labels.csv       ← all zeros
data/labels/packet_loss_labels.csv
data/labels/sensor_dropout_labels.csv
data/labels/gps_jump_labels.csv
data/labels/low_battery_labels.csv
data/labels/out_of_order_packets_labels.csv
data/labels/duplicate_packet_labels.csv
data/labels/frozen_imu_labels.csv
data/labels/gps_fix_loss_labels.csv
data/labels/gps_imu_inconsistency_labels.csv
data/labels/combined_fault_labels.csv
```

**New file: `guardian/precision_metrics.py`**

Implement these functions:
```python
def load_labels(labels_path) -> dict[int, int]
    # reads CSV → {packet_id: 0_or_1}

def compute_precision_recall(alerts, labels) -> dict
    # returns {tp, fp, fn, precision, recall, f1}
    # TP: alert on a packet_id with label=1
    # FP: alert on a packet_id with label=0
    # FN: labeled packet_id=1 with no alert

def compute_detection_latency_ms(alerts, labels, telemetry_rows) -> float | None
    # mean ms between first labeled anomaly row and first alert's timestamp_ms

def generate_precision_recall_csv(output_path)
    # iterates all 11 scenario/label pairs
    # writes results/metrics/precision_recall.csv
    # columns: scenario, precision, recall, f1, mean_latency_ms, tp, fp, fn
```

**New file: `tests/test_precision_metrics.py`**

Write tests for:
- Perfect detection: all TP → precision=1.0, recall=1.0
- False positive: alert on label=0 row → fp=1, precision < 1.0
- False negative: missed label=1 row → fn=1, recall < 1.0
- Latency returns a float for well-formed input
- CSV file is created with correct header

### Modify existing files

**`guardian/metrics.py`** — At end of `generate_metrics_csv()`, call `generate_precision_recall_csv(output_path)`.

**`guardian/run_pipeline.py`** — After generating metrics, print precision/recall totals from the new CSV.

### No new pip dependencies

### Verify
```bash
python -m guardian.metrics
# results/metrics/precision_recall.csv must exist

# Check normal_flight shows precision=1.0 (no false alarms)
pytest tests/test_precision_metrics.py -v
```

**Complexity: Medium**

---

## Phase 6 — Dashboard + Operator Actions
**Fixes Gap 2 (no dashboard) and Gap 4 (no operator action loop)**

### What to build

**New package: `dashboard/`**

```
dashboard/
├── __init__.py
├── app.py          ← Flask app factory + entry point
├── routes.py       ← all route handlers as a Blueprint
└── templates/
    ├── base.html   ← base layout with minimal inline CSS
    └── index.html  ← three-panel dashboard
```

**`dashboard/app.py`**
```python
def create_app(db_path=None, config_path=None) -> Flask
    # reads db_path from config if not provided
    # registers routes blueprint
    # returns Flask app

def run_dashboard(host="0.0.0.0", port=5000, debug=False)
    # called from __main__
```

**`dashboard/routes.py`** — Flask Blueprint with these endpoints:

| Method | Route | What it does |
|---|---|---|
| GET | `/` | Renders `index.html` with latest telemetry + 50 alerts |
| GET | `/api/alerts` | JSON list of recent alerts from DB |
| GET | `/api/telemetry` | JSON of most recent telemetry row |
| GET | `/api/alerts/<id>` | Single alert as JSON |
| POST | `/api/alerts/<id>/action` | Accepts `{"action_type": "acknowledge"\|"escalate"\|"resolve", "operator_note": "..."}` → updates DB, returns `{"status": "ok"}` |

**`dashboard/templates/index.html`** — Three panels:
1. **Live Telemetry** — table with: `packet_id`, `battery_voltage_v`, `altitude_est_m`, `gps_speed_mps`, `gps_fix_status`, `link_status`, `mode_state`
2. **Active Alerts** — table with severity, reason_code, reason_text, confidence, recommended_action, status + action buttons (Acknowledge / Escalate / Resolve) as HTML forms posting to `/api/alerts/<id>/action`
3. **Alert History** — last 50 alerts in descending order

Add `<meta http-equiv="refresh" content="5">` for automatic live updates without WebSocket.

**New file: `tests/test_dashboard.py`** — Uses Flask test client:
- `GET /` returns 200
- `GET /api/alerts` returns JSON list
- `GET /api/telemetry` returns valid JSON
- `POST /api/alerts/1/action` with `acknowledge` → then `GET /api/alerts/1` shows `alert_status == "acknowledged"`
- `POST` with invalid `action_type` returns 400

### Modify existing files

**`requirements.txt`** — Add `Flask>=3.0`

### Install
```bash
pip install Flask>=3.0
```

### Run
```bash
# Terminal 1: populate the DB
python -m guardian.main data/scenarios/combined_fault.csv

# Terminal 2: start the dashboard
python -m dashboard.app

# Open browser: http://localhost:5000
```

### Verify
```bash
pytest tests/test_dashboard.py -v
# Click Acknowledge on an alert → status changes to "acknowledged"
```

**Complexity: Medium-High**

---

## Phase 7 — Live Telemetry Ingestion
**Fixes Gap 1 — No live telemetry ingestion**

### What to build

**New package: `guardian/ingestion/`**

```
guardian/ingestion/
├── __init__.py
├── udp_listener.py       ← primary: UDP socket listener
├── serial_listener.py    ← serial/UART listener (pyserial)
├── mqtt_listener.py      ← MQTT subscriber (paho-mqtt, optional)
└── listener_factory.py   ← factory: returns correct listener from config
```

**`guardian/ingestion/udp_listener.py`**
```python
class UDPListener:
    def __init__(self, host, port, parser)
    def start(self, callback)  # blocks; calls callback(row) for each valid packet
    def stop()                 # sets threading.Event to break loop

def parse_json_packet(data: bytes) -> dict | None
    # json.loads → validate_telemetry_row → return dict or None

def parse_csv_packet(data: bytes) -> dict | None
    # split by comma, zip with REQUIRED_FIELDS → return dict
```

Use a `queue.Queue` between listener thread and engine to avoid threading issues:
- Listener thread puts rows on queue
- Main thread consumes queue and calls `engine.process_row(row)`

**`guardian/ingest_runner.py`**
```python
def run_live(mode=None):
    # loads config
    # creates listener via listener_factory.create_listener(config)
    # instantiates GuardianEngine (with DB + exporter)
    # defines on_row(row) callback → engine.process_row(row) → print/store alerts
    # starts listener

if __name__ == "__main__":
    run_live()
```

**New file: `tests/test_udp_listener.py`**

Write tests for:
- `parse_json_packet` with valid row bytes → returns dict
- `parse_json_packet` with garbage bytes → returns None
- `parse_csv_packet` with valid comma-separated row → returns dict with correct field names
- Send one UDP packet to ephemeral port in a thread → callback is called with parsed row

### Modify existing files

**`guardian/main.py`** — Add `--live` CLI argument that calls `run_live()` instead of `replay_csv()`.

**`requirements.txt`** — Add `pyserial>=3.5` and a commented `# paho-mqtt>=1.6`

### Install
```bash
pip install pyserial>=3.5
```

### Test live ingestion manually
```bash
# Terminal 1: start live listener
python -m guardian.ingest_runner

# Terminal 2: send test packets
python -c "
import socket, json, time, csv
with open('data/scenarios/normal_flight.csv') as f:
    reader = csv.DictReader(f)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for row in reader:
        sock.sendto(json.dumps(row).encode(), ('127.0.0.1', 14550))
        time.sleep(0.1)
"
```

### Verify
```bash
pytest tests/test_udp_listener.py -v
```

**Complexity: Medium**

---

## Phase 8 — Deployment & Packaging
**Fixes Gap 9 — No deployment or packaging**

### What to build

**New file: `pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "fyi26-ai-guardian"
version = "0.2.0"
description = "Human-in-the-loop AI Guardian for connected aerospace systems"
requires-python = ">=3.10"
dependencies = [
    "pandas>=2.0",
    "scikit-learn>=1.3",
    "PyYAML>=6.0",
    "Flask>=3.0",
    "pyserial>=3.5",
]

[project.optional-dependencies]
mqtt = ["paho-mqtt>=1.6"]
dev  = ["pytest>=8.0"]

[project.scripts]
guardian           = "guardian.main:run"
guardian-dashboard = "dashboard.app:run_dashboard"
guardian-live      = "guardian.ingest_runner:run_live"
```

**New file: `Dockerfile`**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
EXPOSE 5000
CMD ["python", "-m", "guardian.main"]
```

**New file: `docker-compose.yml`**
```yaml
services:
  guardian:
    build: .
    volumes:
      - ./data:/app/data
      - ./results:/app/results
      - ./config:/app/config
    ports:
      - "5000:5000"
    command: python -m dashboard.app
```

**New file: `.dockerignore`**
```
__pycache__
*.pyc
.git
results/*.db
results/logs/*.jsonl
```

**New file: `.github/workflows/ci.yml`**
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: python -m pytest -q
      - run: python -m guardian.metrics
      - run: python -m guardian.validation
```

**New file: `Makefile`**
```makefile
test:
	python -m pytest -q

pipeline:
	python -m guardian.run_pipeline

dashboard:
	python -m dashboard.app

docker-build:
	docker build -t fyi26-guardian .

docker-run:
	docker run -p 5000:5000 -v $(PWD)/data:/app/data fyi26-guardian
```

### Verify
```bash
pip install -e .
guardian data/scenarios/low_battery.csv     # entry point works

docker build -t fyi26-guardian .
docker run fyi26-guardian python -m pytest -q   # tests pass inside container

# Push to GitHub → check Actions tab → CI should be green
```

**Complexity: Low**

---

## Phase 9 — Hardware Integration (MAVLink)
**Fixes Gap 10 — No hardware integration**

### What to build

**New file: `guardian/ingestion/mavlink_assembler.py`**

The problem: MAVLink delivers different fields in different message types at different frequencies. The assembler merges them into one complete Guardian row.

```python
class MAVLinkAssembler:
    def __init__(self)
        # self._state = dict with all 22 fields initialized to None

    def update(self, msg_type, fields) -> dict | None
        # merges fields into self._state
        # returns a copy of self._state only when ALL required fields are non-None
        # returns None otherwise
```

**New file: `guardian/ingestion/mavlink_listener.py`**

```python
class MAVLinkListener:
    def __init__(self, connection_string, system_id=1)
        # e.g. "udp:0.0.0.0:14550" or "serial:/dev/ttyUSB0:57600"
        # stores mavutil.mavlink_connection(connection_string)

    def start(self, callback)
        # recv_match loop → _map_mavlink_to_telemetry(msg) → assembler.update() → callback(row)

    def stop()

    def _map_mavlink_to_telemetry(self, msg) -> tuple[str, dict] | None
        # returns (msg_type, partial_fields) for supported message types
        # returns None for unsupported message types
```

**MAVLink field mapping:**

| Guardian field | MAVLink message | MAVLink field | Conversion |
|---|---|---|---|
| `accel_x_g` | `SCALED_IMU` | `xacc` | `/ 1000.0` (mg → g) |
| `accel_y_g` | `SCALED_IMU` | `yacc` | `/ 1000.0` |
| `accel_z_g` | `SCALED_IMU` | `zacc` | `/ 1000.0` |
| `gyro_x_dps` | `SCALED_IMU` | `xgyro` | `/ 1000.0` |
| `gyro_y_dps` | `SCALED_IMU` | `ygyro` | `/ 1000.0` |
| `gyro_z_dps` | `SCALED_IMU` | `zgyro` | `/ 1000.0` |
| `altitude_est_m` | `VFR_HUD` | `alt` | direct |
| `gps_lat_deg` | `GPS_RAW_INT` | `lat` | `/ 1e7` |
| `gps_lon_deg` | `GPS_RAW_INT` | `lon` | `/ 1e7` |
| `gps_speed_mps` | `VFR_HUD` | `groundspeed` | direct |
| `satellite_count` | `GPS_RAW_INT` | `satellites_visible` | direct |
| `gps_fix_status` | `GPS_RAW_INT` | `fix_type` | `1 if fix_type >= 3 else 0` |
| `battery_voltage_v` | `SYS_STATUS` | `voltage_battery` | `/ 1000.0` |
| `temperature_c` | `SCALED_PRESSURE` | `temperature` | `/ 100.0` |
| `pressure_hpa` | `SCALED_PRESSURE` | `press_abs` | direct |

**New file: `guardian/ingestion/mavlink_heartbeat.py`**

```python
class HeartbeatMonitor:
    # daemon thread
    # tracks time of last heartbeat
    # emits PACKET_LOSS alert via callback if no heartbeat within 3 seconds
    def __init__(self, timeout_s=3.0, alert_callback=None)
    def record_heartbeat(self)
    def start(self)
    def stop(self)
```

### Modify existing files

**`guardian/ingestion/listener_factory.py`** — Add `"mavlink"` case:
```python
elif mode == "mavlink":
    from guardian.ingestion.mavlink_listener import MAVLinkListener
    conn = config["ingestion"].get("mavlink_connection", "udp:0.0.0.0:14550")
    return MAVLinkListener(conn)
```

**`requirements.txt`** — Add `pymavlink>=2.4`

### New test files

**`tests/test_mavlink_assembler.py`** — Unit tests (no hardware required):
- Assembler returns None when fields are incomplete
- Assembler returns row when all 22 fields are filled across multiple updates
- State merges incrementally
- GPS lat conversion: `lat=435000000` → `gps_lat_deg=43.5`

**`tests/test_mavlink_listener.py`** — Integration tests:
```python
import pytest, os
pytestmark = pytest.mark.skipif(
    not os.getenv("MAVLINK_SIM"),
    reason="requires MAVLink simulator (set MAVLINK_SIM=1)"
)
```

### Install
```bash
pip install pymavlink>=2.4
```

### Verify (with ArduPilot SITL)
```bash
# Terminal 1: ArduPilot SITL
# Terminal 2: MAVProxy bridge
mavproxy.py --master tcp:127.0.0.1:5760 --out udp:127.0.0.1:14550

# Terminal 3: Guardian live ingestion
# In config: ingestion.mode: mavlink
python -m guardian.ingest_runner
# → Guardian prints packet_ids and anomaly scores from simulated flight

pytest tests/test_mavlink_assembler.py -v   # passes without hardware
MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v  # with SITL running
```

**Complexity: High**

---

## Final Verification Checklist

Run these in order after all phases are complete:

```bash
# 1. Full test suite
pytest -q

# 2. Full pipeline (metrics + validation + tests)
python -m guardian.run_pipeline

# 3. Scenario run with all features active (DB + JSON export)
#    Set database.enabled: true in config/guardian_config.yaml first
python -m guardian.main data/scenarios/combined_fault.csv

# 4. Check DB has data
python3 -c "
import sqlite3
conn = sqlite3.connect('results/guardian.db')
print('Alerts:', conn.execute('SELECT COUNT(*) FROM Alerts').fetchone())
print('ML alerts:', conn.execute(\"SELECT COUNT(*) FROM Alerts WHERE reason_code='ML_ANOMALY'\").fetchone())
"

# 5. Check JSONL export
python -c "import json; rows=[json.loads(l) for l in open('results/logs/alerts.jsonl')]; print(len(rows), 'alerts exported')"

# 6. Dashboard
python -m dashboard.app
# Open http://localhost:5000

# 7. Docker
docker build -t fyi26-guardian .
docker run fyi26-guardian python -m pytest -q

# 8. Push to GitHub → CI must be green
```

---

## Summary Table

| Phase | Gap Fixed | New Files | Complexity | New Deps |
|---|---|---|---|---|
| 1 — Config System | Gap 8 | `config/guardian_config.yaml`, `guardian/config.py`, `tests/test_config.py` | Low | PyYAML |
| 2 — JSON Export | Gap 6 | `guardian/export.py`, `tests/test_export.py` | Low | none |
| 3 — Database | Gap 3 | `guardian/db.py`, `tests/test_db.py` | Low-Med | none |
| 4 — ML Alerts | Gap 5 | `tests/test_ml_alerts.py` | Low | none |
| 5 — Precision/Recall | Gap 7 | `guardian/precision_metrics.py`, `data/labels/` ×11, `tests/test_precision_metrics.py` | Medium | none |
| 6 — Dashboard | Gaps 2 & 4 | `dashboard/` package + templates + `tests/test_dashboard.py` | Med-High | Flask |
| 7 — Live Ingestion | Gap 1 | `guardian/ingestion/` package + `guardian/ingest_runner.py` + `tests/test_udp_listener.py` | Medium | pyserial |
| 8 — Deployment | Gap 9 | `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `Makefile` | Low | none |
| 9 — Hardware | Gap 10 | `mavlink_assembler.py`, `mavlink_listener.py`, `mavlink_heartbeat.py` + tests | High | pymavlink |
