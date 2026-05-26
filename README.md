# FYI26 AI Guardian

**Human-in-the-Loop AI Anomaly Detection for Connected Aerospace Systems**

*Airbus Fly Your Ideas 2026 — Competition Prototype*

---

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/Tests-162%20passed-brightgreen)
![Precision](https://img.shields.io/badge/Precision-86.4%25-green)
![Recall](https://img.shields.io/badge/Recall-90.9%25-green)
![Scenarios](https://img.shields.io/badge/Scenarios-11%2F11%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## The Problem

Connected aerospace systems depend on continuous data exchange between sensors, onboard computers, ground operators, and infrastructure. This improves situational awareness — but it also introduces new failure modes that can be catastrophic if undetected:

| Failure Mode | Risk |
|---|---|
| Missing or reordered data packets | Loss of situational awareness |
| Spoofed or jumped GPS readings | Navigation error, collision |
| IMU sensor dropout / frozen data | Incorrect attitude estimation |
| Battery degradation during flight | Unexpected power loss |
| GPS / IMU motion inconsistency | Sensor fusion breakdown |

**The Guardian sits between raw telemetry and the human operator** — catching these anomalies in real time, explaining them in plain language, and supporting the operator's response.

> Every detection is explained. Every alert includes a recommended action. Every decision stays with the human.

---

## System Architecture

```
  ┌─────────────────────────────────────────────────────────┐
  │                   TELEMETRY SOURCES                     │
  │  CSV Replay · UDP Socket · Serial Port · MAVLink        │
  │  (QGroundControl · Mission Planner · ArduPilot · PX4)   │
  └──────────────────────┬──────────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │                  GUARDIAN ENGINE                        │
  │                                                         │
  │   9 Deterministic Rule Checks                           │
  │   +  Isolation Forest ML Model                          │
  │   →  build_alert()  (severity · reason · action)        │
  └──────────────────┬──────────────────┬───────────────────┘
                     │                  │
           ┌─────────▼──────┐   ┌───────▼────────┐
           │   SQLite DB    │   │  JSONL Export  │
           │ (guardian.db)  │   │ (alerts.jsonl) │
           └─────────┬──────┘   └────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────┐
  │              FLASK DASHBOARD  :5000                     │
  │                                                         │
  │  Live Telemetry Panel                                   │
  │  Active Alert Feed  →  ACK / Escalate / Resolve         │
  │  Alert History                                          │
  └─────────────────────────────────────────────────────────┘
```

---

## Detection Capabilities

### 9 Deterministic Rule Checks

| Reason Code | Severity | Trigger Condition |
|---|---|---|
| `PACKET_LOSS` | WARNING | Timestamp gap > 200 ms or sequence gap |
| `OUT_OF_ORDER_PACKET` | WARNING | Packet ID < previous packet ID |
| `DUPLICATE_PACKET` | WARNING | Packet ID == previous packet ID |
| `IMU_DROPOUT` | CRITICAL | All 6 IMU fields exactly 0.0 |
| `IMU_FROZEN` | WARNING | All 6 IMU fields identical to previous row |
| `LOW_BATTERY` | WARNING / CRITICAL | Voltage < 10.5 V (WARNING) or < 10.2 V (CRITICAL) |
| `GPS_FIX_LOSS` | CRITICAL | Fix status == 0 or satellite count < 4 |
| `GPS_JUMP` | CRITICAL | Lat/lon change > 0.001° or speed change > 15 m/s |
| `GPS_IMU_INCONSISTENCY` | CRITICAL | GPS moved but IMU shows near-zero motion |

### ML Anomaly Detection

An **Isolation Forest** model is trained on clean `normal_flight.csv` data. Every incoming telemetry row is scored — rows above the configurable threshold generate an `ML_ANOMALY` alert. The ML layer catches composite or unusual anomalies that no single rule covers.

---

## Validated Performance

| Metric | Result |
|---|---|
| Scenarios tested | **11 / 11 passed** |
| Test suite | **162 passed**, 6 skipped (MAVLink SITL — no hardware required) |
| Average Precision | **86.4%** |
| Average Recall | **90.9%** |

All thresholds, ML parameters, and feature flags are tunable in `config/guardian_config.yaml` — no code changes needed.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run a fault scenario (CSV replay)
python -m guardian.main data/scenarios/combined_fault.csv

# 3. Start the web dashboard
python -m dashboard.app
# Open http://localhost:5000

# 4. Run the full validation pipeline
python -m guardian.run_pipeline

# 5. Run all tests
pytest -q
```

---

## Live Ingestion

Guardian can accept live telemetry from real hardware and simulators:

```bash
# UDP — from a GCS or simulator
# Set ingestion.mode: udp in config/guardian_config.yaml
python -m guardian.ingest_runner

# MAVLink — from a real flight controller or SITL
# Set ingestion.mode: mavlink in config/guardian_config.yaml
python -m guardian.ingest_runner

# Serial — from a USB-connected Pixhawk
# Set ingestion.mode: serial in config/guardian_config.yaml
python -m guardian.ingest_runner
```

### Compatible Aircraft Apps

| App | Protocol | Connection String |
|---|---|---|
| QGroundControl | UDP MAVLink | `udp:0.0.0.0:14550` |
| Mission Planner | UDP MAVLink | `udp:0.0.0.0:14550` |
| ArduPilot SITL (via MAVProxy) | UDP MAVLink | `udp:0.0.0.0:14550` |
| PX4 / Gazebo SITL | UDP MAVLink | `udp:0.0.0.0:14550` |
| Pixhawk USB (Windows) | Serial MAVLink | `serial:COM3:57600` |
| Pixhawk USB (Linux/Mac) | Serial MAVLink | `serial:/dev/ttyUSB0:57600` |

Full setup instructions per app: [How_To_Run.md](How_To_Run.md)

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Anomaly Detection** | scikit-learn · Isolation Forest · pandas |
| **Rule Engine** | Pure Python — 9 deterministic checks |
| **Database** | SQLite (stdlib `sqlite3`, no ORM) |
| **Alert Export** | JSONL (stdlib `json`) |
| **Web Dashboard** | Flask 3 · Jinja2 · Leaflet map |
| **Live Ingestion** | UDP sockets · pyserial · pymavlink |
| **Testing** | pytest — 162 automated tests |
| **Packaging** | pyproject.toml · Dockerfile · docker-compose · GitHub Actions CI |

---

## Project Structure

```
guardian/               Core detection engine (rules, ML, alerts, DB, export)
guardian/ingestion/     Live data listeners (UDP, serial, MAVLink, MQTT stub)
dashboard/              Flask web UI (routes, templates)
data/scenarios/         11 telemetry replay CSV files
data/labels/            Ground-truth labels for precision/recall measurement
config/                 guardian_config.yaml — all tuneable settings
tests/                  162 automated tests
docs/                   Architecture, schema, and contract documentation
results/                Auto-generated: guardian.db · alerts.jsonl · metrics CSVs
```

---

## Configuration

Everything is driven by `config/guardian_config.yaml`:

```yaml
rules:
  packet_loss_gap_ms: 200
  battery_warning_v: 10.5
  battery_critical_v: 10.2
  gps_jump_threshold_deg: 0.001
  gps_speed_jump_mps: 15.0
  min_satellites: 4

ml:
  n_estimators: 100
  contamination: 0.05
  alert_threshold: 0.1

ingestion:
  mode: mavlink           # replay | udp | serial | mavlink
  udp_port: 14550
```

---

## Docker

```bash
# Build and run the dashboard in a container
make docker-build
make docker-run
# Dashboard available at http://localhost:5000

# Or with docker-compose
docker-compose up --build
```

---

## Makefile Shortcuts

```bash
make test           # pytest -q
make pipeline       # metrics → validation → tests → summary
make dashboard      # start Flask on port 5000
make docker-build   # docker build -t fyi26-guardian .
make docker-run     # run container with data/results/config mounts
make install        # pip install -e .
```

---

## CI / CD

GitHub Actions runs automatically on every push to `main`:

1. Install dependencies
2. Run the full test suite (`pytest -q`)
3. Generate per-scenario and precision/recall metrics
4. Run expected-vs-observed validation — **11/11 must pass**

---

## Alert Schema

Every alert generated by Guardian contains:

| Field | Description |
|---|---|
| `timestamp_ms` | When the anomaly was detected |
| `packet_id` | Offending telemetry packet |
| `node_id` | Source node identifier |
| `severity` | `WARNING` or `CRITICAL` |
| `confidence` | 0.0 – 1.0 |
| `reason_code` | Machine-readable code (e.g. `GPS_JUMP`) |
| `reason_text` | Human-readable explanation |
| `recommended_action` | Suggested operator response |
| `alert_status` | `active` · `acknowledged` · `escalated` · `resolved` |

---

## Documentation

| File | Contents |
|---|---|
| [How_To_Run.md](How_To_Run.md) | Step-by-step setup and usage guide |
| [README_DETAILED.md](README_DETAILED.md) | Full 9-phase development documentation |
| [docs/architecture.md](docs/architecture.md) | System architecture deep-dive |
| [docs/alert_schema.md](docs/alert_schema.md) | Alert record field definitions |
| [docs/telemetry_schema.md](docs/telemetry_schema.md) | Telemetry row field definitions |
| [docs/database_contract.md](docs/database_contract.md) | SQLite schema and query patterns |
| [docs/dashboard_contract.md](docs/dashboard_contract.md) | Dashboard API and UI contract |

---

*FYI26 AI Guardian — built for Airbus Fly Your Ideas 2026.*
