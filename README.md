# FYI26 AI Guardian

**Human-in-the-Loop AI Guardian for Connected Aerospace Systems**
*Airbus Fly Your Ideas 2026 competition prototype*

---

## What it does

The Guardian sits between raw RC aircraft telemetry and a human operator. It continuously monitors incoming sensor data, detects anomalies using both deterministic rules and a machine learning model, and generates structured, explainable alerts — so operators can make fast, informed decisions without being overwhelmed by raw numbers.

It is deliberately **not** an autonomous system. Every detection is explained, every alert includes a recommended action, and every decision stays with the human.

---

## The problem

Connected aerospace systems rely on continuous data exchange between sensors, onboard computers, ground operators, and infrastructure. This improves situational awareness — but also introduces new failure modes:

- Missing or reordered data packets
- Spoofed or jumped GPS readings
- IMU sensor dropouts and frozen readings
- Battery degradation during flight
- Inconsistencies between GPS and inertial data

A monitoring layer that catches these anomalies in real time, explains them in plain language, and supports the operator's response is critical for safety-of-flight decisions.

---

## System overview

```
Telemetry sources
  CSV replay | UDP socket | Serial port | MAVLink (QGC, Mission Planner, ArduPilot, PX4)
              │
              ▼
    Guardian Engine
      9 rule-based checks  +  Isolation Forest ML model
      → build_alert() for each anomaly detected
              │
       ┌──────┴──────┐
       ▼             ▼
  SQLite DB     JSONL export
  (guardian.db) (alerts.jsonl)
       │
       ▼
  Flask Dashboard  →  http://localhost:5000
    Live telemetry panel
    Active alert feed  (ACK / Escalate / Resolve)
    Alert history
```

---

## Detection capabilities

### 9 deterministic rule checks

| Reason code | Severity | Trigger |
|---|---|---|
| `PACKET_LOSS` | WARNING | Timestamp gap > 200 ms or sequence gap |
| `OUT_OF_ORDER_PACKET` | WARNING | Packet ID < previous packet ID |
| `DUPLICATE_PACKET` | WARNING | Packet ID == previous packet ID |
| `IMU_DROPOUT` | CRITICAL | All 6 IMU fields exactly 0.0 |
| `IMU_FROZEN` | WARNING | All 6 IMU fields identical to previous row |
| `LOW_BATTERY` | WARNING / CRITICAL | Voltage < 10.5 V (WARNING) or < 10.2 V (CRITICAL) |
| `GPS_FIX_LOSS` | CRITICAL | `gps_fix_status == 0` or `satellite_count < 4` |
| `GPS_JUMP` | WARNING | Lat/lon change > 0.001° or speed change > 15 m/s |
| `GPS_IMU_INCONSISTENCY` | WARNING | GPS moved but IMU shows near-zero motion |

### ML anomaly scoring

An **Isolation Forest** model is trained on clean `normal_flight.csv` data. Every incoming row is scored; scores above the configurable threshold generate an `ML_ANOMALY` alert. The ML layer catches composite or unusual anomalies that no single rule covers.

---

## Validated performance

```
Scenarios tested:  11 / 11 passed
Test suite:        162 passed, 6 skipped (MAVLink SITL — no hardware required)
Avg Precision:     0.864
Avg Recall:        0.909
```

All thresholds, ML parameters, and feature flags are configurable in `config/guardian_config.yaml` — no code changes needed.

---

## Compatible aircraft apps

Guardian speaks MAVLink and works with any app that outputs it:

| App | Protocol | Connection |
|---|---|---|
| QGroundControl | UDP MAVLink | `udp:0.0.0.0:14550` |
| Mission Planner | UDP MAVLink | `udp:0.0.0.0:14550` |
| ArduPilot SITL (via MAVProxy) | UDP MAVLink | `udp:0.0.0.0:14550` |
| PX4 / Gazebo SITL | UDP MAVLink | `udp:0.0.0.0:14550` |
| Pixhawk USB (Windows) | Serial MAVLink | `serial:COM3:57600` |
| Pixhawk USB (Linux) | Serial MAVLink | `serial:/dev/ttyUSB0:57600` |

See [How_To_Run.md](How_To_Run.md) for full setup instructions per app.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run a fault scenario (CSV replay)
python -m guardian.main data/scenarios/combined_fault.csv

# 3. Start the web dashboard
python -m dashboard.app
# Open: http://localhost:5000

# 4. Run the full validation pipeline
python -m guardian.run_pipeline

# 5. Run all tests
pytest -q
```

---

## Live ingestion

```bash
# UDP (from a GCS or simulator)
# Set ingestion.mode: udp in config/guardian_config.yaml
python -m guardian.ingest_runner

# MAVLink (from a real flight controller or SITL)
# Set ingestion.mode: mavlink in config/guardian_config.yaml
python -m guardian.ingest_runner
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Anomaly detection | Python · scikit-learn (Isolation Forest) · pandas |
| Rule engine | Pure Python (9 deterministic checks) |
| Database | SQLite (stdlib `sqlite3`, no ORM) |
| Alert export | JSONL (stdlib `json`) |
| Dashboard | Flask 3 · Jinja2 · Leaflet map |
| Live ingestion | UDP sockets · pyserial · pymavlink |
| Testing | pytest (162 tests) |
| Packaging | pyproject.toml · Dockerfile · docker-compose · GitHub Actions CI |

---

## Project structure

```
guardian/           Core detection engine (rules, ML, alerts, DB, export)
guardian/ingestion/ Live data listeners (UDP, serial, MAVLink, MQTT stub)
dashboard/          Flask web UI (routes, templates)
data/scenarios/     11 telemetry replay CSV files
data/labels/        Ground-truth labels for precision/recall measurement
config/             guardian_config.yaml (all tuneable settings)
tests/              162 automated tests
docs/               Architecture, schema, and contract documentation
```

---

## Makefile shortcuts

```bash
make test          # pytest -q
make pipeline      # metrics → validation → tests → summary
make dashboard     # start Flask on port 5000
make docker-build  # docker build -t fyi26-guardian .
make docker-run    # run container with data/results/config mounts
make install       # pip install -e .
```

---

## CI

GitHub Actions runs on every push to `main`:
1. Install dependencies
2. Run full test suite (`pytest -q`)
3. Generate scenario and precision/recall metrics
4. Run expected-vs-observed validation (11/11 must pass)

---

*FYI26 AI Guardian — built for Airbus Fly Your Ideas 2026.*
