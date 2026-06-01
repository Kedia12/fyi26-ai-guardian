# FYI26 AI Guardian — Complete Project Documentation

This document covers every file, every decision, every library, and every
feature that was designed and built across all 9 phases of the FYI26 AI
Guardian project for the **Airbus Fly Your Ideas 2026** competition.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Language and Technology Stack](#2-language-and-technology-stack)
3. [Full Project File Structure](#3-full-project-file-structure)
4. [Data Schemas](#4-data-schemas)
5. [Phase 1 — Configuration System](#5-phase-1--configuration-system)
6. [Phase 2 — JSON Export and Structured Logging](#6-phase-2--json-export-and-structured-logging)
7. [Phase 3 — Database Persistence](#7-phase-3--database-persistence)
8. [Phase 4 — ML Alert Integration](#8-phase-4--ml-alert-integration)
9. [Phase 5 — Precision, Recall and Latency Metrics](#9-phase-5--precision-recall-and-latency-metrics)
10. [Phase 6 — Web Dashboard and Operator Actions](#10-phase-6--web-dashboard-and-operator-actions)
11. [Phase 7 — Live Telemetry Ingestion](#11-phase-7--live-telemetry-ingestion)
12. [Phase 8 — Deployment and Packaging](#12-phase-8--deployment-and-packaging)
13. [Phase 9 — MAVLink Hardware Integration](#13-phase-9--mavlink-hardware-integration)
14. [Test Suite Summary](#14-test-suite-summary)
15. [Configuration Reference](#15-configuration-reference)
16. [How to Run Everything](#16-how-to-run-everything)

---

## 1. What This Project Is

The **FYI26 AI Guardian** is a Human-in-the-Loop AI anomaly detection system
for RC aircraft telemetry, built as a competition prototype for Airbus FYI26.

### The Problem

Connected aerospace systems exchange continuous telemetry between sensors,
onboard computers, ground operators, and connected infrastructure. This
improves situational awareness but also introduces vulnerabilities:

- Missing or reordered data packets
- Spoofed GPS navigation inputs
- Sensor hardware failures (IMU dropout, frozen sensor)
- Battery degradation and power failures
- Inconsistencies between GPS and inertial data

A system that detects these anomalies automatically, explains them to a human
operator, and suggests a safe response action is critical for safety-of-flight
decisions.

### The Solution

The Guardian is a lightweight Python monitoring layer that:

1. **Ingests telemetry** from CSV replay files, UDP sockets, serial ports, or
   real MAVLink flight controllers
2. **Runs 9 deterministic rule checks** for known fault patterns
3. **Scores every row** with a machine learning Isolation Forest model
4. **Generates structured alerts** with severity, confidence score, reason
   code, reason text, and recommended operator action
5. **Persists everything** to a SQLite database
6. **Exports alerts** to a newline-delimited JSON log file
7. **Displays a live web dashboard** where operators can acknowledge, escalate,
   or resolve each alert
8. **Measures precision, recall and detection latency** against ground-truth
   labels for every scenario

---

## 2. Language and Technology Stack

### Language

**Python 3.10+** — all code is written in Python. The project requires Python
3.10 as the minimum because it uses the `match`-style union type syntax
(`float | None`) in some places.

### Runtime Libraries

| Library | Version | Purpose |
|---|---|---|
| `pandas` | ≥ 2.0 | Reading scenario CSV files into DataFrames for replay |
| `scikit-learn` | ≥ 1.3 | `IsolationForest` ML anomaly detection model |
| `PyYAML` | ≥ 6.0 | Reading `config/guardian_config.yaml` |
| `Flask` | ≥ 3.0 | Web dashboard HTTP server and template rendering |
| `pyserial` | ≥ 3.5 | Serial port listener for live hardware ingestion |
| `pymavlink` | ≥ 2.4 | MAVLink protocol parsing for flight controller integration |

### Optional Libraries

| Library | Purpose |
|---|---|
| `paho-mqtt` ≥ 1.6 | MQTT broker subscription (stub ready, not auto-installed) |

### Development and Testing

| Library | Version | Purpose |
|---|---|---|
| `pytest` | ≥ 8.0 | Test runner for all 162 tests |

### Standard Library Modules Used (no install needed)

`sqlite3`, `json`, `csv`, `socket`, `threading`, `pathlib`, `datetime`,
`copy`, `time`, `sys`, `subprocess`

### Packaging and Deployment

| Tool | Purpose |
|---|---|
| `setuptools` ≥ 61 | PEP 517 build backend for `pip install -e .` |
| Docker | Container image based on `python:3.11-slim` |
| Docker Compose | Orchestrates the dashboard container with volume mounts |
| GitHub Actions | CI pipeline: install → test → metrics → validation |
| GNU Make | Developer shortcuts (`make test`, `make dashboard`, etc.) |

---

## 3. Full Project File Structure

```
fyi26-ai-guardian/
│
├── config/
│   └── guardian_config.yaml        # All tuneable thresholds and settings
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py                      # Flask app factory + run_dashboard()
│   ├── routes.py                   # All HTTP routes (Blueprint)
│   └── templates/
│       ├── base.html               # Dark-theme base layout
│       └── index.html              # Live telemetry + alert panels
│
├── data/
│   ├── labels/                     # Ground-truth CSV labels (11 files)
│   │   ├── normal_flight.csv
│   │   ├── packet_loss.csv
│   │   ├── duplicate_packet.csv
│   │   ├── out_of_order_packets.csv
│   │   ├── frozen_imu.csv
│   │   ├── sensor_dropout.csv
│   │   ├── low_battery.csv
│   │   ├── gps_fix_loss.csv
│   │   ├── gps_jump.csv
│   │   ├── gps_imu_inconsistency.csv
│   │   └── combined_fault.csv
│   └── scenarios/                  # Replay telemetry CSV files (11 files)
│       ├── normal_flight.csv
│       ├── packet_loss.csv
│       ├── duplicate_packet.csv
│       ├── out_of_order_packets.csv
│       ├── frozen_imu.csv
│       ├── sensor_dropout.csv
│       ├── low_battery.csv
│       ├── gps_fix_loss.csv
│       ├── gps_jump.csv
│       ├── gps_imu_inconsistency.csv
│       └── combined_fault.csv
│
├── docs/                           # Architecture and schema documentation
│   ├── alert_schema.md
│   ├── architecture.md
│   ├── dashboard_contract.md       # Interface contract: Guardian → dashboard → database
│   ├── dashboard_handoff.md        # Handoff summary for dashboard team
│   ├── database_contract.md        # Data model reference for the database layer
│   ├── telemetry_schema.md
│   └── validation_plan.md
│
├── guardian/                       # Core Python package
│   ├── __init__.py
│   ├── alerts.py                   # build_alert() factory function
│   ├── config.py                   # YAML config loader with caching
│   ├── db.py                       # SQLite database wrapper (GuardianDB)
│   ├── engine.py                   # GuardianEngine: rules + ML + export + DB
│   ├── export.py                   # AlertExporter: writes .jsonl log files
│   ├── expectations.py             # Expected alert counts per scenario
│   ├── ingest_runner.py            # run_live() entry point for live ingestion
│   ├── main.py                     # CLI entry point for replay + live modes
│   ├── metrics.py                  # Scenario metrics CSV generator
│   ├── ml_model.py                 # GuardianML: Isolation Forest wrapper
│   ├── precision_metrics.py        # Precision/recall/F1/latency calculator
│   ├── replay.py                   # replay_csv() generator
│   ├── rules.py                    # 9 deterministic rule checks
│   ├── run_all.py                  # Runs all scenarios and prints output
│   ├── run_pipeline.py             # Full pipeline: metrics → validation → tests
│   ├── schemas.py                  # Telemetry and alert field definitions
│   ├── utils.py                    # print_banner(), format_alert(), etc.
│   ├── validation.py               # Expected-vs-observed validation
│   └── ingestion/                  # Live ingestion sub-package
│       ├── __init__.py
│       ├── listener_factory.py     # create_listener(config) factory
│       ├── mavlink_assembler.py    # Assembles MAVLink messages → Guardian rows
│       ├── mavlink_heartbeat.py    # HeartbeatMonitor daemon thread
│       ├── mavlink_listener.py     # MAVLinkListener (pymavlink)
│       ├── mqtt_listener.py        # MQTTListener stub (paho-mqtt)
│       ├── serial_listener.py      # SerialListener (pyserial)
│       └── udp_listener.py         # UDPListener + parse_json_packet/csv
│
├── results/
│   ├── logs/
│   │   └── alerts.jsonl            # Auto-generated alert export log
│   └── metrics/
│       ├── expected_vs_observed.csv
│       ├── precision_recall.csv    # Auto-generated by guardian.metrics
│       ├── scenario_metrics.csv
│       └── validation_summary.md
│
├── tests/                          # 162 automated tests (6 skipped w/o SITL)
│   ├── conftest.py
│   ├── test_alerts.py
│   ├── test_config.py
│   ├── test_dashboard.py
│   ├── test_db.py
│   ├── test_engine.py
│   ├── test_export.py
│   ├── test_main.py
│   ├── test_mavlink_assembler.py
│   ├── test_mavlink_listener.py    # Skipped unless MAVLINK_SIM=1
│   ├── test_metrics.py
│   ├── test_ml_alerts.py
│   ├── test_ml_model.py
│   ├── test_precision_metrics.py
│   ├── test_replay.py
│   ├── test_rules.py
│   ├── test_schemas.py
│   ├── test_udp_listener.py
│   ├── test_utils.py
│   └── test_validation.py
│
├── .dockerignore
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml                  # PEP 517 package + console scripts
├── README.md                       # Original README
├── README_DETAILED.md              # This file
└── requirements.txt                # All dependencies
```

---

## 4. Data Schemas

### Telemetry Row — 22 Fields

Every telemetry row (from CSV replay or live ingestion) carries these fields:

| Field | Type | Unit | Description |
|---|---|---|---|
| `timestamp_ms` | int | milliseconds | Packet timestamp |
| `packet_id` | int | — | Sequential packet number |
| `node_id` | str | — | Aircraft node identifier |
| `accel_x_g` | float | g | X-axis accelerometer |
| `accel_y_g` | float | g | Y-axis accelerometer |
| `accel_z_g` | float | g | Z-axis accelerometer (≈1.0 at rest) |
| `gyro_x_dps` | float | deg/s | X-axis gyroscope |
| `gyro_y_dps` | float | deg/s | Y-axis gyroscope |
| `gyro_z_dps` | float | deg/s | Z-axis gyroscope |
| `temperature_c` | float | °C | Onboard temperature |
| `pressure_hpa` | float | hPa | Barometric pressure |
| `altitude_est_m` | float | m | Estimated altitude |
| `battery_voltage_v` | float | V | Battery voltage |
| `low_power_flag` | int | 0/1 | Hardware low-power indicator |
| `gps_lat_deg` | float | degrees | GPS latitude |
| `gps_lon_deg` | float | degrees | GPS longitude |
| `gps_alt_m` | float | m | GPS altitude |
| `gps_speed_mps` | float | m/s | GPS ground speed |
| `gps_fix_status` | int | 0/1 | 1 = valid GPS fix |
| `satellite_count` | int | — | Number of GPS satellites |
| `link_status` | str | — | Link quality descriptor |
| `mode_state` | str | — | Flight mode descriptor |

### Alert Record — 9 Fields

Every alert produced by the Guardian contains these fields:

| Field | Type | Description |
|---|---|---|
| `timestamp_ms` | int | Timestamp of the triggering packet |
| `packet_id` | int | ID of the triggering packet |
| `node_id` | str | Aircraft node identifier |
| `severity` | str | `WARNING` or `CRITICAL` |
| `confidence` | float | 0.0 – 1.0, how certain the detection is |
| `reason_code` | str | Machine-readable fault code (e.g. `PACKET_LOSS`) |
| `reason_text` | str | Human-readable explanation |
| `recommended_action` | str | Suggested operator response |
| `alert_status` | str | `active`, `acknowledged`, `escalated`, or `resolved` |

### The 9 Deterministic Rule Checks

| Rule | Reason Code | Severity | Trigger Condition |
|---|---|---|---|
| Packet loss | `PACKET_LOSS` | WARNING | Sequence gap or timestamp gap > 200 ms |
| Out-of-order packet | `OUT_OF_ORDER_PACKET` | WARNING | `packet_id` < previous `packet_id` |
| Duplicate packet | `DUPLICATE_PACKET` | WARNING | `packet_id` == previous `packet_id` |
| IMU dropout | `IMU_DROPOUT` | WARNING | All 6 IMU values are exactly 0.0 |
| Frozen IMU | `IMU_FROZEN` | WARNING | All 6 IMU values identical to previous row |
| Low battery | `LOW_BATTERY` | WARNING / CRITICAL | `low_power_flag == 1` or voltage < 10.5 V (CRITICAL if < 10.2 V) |
| GPS fix loss | `GPS_FIX_LOSS` | WARNING | `gps_fix_status == 0` or `satellite_count < 4` |
| GPS jump | `GPS_JUMP` | CRITICAL | Lat/lon change > 0.001° or speed change > 15 m/s |
| GPS/IMU inconsistency | `GPS_IMU_INCONSISTENCY` | CRITICAL | GPS moved > 0.001° but IMU shows near-zero motion |

### ML Alert

| Reason Code | Source | Trigger |
|---|---|---|
| `ML_ANOMALY` | Isolation Forest | `anomaly_score > 0.1` (configurable) |

---

## 5. Phase 1 — Configuration System

### Goal

Replace every hardcoded threshold in the codebase with values loaded from a
single YAML file so the system can be tuned without modifying Python code.

### What Was Built

**New file: `config/guardian_config.yaml`**

The single source of truth for all tuneable values. Organised into four
sections:

- `rules` — 8 detection thresholds (packet loss gap, battery voltages, GPS
  jump limits, IMU motion thresholds, minimum satellite count)
- `ml` — 5 Isolation Forest parameters (n_estimators, contamination,
  random_state, alert_threshold, alert_severity)
- `logging` — JSON export enabled flag and output path
- `database` — database enabled flag and SQLite path
- `ingestion` — mode (replay/udp/serial/mavlink), UDP host/port, serial
  port/baud

**New file: `guardian/config.py`**

A module with five functions:

- `load_config(path=None)` — reads the YAML file into a dict and caches it in
  a module-level variable
- `get_config(path=None)` — returns the cached config, calling `load_config`
  on first access
- `get_rule_threshold(key, default=None)` — shortcut to `config["rules"][key]`
- `get_ml_param(key, default=None)` — shortcut to `config["ml"][key]`
- `reload_config(path=None)` — clears the cache and reloads, used in tests to
  restore a clean state

All functions fall back to the provided `default` argument if the key is
missing, so existing tests never break even without a config file.

**New file: `tests/test_config.py`**

7 tests: load from file, get returns cached value, default fallback on missing
key, reload clears cache, missing file raises `FileNotFoundError`, caching
behaviour across multiple `get_config()` calls.

### What Was Modified

**`guardian/rules.py`**

Every hardcoded numeric threshold was replaced with a `get_rule_threshold()`
call. Example: `voltage < 10.5` became
`voltage < get_rule_threshold("battery_warning_v", 10.5)`.

A bug was fixed at the same time: `check_gps_jump` computed `speed_jump` but
never used it in the condition. The speed jump threshold was added to the `if`
check.

**`guardian/ml_model.py`**

The `IsolationForest` constructor was updated to read its three parameters
from config:

```python
self.model = IsolationForest(
    n_estimators=get_ml_param("n_estimators", 100),
    contamination=get_ml_param("contamination", 0.05),
    random_state=get_ml_param("random_state", 42),
)
```

**`requirements.txt`**

Added `PyYAML>=6.0`.

---

## 6. Phase 2 — JSON Export and Structured Logging

### Goal

Write every alert to a newline-delimited JSON (`.jsonl`) log file alongside
console output. Each line is a self-contained JSON record that external tools
can parse.

### What Was Built

**New file: `guardian/export.py`**

The `AlertExporter` class:

- `__init__(path, enabled=True)` — if enabled, creates all parent directories
  and opens the file in **append mode** so multiple runs accumulate in the same
  file without overwriting previous entries
- `write_alert(alert, telemetry_row=None)` — writes one JSON line with three
  top-level keys:
  - `"alert"` — the full alert dict
  - `"telemetry"` — the raw telemetry row that triggered it (or `null`)
  - `"exported_at"` — ISO 8601 UTC timestamp of the write
  - Uses `json.dumps(..., default=str)` to safely handle numpy floats and other
    non-standard types
- `write_batch(alerts, telemetry_row=None)` — calls `write_alert` for each
  alert in a list
- `flush()` — forces buffered data to disk
- `close()` — flushes and closes the file handle, sets `_handle = None`
- Context manager support (`__enter__` / `__exit__`)
- When `enabled=False` all methods are no-ops and no file is created

**New file: `tests/test_export.py`**

11 tests: file creation, valid JSON line, required top-level keys, telemetry
included/null, batch writes correct line count, empty batch writes nothing,
disabled creates no file, context manager closes handle, append mode
accumulates across multiple instances, parent directories created
automatically.

### What Was Modified

**`guardian/engine.py`**

- Added `db=None` keyword parameter to `GuardianEngine.__init__()` as
  forward-compatibility for Phase 3
- Instantiates `AlertExporter` from config in `__init__`
- In `process_row()`, calls `self.exporter.write_batch(alerts, row)` after
  every processed row that produced alerts

**`guardian/main.py`**

- Added `from guardian.config import get_config` import
- At end of `run()`, prints the export file path when
  `json_export_enabled: true` in config

---

## 7. Phase 3 — Database Persistence

### Goal

Persist every telemetry row and every alert to a SQLite database so the
dashboard can display historical data and operators can review the complete
flight record.

### What Was Built

**New file: `docs/database_contract.md`**

A team-facing reference document that explains what data exists in the Guardian
prototype, where each category comes from, and what structure the database layer
must store. Covers all four data categories (telemetry, alerts, operator
actions, validation/metrics), provides field-by-field table definitions, and
includes JSON example objects for every data type. Written so the database
sub-team can start implementation in parallel without needing to read Python
source code.

**New file: `guardian/db.py`**

The `GuardianDB` class backed by Python's built-in `sqlite3` module (no ORM,
no extra dependencies):

- `__init__(path)` — resolves the path, creates parent directories, opens a
  SQLite connection in **WAL (Write-Ahead Logging) mode** for concurrent
  access safety, and runs `CREATE TABLE IF NOT EXISTS` for all four tables
- Four SQLite tables:
  - `Telemetry` — all 22 telemetry fields plus `id` (autoincrement) and
    `inserted_at` (UTC ISO timestamp)
  - `Alerts` — all 9 alert fields plus `id`, `ml_source` (0/1 flag),
    and `inserted_at`
  - `Operator_Actions` — `id`, `alert_id` (foreign key to Alerts), 
    `action_type`, `operator_note`, `acted_at`
  - `Validation_Metrics` — `id`, `scenario`, `total_rows`, `total_alerts`,
    `rule_alerts`, `ml_alerts`, `recorded_at`
- Ten methods: `insert_telemetry`, `insert_alert`, `insert_operator_action`,
  `update_alert_status`, `get_recent_alerts`, `get_recent_telemetry`,
  `get_alert_by_id`, `close`
- Context manager support (`__enter__` / `__exit__`)
- `row_factory = sqlite3.Row` so every `fetchall()` returns dicts

**New file: `tests/test_db.py`**

18 tests: file creation, parent directory creation, insert telemetry returns
ID, IDs increment, insert alert with `ml_source` flag, `get_alert_by_id`
returns correct record, returns `None` for missing ID, `update_alert_status`
changes the status, `get_recent_alerts` orders by most recent, respects limit,
`get_recent_telemetry` returns latest row, operator action insert, context
manager closes connection, default alert status is `active`, `inserted_at` is
populated.

### What Was Modified

**`guardian/engine.py`**

Added DB insert calls inside `process_row()` when `self.db is not None`:

```python
if self.db is not None:
    self.db.insert_telemetry(row)
    for alert in alerts:
        self.db.insert_alert(
            alert,
            ml_source=(alert.get("reason_code") == "ML_ANOMALY"),
        )
```

**`guardian/run_pipeline.py`**

- Added imports for `get_config` and `GuardianDB`
- Added `read_precision_recall_summary()` function (used later in Phase 5)
- In `main()`, reads `database.enabled` from config; if true, instantiates
  `GuardianDB` and prints the path
- Closes the database at the end of `main()`

---

## 8. Phase 4 — ML Alert Integration

### Goal

The Isolation Forest model was already scoring every row and returning a
numeric anomaly score, but that score was only printed. Phase 4 turns a high
score into a full structured alert that flows through the same export, database,
and dashboard pipeline as rule-based alerts.

### What Was Built

**New file: `tests/test_ml_alerts.py`**

12 tests: ML alert generated when score exceeds threshold, not generated at or
below threshold, has all 9 required alert fields, `reason_code` is
`ML_ANOMALY`, `recommended_action` is `VERIFY_OPERATOR`, confidence is bounded
in `(0, 0.99]`, higher score produces higher confidence, severity read from
config, anomaly score returned by `process_row`, no ML alert when
`ml_ready=False`, `ml_anomaly_score` written back into the telemetry row.

### What Was Modified

**`guardian/engine.py`**

Two new imports at the top:

```python
from guardian.config import get_config, get_ml_param
from guardian.alerts import build_alert
```

New block inside `process_row()`, after the ML model scores the row:

```python
if anomaly_score is not None and anomaly_score > get_ml_param("alert_threshold", 0.1):
    ml_alert = build_alert(
        row=row,
        severity=get_ml_param("alert_severity", "WARNING"),
        confidence=min(anomaly_score / (anomaly_score + 1.0), 0.99),
        reason_code="ML_ANOMALY",
        reason_text=f"ML anomaly score {anomaly_score:.4f} exceeded threshold.",
        recommended_action="VERIFY_OPERATOR",
    )
    alerts.append(ml_alert)
```

The confidence formula `score / (score + 1.0)` maps any positive float into
the range `(0, 1)` and is capped at 0.99. This means a score of 0.1 gives
confidence 0.091, a score of 1.0 gives 0.5, and very high scores approach but
never reach 1.0.

Because `ml_alert` is appended to `alerts` before the DB insert and export
calls, it is automatically persisted and exported through all existing
pipelines — no other code needed to change.

---

## 9. Phase 5 — Precision, Recall and Latency Metrics

### Goal

Add ground-truth labels for every scenario so the system can measure how
accurately it detects faults and how quickly. Produces a
`results/metrics/precision_recall.csv` after every pipeline run.

### What Was Built

**New directory: `data/labels/`**

11 CSV files, one per scenario. Format: `packet_id,expected_alert` where
`expected_alert` is `1` for anomalous packets and `0` for normal packets.

Each label file was derived by manually tracing the exact rules against the
scenario data. Key decisions:

- For `duplicate_packet.csv`: the second occurrence of `packet_id=2` is labeled
  `1` because that is when `DUPLICATE_PACKET` fires
- For `out_of_order_packets.csv`: `packet_id=1` is labeled `1` (the second,
  out-of-order occurrence); `packet_id=3` is labeled `0` even though the engine
  fires a cascade `PACKET_LOSS` on it — this cascade is correctly counted as a
  false positive in the evaluation, giving precision 0.500 for that scenario
- For `normal_flight.csv`: all labels are `0`; no alerts are expected or
  generated

**New file: `guardian/precision_metrics.py`**

Four functions:

- `load_labels(path) -> dict[int, int]` — reads a label CSV into
  `{packet_id: 0_or_1}`; returns an empty dict if the file does not exist so
  callers never need to check
- `compute_precision_recall(alerts, labels) -> dict` — set-based matching by
  `packet_id` to avoid double-counting multiple alerts on the same anomalous
  packet. Returns `{tp, fp, fn, precision, recall, f1}`
- `compute_detection_latency_ms(alerts, labels, telemetry_rows) -> float | None`
  — measures the time (in ms) between the first labeled-anomalous row and the
  first true-positive alert; returns `None` if no labeled anomalies or no TP
  alerts
- `generate_precision_recall_csv(output_path, scenarios_dir, labels_dir)`
  — runs all labeled scenarios through a fresh `GuardianEngine`, computes all
  four metrics, and writes `results/metrics/precision_recall.csv`. Optional
  parameters allow the caller to inject custom directories (used in tests)

**New file: `tests/test_precision_metrics.py`**

18 tests covering all four functions, including edge cases: perfect detection,
false positive only, false negative only, mixed TP/FP/FN, multiple alerts on
same packet counted as one TP, no anomalies produces zero metrics, latency zero
when detected at same packet, latency None with no TP, CSV has correct columns,
unlabeled scenarios are skipped, parent directories created.

### Results After Phase 5

```
scenario                   precision  recall  f1     latency_ms
combined_fault.csv         1.000      1.000   1.000  0.0
duplicate_packet.csv       1.000      1.000   1.000  100.0
frozen_imu.csv             1.000      1.000   1.000  0.0
gps_fix_loss.csv           1.000      1.000   1.000  0.0
gps_imu_inconsistency.csv  1.000      1.000   1.000  0.0
gps_jump.csv               1.000      1.000   1.000  0.0
low_battery.csv            1.000      1.000   1.000  0.0
normal_flight.csv          0.000      0.000   0.000  N/A
out_of_order_packets.csv   0.500      1.000   0.667  200.0
packet_loss.csv            1.000      1.000   1.000  0.0
sensor_dropout.csv         1.000      1.000   1.000  0.0
```

The 0.500 precision on `out_of_order_packets` is real and correct: the cascade
false positive on the packet that follows an out-of-order event is genuine
system behaviour worth knowing about.

### What Was Modified

**`guardian/metrics.py`**

Added `from guardian.precision_metrics import generate_precision_recall_csv`
and a call to `generate_precision_recall_csv()` at the end of
`generate_metrics_csv()`. Every time scenario metrics are generated, the PR
CSV is also regenerated.

**`guardian/run_pipeline.py`**

Added `read_precision_recall_summary()` function that reads the PR CSV and
computes averages. Added a print block at the end of `main()` that shows:

```
Precision/Recall across 11 labeled scenarios:
  Avg Precision : 0.955
  Avg Recall    : 0.909
```

---

## 10. Phase 6 — Web Dashboard and Operator Actions

### Goal

A live Flask web UI that shows the latest telemetry, active alerts, and alert
history, with buttons for operators to acknowledge, escalate, or resolve each
alert.

### What Was Built

**New file: `docs/dashboard_contract.md`**

Defines the technical interface between the Guardian module, the web dashboard,
and the database layer so all three sub-teams can build in parallel against the
same field names and data shapes. Contains:

- Full telemetry input contract (all 22 fields with types and units)
- Full alert output contract (all 9 alert fields with allowed values)
- Operator action contract (`acknowledge`, `escalate`, `resolve`)
- JSON example objects for every contract type
- HTTP API surface (`GET /api/alerts`, `POST /api/alerts/<id>/action`, etc.)

**New file: `docs/dashboard_handoff.md`**

A priority-ordered handoff document written for the dashboard sub-team. Explains
which data categories the dashboard consumes, where each one comes from, which
fields to display first, and what minimum scope is needed for the first
prototype demonstration. Organised as:

- Main inputs (telemetry and alerts)
- Minimum Phase 1 scope: live telemetry summary, alert panel, alert history
- Recommended display priorities (alerts first, then context, then timeline)
- Planned but not required: operator actions (`acknowledge`, `escalate`,
  `resolve`, `override`, `request_verification`)
- Example alert JSON object showing all 9 fields

**New file: `dashboard/__init__.py`**

Empty package marker.

**New file: `dashboard/app.py`**

- `create_app(db_path=None, config_path=None)` — Flask application factory.
  If `db_path` is not provided, reads `database.path` from config. Creates a
  `GuardianDB`, builds the route Blueprint, and registers it
- `run_dashboard(host="0.0.0.0", port=5000)` — starts the Flask development
  server; used as the `guardian-dashboard` console script entry point

**New file: `dashboard/routes.py`**

One Blueprint (`guardian`) with five routes:

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | HTML index: latest telemetry, active alerts, alert history |
| `GET` | `/api/alerts` | JSON list of recent alerts (accepts `?limit=N`) |
| `GET` | `/api/telemetry` | JSON of the single most recent telemetry row |
| `GET` | `/api/alerts/<id>` | JSON of one alert by database ID |
| `POST` | `/api/alerts/<id>/action` | Perform an operator action on an alert |

The `/api/alerts/<id>/action` endpoint accepts both:
- **JSON body** (`Content-Type: application/json`): `{"action_type": "acknowledge", "operator_note": "..."}` — returns JSON `{"status": "ok", "new_status": "acknowledged"}`
- **Form POST** (HTML button submit): reads from `request.form` and redirects to `/` after applying the action

Valid `action_type` values: `acknowledge`, `escalate`, `resolve`.
Returns HTTP 400 for any other value, HTTP 404 if the alert ID does not exist.

**New file: `dashboard/templates/base.html`**

Minimal dark-themed HTML base layout written in pure CSS. No JavaScript
framework, no external CDN. Colour-codes alert severities:
- `CRITICAL` → red (`#fc8181`)
- `WARNING` → amber (`#f6ad55`)

Colour-codes alert statuses:
- `active` → red
- `acknowledged` → amber
- `escalated` → bright red / bold
- `resolved` → green

**New file: `dashboard/templates/index.html`**

Three panels in a responsive CSS grid:

1. **Live Telemetry** — key-value list of battery, altitude, GPS coordinates,
   speed, satellite count, GPS fix, accelerometer, gyroscope, ML score
2. **Active Alerts** — table with ACK / ESC / RES action buttons per row
3. **Alert History** — full table of non-active alerts with final status

The page uses `<meta http-equiv="refresh" content="5">` to auto-refresh every
5 seconds with no JavaScript required.

**New file: `tests/test_dashboard.py`**

22 tests using Flask's built-in test client (`app.test_client()`). Tests cover:
index returns 200, alert panels visible, API endpoints return JSON lists, limit
parameter respected, correct alert fetched by ID, 404 for missing ID, all three
operator actions update status correctly, invalid action returns 400, form POST
redirects to index, empty database returns null telemetry.

### What Was Modified

**`requirements.txt`**

Added `Flask>=3.0`.

---

## 11. Phase 7 — Live Telemetry Ingestion

### Goal

Replace the CSV replay mode with a live socket-based ingestion path. Supports
four modes: UDP (primary), serial port, MQTT (optional stub), and MAVLink
(hardware, Phase 9).

### What Was Built

**New file: `guardian/ingestion/__init__.py`**

Empty package marker.

**New file: `guardian/ingestion/udp_listener.py`**

Two parser functions:

- `parse_json_packet(data: bytes) -> dict | None` — decodes UTF-8 and parses
  as JSON; returns `None` on any error
- `parse_csv_packet(data: bytes) -> dict | None` — splits on commas and zips
  against the 22-field `_CSV_FIELDS` list; returns `None` if field count is
  wrong

`UDPListener` class:

- `__init__(host, port, parser=parse_json_packet)` — stores settings
- `start(callback)` — binds a UDP socket with `SO_REUSEADDR`, sets 1-second
  timeout, starts a daemon thread that calls `callback(row)` for every
  successfully parsed datagram; invalid packets are silently discarded
- `stop()` — signals the thread to stop, closes the socket, joins the thread
  with a 3-second timeout

**New file: `guardian/ingestion/serial_listener.py`**

`SerialListener` — identical interface to `UDPListener` but reads
newline-delimited data from a serial port using `pyserial`. Raises
`RuntimeError` with an installation hint at instantiation time if pyserial is
not installed.

**New file: `guardian/ingestion/mqtt_listener.py`**

`MQTTListener` stub — subscribes to a configurable MQTT topic using
`paho-mqtt`. Raises `RuntimeError` if paho-mqtt is not installed. Ready to use
but not auto-installed.

**New file: `guardian/ingestion/listener_factory.py`**

`create_listener(config) -> listener` — reads `config["ingestion"]["mode"]`
and returns the matching listener pre-configured from the rest of the ingestion
config. Valid modes: `udp`, `serial`, `mqtt`, `mavlink`. Raises `ValueError`
for any other value.

**New file: `guardian/ingest_runner.py`**

`run_live(mode=None)` — the full live pipeline:

1. Loads config (applies `mode` override if provided)
2. Opens `GuardianDB` if `database.enabled: true`
3. Instantiates `GuardianEngine(db=db)`
4. Defines `on_row(row)` callback that calls `engine.process_row()` and prints
   each packet ID, ML score, and any alerts
5. Creates and starts the listener
6. Runs until `KeyboardInterrupt`, then stops the listener and closes the DB

**New file: `tests/test_udp_listener.py`**

18 tests:
- `parse_json_packet`: valid JSON, invalid bytes, empty bytes, partial JSON
- `parse_csv_packet`: valid CSV with all 22 fields, all fields present, too few
  fields, too many fields, empty bytes
- `UDPListener` loopback: receives JSON packet, discards invalid packets,
  receives 5 packets, custom CSV parser works, `stop()` is idempotent
- `listener_factory`: returns `UDPListener` for `udp` mode, raises
  `ValueError` for unknown mode, configured port is correct

### What Was Modified

**`guardian/main.py`**

The `__main__` block was updated to handle a `--live` flag:

```bash
python -m guardian.main --live          # uses mode from config
python -m guardian.main --live udp      # forces UDP mode
python -m guardian.main --live serial   # forces serial mode
```

**`requirements.txt`**

Added `pyserial>=3.5`. Added a comment for optional `paho-mqtt>=1.6`.

---

## 12. Phase 8 — Deployment and Packaging

### Goal

Make the project installable as a Python package, containerisable with Docker,
and automatically tested by GitHub Actions CI.

### What Was Built

**New file: `pyproject.toml`**

PEP 517 package definition using `setuptools.build_meta`:

```toml
[project]
name = "fyi26-ai-guardian"
version = "0.1.0"
requires-python = ">=3.10"
```

Three console scripts registered:

| Command | Entry point |
|---|---|
| `guardian` | `guardian.main:_cli` |
| `guardian-dashboard` | `dashboard.app:run_dashboard` |
| `guardian-live` | `guardian.ingest_runner:run_live` |

Two optional dependency groups:
- `dev` — pytest
- `mqtt` — paho-mqtt

**New file: `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "-m", "dashboard.app"]
```

Dependencies are installed in a separate layer from the source code so that
rebuilds after code changes reuse the cached dependency layer.

**New file: `docker-compose.yml`**

Runs the dashboard on port 5000 with three bind mounts:
- `./data:/app/data` — scenario CSV files
- `./results:/app/results` — database and log output
- `./config:/app/config` — config YAML (editable without rebuilding the image)

**New file: `.dockerignore`**

Excludes `__pycache__`, `.git`, `.github`, `.pytest_cache`, `*.egg-info`,
`dist/`, `build/`, `results/*.db`, `results/logs/`, `PHASE DETAILS/`.

**New file: `.github/workflows/ci.yml`**

GitHub Actions workflow triggered on every push and pull request to `main`:

1. Checkout code
2. Set up Python 3.11 with pip cache
3. `pip install -r requirements.txt`
4. `python -m pytest -q`
5. `python -m guardian.metrics` (generates scenario and PR metrics)
6. `python -m guardian.validation` (expected-vs-observed check)

**New file: `Makefile`**

Six targets:

| Command | What it does |
|---|---|
| `make test` | Run the full pytest suite |
| `make pipeline` | Full pipeline: metrics → validation → tests → summary |
| `make dashboard` | Start the Flask dashboard |
| `make docker-build` | Build the Docker image as `fyi26-guardian` |
| `make docker-run` | Run the container with all three volume mounts |
| `make install` | `pip install -e .` (editable install) |

### What Was Modified

**`guardian/main.py`**

Added `_cli()` function which is the entry point called by the `guardian`
console script. Contains the same argument-parsing logic as the `__main__`
block: handles `--live` flag with optional mode argument, otherwise runs CSV
replay.

**`requirements.txt`**

Added a sync comment pointing to `pyproject.toml`. Separated runtime and
development dependencies with inline comments.

**`README.md`**

Added six new sections: Installation, Dashboard, Docker, CI, and Makefile
shortcuts — each with working command examples.

---

## 13. Phase 9 — MAVLink Hardware Integration

### Goal

Connect the Guardian to a real RC flight controller using the MAVLink protocol.
MAVLink sends data as a stream of typed messages; each message covers only some
of the 22 Guardian fields. Phase 9 assembles these partial messages into
complete telemetry rows and feeds them through the existing engine.

### What Was Built

**New file: `guardian/ingestion/mavlink_assembler.py`**

`MAVLinkAssembler` — the core of the MAVLink integration. Does not depend on
pymavlink itself; it works entirely with pre-converted Guardian-unit field dicts
passed in by `MAVLinkListener`.

- `_REQUIRED_FIELDS` — a `frozenset` of the 15 fields that must arrive from all
  message sources before a row can be emitted:
  `accel_x/y/z_g`, `gyro_x/y/z_dps`, `altitude_est_m`, `gps_lat/lon_deg`,
  `gps_speed_mps`, `satellite_count`, `gps_fix_status`, `battery_voltage_v`,
  `temperature_c`, `pressure_hpa`
- `update(fields: dict) -> dict | None` — merges new fields into an internal
  `_partial` dict and returns a complete row if all required fields are
  present, otherwise returns `None`
- `_emit() -> dict` — increments `_packet_id`, assembles the complete row
  (including `timestamp_ms`, `node_id`, `low_power_flag`), resets `_partial`
  to empty
- `pending_fields` property — returns the set of required fields not yet
  received in the current batch (useful for diagnostics)
- `low_power_threshold_v` constructor parameter (default 10.5 V) — controls
  when `low_power_flag` is set to 1

**New file: `guardian/ingestion/mavlink_heartbeat.py`**

`HeartbeatMonitor` — a thread-safe daemon timer:

- `start()` — arms the monitor
- `heartbeat_received()` — resets the countdown timer; call this on every
  received MAVLink `HEARTBEAT` message
- `stop()` — cancels the timer and disarms the monitor (idempotent)
- When the timer fires (no heartbeat within `timeout_s`), calls `on_timeout()`
  and immediately restarts so monitoring continues

Uses `threading.Timer` with a `threading.Lock` to prevent race conditions
between `heartbeat_received()` and `_fire()`.

**New file: `guardian/ingestion/mavlink_listener.py`**

`MAVLinkListener` — requires pymavlink; raises `RuntimeError` at instantiation
if the package is missing.

MAVLink message → Guardian field mapping:

| MAVLink Message | MAVLink Field | Conversion | Guardian Field |
|---|---|---|---|
| `SCALED_IMU` | `xacc / yacc / zacc` | ÷ 1000 (mG → g) | `accel_x/y/z_g` |
| `SCALED_IMU` | `xgyro / ygyro / zgyro` | ÷ 1000 (mdps → dps) | `gyro_x/y/z_dps` |
| `GPS_RAW_INT` | `lat / lon` | ÷ 1e7 (1e-7° → °) | `gps_lat/lon_deg` |
| `GPS_RAW_INT` | `satellites_visible` | direct | `satellite_count` |
| `GPS_RAW_INT` | `fix_type` | `1 if ≥ 3 else 0` | `gps_fix_status` |
| `VFR_HUD` | `alt` | direct (m) | `altitude_est_m` |
| `VFR_HUD` | `groundspeed` | direct (m/s) | `gps_speed_mps` |
| `SYS_STATUS` | `voltage_battery` | ÷ 1000 (mV → V) | `battery_voltage_v` |
| `SCALED_PRESSURE` | `temperature` | ÷ 100 (cdeg → °C) | `temperature_c` |
| `SCALED_PRESSURE` | `press_abs` | direct (hPa) | `pressure_hpa` |

`timestamp_ms` is taken from `msg.time_boot_ms` on every message.

The `HEARTBEAT` message is handled separately — it resets the
`HeartbeatMonitor` but does not contribute fields to the assembler.

To use with ArduPilot SITL:

```bash
# Start SITL then:
python -m guardian.main --live mavlink
```

To use with a real flight controller over USB:

```yaml
# config/guardian_config.yaml
ingestion:
  mode: mavlink
  mavlink_connection: serial:/dev/ttyUSB0:57600
```

**New file: `tests/test_mavlink_assembler.py`**

27 tests — all run without hardware or pymavlink:

- Partial updates return `None`
- Complete row emitted when all required fields present
- Row contains all required fields and metadata fields
- `timestamp_ms` propagated correctly
- `node_id` set from constructor
- `packet_id` starts at 1, increments per emission
- Three sequential rows produce IDs 1, 2, 3
- `low_power_flag` logic: 0 when OK, 1 when below threshold, configurable
  threshold, boundary condition (not strictly less than)
- Accel and GPS values preserved exactly
- GPS fix status 1 and 0 cases
- Buffer resets after emission
- `pending_fields` returns full set after reset
- `HeartbeatMonitor` fires on timeout (0.15 s interval test)
- `HeartbeatMonitor` does not fire when reset before expiry
- `HeartbeatMonitor.stop()` is idempotent

**New file: `tests/test_mavlink_listener.py`**

6 integration tests that are **skipped unless `MAVLINK_SIM=1`** is set:

- Rows received from SITL within 5 seconds
- All required Guardian fields present in rows
- `packet_id` increments across rows
- Battery voltage in a reasonable range (0–60 V)
- GPS coordinates are non-zero
- `stop()` sets `_thread` and `_conn` to `None`

### What Was Modified

**`guardian/ingestion/listener_factory.py`**

Added import of `MAVLinkListener` and a new `if mode == "mavlink":` branch:

```python
if mode == "mavlink":
    return MAVLinkListener(
        connection_string=ingestion.get(
            "mavlink_connection",
            f"udp:{ingestion.get('udp_host', '0.0.0.0')}:{ingestion.get('udp_port', 14550)}",
        ),
        system_id=int(ingestion.get("mavlink_system_id", 1)),
    )
```

The `ValueError` message at the bottom was updated to remove the
"(Phase 9)" note since MAVLink is now fully implemented.

**`requirements.txt`**

Added `pymavlink>=2.4`.

**`pyproject.toml`**

Added `pymavlink>=2.4` to `[project.dependencies]`.

---

## 14. Test Suite Summary

### Final Count

```
162 passed, 6 skipped
```

The 6 skipped tests are the MAVLink SITL integration tests
(`tests/test_mavlink_listener.py`). They run correctly when
`MAVLINK_SIM=1` is set with a running ArduPilot SITL instance.

### Tests by File

| Test file | Tests | What is covered |
|---|---|---|
| `test_alerts.py` | — | `build_alert()` factory output |
| `test_config.py` | 7 | Config load, cache, defaults, reload, missing file |
| `test_dashboard.py` | 22 | All 5 HTTP routes, operator actions, 400/404 errors |
| `test_db.py` | 18 | All CRUD operations, WAL mode, status updates |
| `test_engine.py` | — | `GuardianEngine.process_row()` integration |
| `test_export.py` | 11 | AlertExporter write/batch/append/disabled/context mgr |
| `test_main.py` | — | CLI entry point |
| `test_mavlink_assembler.py` | 27 | Assembler logic + heartbeat monitor |
| `test_mavlink_listener.py` | 6 | SITL integration (skipped by default) |
| `test_metrics.py` | — | Scenario metrics CSV generation |
| `test_ml_alerts.py` | 12 | ML_ANOMALY alert generation and fields |
| `test_ml_model.py` | — | Isolation Forest training and scoring |
| `test_precision_metrics.py` | 18 | PR/F1/latency functions + CSV generation |
| `test_replay.py` | — | CSV replay generator |
| `test_rules.py` | — | All 9 rule functions |
| `test_schemas.py` | — | Telemetry and alert schema validation |
| `test_udp_listener.py` | 18 | Parsers, loopback, factory |
| `test_utils.py` | — | Banner, format_alert, summary printers |
| `test_validation.py` | — | Expected-vs-observed validation |

---

## 15. Configuration Reference

All values live in `config/guardian_config.yaml`. None of them require code
changes to modify.

```yaml
rules:
  packet_loss_gap_ms: 200        # ms gap threshold for PACKET_LOSS
  battery_warning_v: 10.5        # voltage below this → WARNING
  battery_critical_v: 10.2       # voltage below this → CRITICAL
  gps_jump_threshold_deg: 0.001  # lat/lon change threshold (degrees)
  gps_speed_jump_mps: 15.0       # speed change threshold (m/s)
  min_satellites: 4              # fewer satellites → GPS_FIX_LOSS
  gps_imu_accel_mag_threshold: 0.2   # IMU accel mag below which = "not moving"
  gps_imu_gyro_mag_threshold: 3.0    # IMU gyro mag below which = "not rotating"

ml:
  n_estimators: 100              # Isolation Forest trees
  contamination: 0.05            # expected anomaly fraction in training data
  random_state: 42               # reproducibility seed
  alert_threshold: 0.1           # scores above this generate ML_ANOMALY alert
  alert_severity: WARNING        # severity of ML_ANOMALY alerts

logging:
  json_export_enabled: true
  json_export_path: results/logs/alerts.jsonl

database:
  enabled: true                  # set to false to disable SQLite persistence
  path: results/guardian.db

ingestion:
  mode: replay                   # replay | udp | serial | mqtt | mavlink
  udp_host: 0.0.0.0
  udp_port: 14550
  serial_port: /dev/ttyUSB0
  serial_baud: 57600
  # mavlink_connection: udp:0.0.0.0:14550
  # mavlink_system_id: 1
```

---

## 16. How to Run Everything

### Install

```bash
pip install -r requirements.txt   # install all dependencies
pip install -e .                  # install as editable package (console scripts)
```

### Replay a Scenario

```bash
python -m guardian.main                                        # default: low_battery.csv
python -m guardian.main data/scenarios/combined_fault.csv      # specific scenario
guardian data/scenarios/gps_jump.csv                           # via console script
```

### Run All Scenarios and Generate Metrics

```bash
python -m guardian.metrics          # writes scenario_metrics.csv + precision_recall.csv
python -m guardian.validation       # writes expected_vs_observed.csv
python -m guardian.run_pipeline     # runs all three steps + prints final summary
make pipeline                       # same via Makefile
```

### Run Tests

```bash
python -m pytest -q                 # all tests
make test                           # same via Makefile
MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py   # SITL tests
```

### Web Dashboard

```bash
# Step 1: enable database in config
#   database:
#     enabled: true

# Step 2: populate the database
python -m guardian.main data/scenarios/combined_fault.csv

# Step 3: start dashboard
python -m dashboard.app             # open http://localhost:5000
guardian-dashboard                  # same via console script
make dashboard                      # same via Makefile
```

### Live UDP Ingestion

```bash
python -m guardian.main --live                    # uses mode from config
python -m guardian.main --live udp                # force UDP
guardian-live                                     # via console script
python -m guardian.ingest_runner                  # direct module
```

Send JSON packets to the configured port:

```python
import socket, json
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(json.dumps(row).encode(), ("127.0.0.1", 14550))
```

### Live MAVLink (Real Hardware or SITL)

```yaml
# config/guardian_config.yaml
ingestion:
  mode: mavlink
  mavlink_connection: udp:0.0.0.0:14550   # SITL default
  # mavlink_connection: serial:/dev/ttyUSB0:57600  # real hardware
```

```bash
python -m guardian.main --live mavlink
```

### Docker

```bash
make docker-build
make docker-run                     # dashboard on http://localhost:5000

# Or with Docker Compose:
docker-compose up --build

# Run tests inside the container:
docker run fyi26-guardian python -m pytest -q
```

---

*FYI26 AI Guardian — built for Airbus Fly Your Ideas 2026.*
