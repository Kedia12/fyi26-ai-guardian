# FYI26 AI Guardian — Project Overview

---

## 1. What Is This Project?

**FYI26 AI Guardian** is a prototype built for the **Airbus Fly Your Ideas 2026 (FYI26)** challenge. The goal is to create a **Human-in-the-Loop AI Guardian** for connected aerospace systems — specifically RC aircraft telemetry monitoring.

The Guardian sits between raw sensor data and a human operator. It continuously monitors incoming telemetry packets, detects anomalies using both deterministic rules and machine learning, and generates structured alerts that help operators make informed decisions. It is explicitly designed **not** to replace human judgment — it informs and supports it.

**Core capabilities:**
- Detect 9 categories of anomalies in real-time telemetry data
- Generate explainable, actionable alerts with severity levels and confidence scores
- Validate detection accuracy against expected outcomes across 11 test scenarios
- Provide a documented interface for a dashboard and database to plug into

**Tech stack:** Python · pandas · scikit-learn · pytest

---

## 2. Project Structure

```
fyi26-ai-guardian/
│
├── guardian/                    ← Main Python package (all core logic)
│   ├── __init__.py              ← Package init (empty)
│   ├── schemas.py               ← Field definitions + validation helpers
│   ├── rules.py                 ← 9 rule-based anomaly detectors
│   ├── ml_model.py              ← Isolation Forest anomaly scorer
│   ├── engine.py                ← Main row processor (rules + ML combined)
│   ├── alerts.py                ← Alert dictionary builder
│   ├── replay.py                ← CSV scenario player
│   ├── expectations.py          ← Expected detections per scenario
│   ├── metrics.py               ← Per-scenario statistics collector
│   ├── validation.py            ← Expected vs. observed comparison reporter
│   ├── utils.py                 ← Print helpers
│   ├── main.py                  ← CLI entry point
│   ├── run_pipeline.py          ← Full pipeline runner (metrics + validation + tests)
│   └── run_all.py               ← Simplified automation script
│
├── data/
│   └── scenarios/               ← 11 CSV test scenario files
│       ├── normal_flight.csv
│       ├── packet_loss.csv
│       ├── sensor_dropout.csv
│       ├── gps_jump.csv
│       ├── low_battery.csv
│       ├── out_of_order_packets.csv
│       ├── duplicate_packet.csv
│       ├── frozen_imu.csv
│       ├── gps_fix_loss.csv
│       ├── gps_imu_inconsistency.csv
│       └── combined_fault.csv
│
├── tests/                       ← pytest unit tests (one file per module)
│   ├── conftest.py
│   ├── test_alerts.py
│   ├── test_schemas.py
│   ├── test_rules.py
│   ├── test_engine.py
│   ├── test_ml_model.py
│   ├── test_replay.py
│   ├── test_utils.py
│   ├── test_metrics.py
│   └── test_main.py
│
├── docs/                        ← Architecture and integration documentation
│   ├── architecture.md          ← System design and data flow
│   ├── telemetry_schema.md      ← 22-field telemetry specification
│   ├── alert_schema.md          ← 9-field alert specification
│   ├── validation_plan.md       ← Scenario validation strategy
│   ├── expected_results.md      ← Expected outcomes per scenario
│   ├── database_contract.md     ← Contract for database team
│   ├── dashboard_contract.md    ← Contract for dashboard/database interface
│   ├── dashboard_handoff.md     ← Dashboard display requirements
│   ├── phase1_checklist.md      ← Phase 1 completion checklist
│   └── guardian_phase1_closure.md ← Phase 1 closure summary
│
├── results/                     ← Auto-generated output files
│   ├── metrics/
│   │   ├── scenario_metrics.csv
│   │   ├── expected_vs_observed.csv
│   │   └── validation_summary.md
│   └── sample_alert_logs/       ← Per-scenario alert text logs
│       ├── normal_flight.txt
│       ├── packet_loss.txt
│       └── ... (one per scenario)
│
├── requirements.txt             ← pandas, scikit-learn, pytest
├── README.md                    ← Public-facing project overview
└── .gitignore
```

---

## 3. How the Project Works

### 3.1 Telemetry Schema

Every telemetry packet contains **22 fields** grouped into 5 categories:

| Category | Fields |
|---|---|
| Packet & timing | `timestamp_ms`, `packet_id`, `node_id` |
| IMU / motion | `accel_x/y/z_g`, `gyro_x/y/z_dps` |
| Environmental | `temperature_c`, `pressure_hpa`, `altitude_est_m` |
| Power / health | `battery_voltage_v`, `low_power_flag` |
| GPS / navigation | `gps_lat/lon_deg`, `gps_alt_m`, `gps_speed_mps`, `gps_fix_status`, `satellite_count` |
| Link / state | `link_status`, `mode_state` |

### 3.2 Data Flow

```
CSV Scenario File
      │
      ▼
  replay.py          ← Yields one row at a time (simulates live stream)
      │
      ▼
  engine.py          ← GuardianEngine.process_row(row)
   ├── rules.py      ← Runs all 9 rule checks against current + previous row
   └── ml_model.py   ← Scores row with Isolation Forest (trained on normal_flight.csv)
      │
      ▼
  alerts.py          ← Builds structured alert dictionaries from rule violations
      │
      ▼
 Alert Output        ← Printed to console / saved to sample_alert_logs/
```

### 3.3 Rule-Based Detection (rules.py)

Nine deterministic checks run on every packet:

| Rule | Trigger Condition | Severity |
|---|---|---|
| `check_packet_loss` | Sequence gap > 1 or timestamp gap > 200ms | WARNING |
| `check_out_of_order_packet` | Current `packet_id` < previous `packet_id` | WARNING |
| `check_duplicate_packet` | Current `packet_id` == previous `packet_id` | WARNING |
| `check_imu_dropout` | All 6 IMU fields exactly 0.0 | CRITICAL |
| `check_frozen_imu` | IMU values identical to previous row | WARNING |
| `check_low_battery` | Voltage < 10.5V or `low_power_flag` = 1 | WARNING / CRITICAL |
| `check_gps_fix_loss` | `gps_fix_status` = 0 or `satellite_count` < 4 | CRITICAL |
| `check_gps_jump` | Position change > 0.001° or speed change > 15 m/s | WARNING |
| `check_gps_imu_inconsistency` | Large GPS change without corresponding IMU motion | WARNING |

### 3.4 Machine Learning Detection (ml_model.py)

- **Model:** Isolation Forest (scikit-learn)
- **Training data:** `normal_flight.csv` (clean baseline)
- **Features:** `accel_x/y/z_g`, `gyro_x/y/z_dps`, `altitude_est_m`, `battery_voltage_v`, `gps_speed_mps`
- **Preprocessing:** StandardScaler normalization
- **Output:** Anomaly score per row (higher = more anomalous, ≥ 0.0 triggers alert)
- **Config:** 100 estimators, 5% contamination, random_state=42

The ML score is returned alongside rule alerts from `engine.py` but currently serves as a supplementary signal — rule alerts are the primary output.

### 3.5 Alert Schema

Every alert is a dictionary with 9 fields:

| Field | Description |
|---|---|
| `timestamp_ms` | When the anomaly was detected |
| `packet_id` | Offending packet |
| `node_id` | Source node |
| `severity` | `warning` or `critical` |
| `confidence` | 0.0 – 1.0 score |
| `reason_code` | Machine-readable code (e.g. `LOW_BATTERY`) |
| `reason_text` | Human-readable explanation |
| `recommended_action` | Operator guidance string |
| `alert_status` | `active`, `acknowledged`, `resolved`, `escalated` |

### 3.6 Validation Pipeline

```
python -m guardian.run_pipeline
```

1. **`metrics.py`** — Runs all 11 scenarios, collects per-scenario counts → `results/metrics/scenario_metrics.csv`
2. **`validation.py`** — Compares collected reason codes against `expectations.py` → `results/metrics/expected_vs_observed.csv`
3. **`pytest -q`** — Runs all unit tests across 10 test files

### 3.7 Test Scenarios

| Scenario | Expected Detection |
|---|---|
| `normal_flight.csv` | No alerts |
| `packet_loss.csv` | `PACKET_LOSS` |
| `sensor_dropout.csv` | `IMU_DROPOUT` |
| `gps_jump.csv` | `GPS_JUMP` |
| `low_battery.csv` | `LOW_BATTERY` |
| `out_of_order_packets.csv` | `OUT_OF_ORDER_PACKET` |
| `duplicate_packet.csv` | `DUPLICATE_PACKET` |
| `frozen_imu.csv` | `IMU_FROZEN` |
| `gps_fix_loss.csv` | `GPS_FIX_LOSS` |
| `gps_imu_inconsistency.csv` | `GPS_IMU_INCONSISTENCY` |
| `combined_fault.csv` | `LOW_BATTERY`, `PACKET_LOSS`, `IMU_DROPOUT`, `GPS_FIX_LOSS`, `GPS_JUMP` |

### 3.8 How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run default scenario (low_battery.csv)
python -m guardian.main

# Run a specific scenario
python -m guardian.main data/scenarios/normal_flight.csv

# Run full validation pipeline (metrics + validation + tests)
python -m guardian.run_pipeline

# Run tests only
pytest -q
```

---

## 4. What Is Still Missing

Phase 1 (detection logic, scenarios, validation, documentation) is complete. The following are the gaps before this system is production-ready or competition-ready.

### 4.1 No Live Telemetry Ingestion

The system only processes CSV files via `replay.py`. There is no:
- Socket listener (UDP/TCP) for live RC aircraft telemetry
- Serial port reader for embedded hardware
- Message queue consumer (MQTT, ZMQ, RabbitMQ)
- REST/WebSocket ingestion endpoint

Without this, the Guardian cannot monitor a real aircraft in flight.

### 4.2 No Dashboard

The `docs/dashboard_contract.md` and `docs/dashboard_handoff.md` define the interface, but no dashboard exists. Missing:
- Real-time telemetry panel (battery, altitude, GPS, link status)
- Live alert feed with severity color coding
- Alert history / incident timeline
- Operator action buttons (acknowledge, escalate, resolve)
- Any web framework (Flask, FastAPI, React, etc.)

### 4.3 No Database Persistence

The `docs/database_contract.md` defines the schema, but no database is connected. Missing:
- Telemetry storage (time-series database or SQL)
- Alert persistence and history
- Operator action logging
- Validation/metrics storage
- Any ORM or database connector

All data currently lives only in memory during a run.

### 4.4 No Operator Action Loop

Alerts are generated but operators cannot interact with them programmatically. Missing:
- Acknowledge / escalate / resolve endpoints
- Alert state transitions beyond the initial `active` status
- Feedback loop from operator decisions back to the Guardian

### 4.5 ML Model Is Minimally Integrated

The Isolation Forest score is computed but:
- It does not trigger structured alerts (only rule violations do)
- There is no threshold tuning or calibration process
- There is no feedback mechanism to retrain on new normal data
- The model is retrained from scratch on every engine startup

### 4.6 No JSON or Structured Log Export

Alerts are printed to console text files. Missing:
- JSON export of alert streams
- Log rotation or structured logging (e.g. Python `logging` module)
- Output that can be consumed directly by a database or dashboard

### 4.7 No False-Positive / False-Negative Metrics

The validation pipeline checks whether expected reason codes appear, but does not measure:
- Precision / recall per rule
- False-alarm rate on the normal flight scenario
- Detection latency (how quickly after the fault the alert fires)
- Alert deduplication (the same fault can fire multiple alerts per packet)

### 4.8 No Configuration System

All thresholds are hardcoded in `rules.py`:
- Packet loss gap: 200ms
- GPS jump threshold: 0.001°
- Battery critical voltage: 10.5V
- IMU consistency threshold: 0.5

There is no config file, environment variable, or CLI flag to tune these without editing source code.

### 4.9 No Deployment or Packaging

Missing:
- `Dockerfile` or container setup
- `setup.py` / `pyproject.toml` for packaging as an installable module
- CI/CD pipeline (GitHub Actions, etc.)
- Environment management (`.env` support)

### 4.10 No Hardware Integration

The project targets RC aircraft but has no:
- Hardware-in-the-loop (HIL) testing setup
- Flight controller interface (MAVLink, ArduPilot, etc.)
- Embedded firmware or embedded Python support
- Latency benchmarks for real-time constraints

---

## Summary

| Area | Status |
|---|---|
| Anomaly detection rules (9 checks) | **Complete** |
| ML anomaly scoring | **Complete (basic)** |
| Alert schema and builder | **Complete** |
| Schema validation | **Complete** |
| 11 test scenarios | **Complete** |
| Unit tests (10 files) | **Complete** |
| Metrics and validation pipeline | **Complete** |
| Documentation contracts | **Complete** |
| Dashboard | **Missing** |
| Database / persistence | **Missing** |
| Live telemetry ingestion | **Missing** |
| Operator action loop | **Missing** |
| JSON export / structured logging | **Missing** |
| Configuration system | **Missing** |
| Deployment / packaging | **Missing** |
| Hardware / RC aircraft integration | **Missing** |
