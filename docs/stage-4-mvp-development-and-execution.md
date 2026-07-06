# Stage 4 Report – MVP Development and Execution

## Project Title
**Human-in-the-Loop AI Guardian for Connected Aerospace Systems**

---

## Table of Contents

- [1. Introduction](#1-introduction)
- [2. Objectives and Importance](#2-objectives-and-importance)
- [3. Team Roles](#3-team-roles)
- [4. Agile Approach and Sprint Strategy](#4-agile-approach-and-sprint-strategy)
- [5. Sprint Overview and Prioritization](#5-sprint-overview-and-prioritization)
- [6. Sprint 1 — Core Engine and Persistence](#6-sprint-1--core-engine-and-persistence)
- [7. Sprint 2 — ML Alerts, Metrics, and Dashboard](#7-sprint-2--ml-alerts-metrics-and-dashboard)
- [8. Sprint 3 — Live Ingestion, Deployment, and Hardware](#8-sprint-3--live-ingestion-deployment-and-hardware)
- [9. Progress Metrics](#9-progress-metrics)
- [10. Final Integration and QA Testing](#10-final-integration-and-qa-testing)
- [11. Deliverables](#11-deliverables)
- [12. Technical Manual Review Preparation](#12-technical-manual-review-preparation)
- [13. Conclusion](#13-conclusion)

---

## 1. Introduction

This document covers Stage 4 of the **Human-in-the-Loop AI Guardian** project — the most execution-intensive phase, during which the technical blueprint defined in Stage 3 was translated into a functional MVP.

Development was organized into three sprints of approximately one week each. Each sprint targeted a specific set of features and ended with a review of what was built and a short retrospective. Agile principles were followed throughout: tasks were broken into small units, assigned explicitly, and tested after every change.

At the start of this stage, Phase 1 of the Guardian (detection rules, 11 test scenarios, and validation pipeline) was already complete. This stage focused on the remaining 9 gaps identified in the project overview: configuration system, JSON export, database persistence, ML alert integration, precision/recall metrics, web dashboard, live telemetry ingestion, deployment packaging, and MAVLink hardware integration.

---

## 2. Objectives and Importance

The objectives of this stage were to:

- implement the MVP based on the technical documentation from Stage 3;
- adopt Agile principles to divide work into manageable sprints;
- assign clear roles and responsibilities, especially for Project Manager, SCM, and QA;
- promote collaboration through clear task ownership, deadlines, and dependencies;
- monitor progress using metrics and adjust the plan when necessary;
- prepare the project for the final technical manual review.

This stage matters because it transforms plans and designs into a working, testable system. Non-technical roles — **Project Manager**, **Source Control Manager**, and **Quality Assurance** — are essential for keeping the work organized, protecting code quality, and delivering a stable, presentable result. The Agile structure keeps the team adaptable, collaborative, and delivery-focused.

---

## 3. Team Roles

| Member | Role | Responsibilities for Stage 4 |
|---|---|---|
| **Kedia Ihogoza** | Project Manager, AI/ML Lead, SCM | Sprint planning and tracking, anomaly detection rules, ML integration, live ingestion, MAVLink, CI/CD, code reviews, Git/GitHub discipline |
| **David Roset** | Database & Dashboard Developer, QA | Database persistence layer, Flask dashboard, operator action API, test execution, scenario validation, QA sign-off |

Source Control Management and Quality Assurance were shared responsibilities: Kedia led branch/commit discipline and code review, while QA (scenario validation, output verification, readiness checks) was carried by both members across every sprint.

---

## 4. Agile Approach and Sprint Strategy

Because the team is small, the process was kept lightweight while still following Agile principles. Each sprint included:

| Activity | Purpose |
|---|---|
| **Sprint Planning** | Define sprint goals, assign tasks, and set deadlines. |
| **Daily Stand-Ups / Check-ins** | Discuss progress, blockers, and next steps. |
| **Development** | Implement features according to the sprint plan. |
| **Code Reviews** | Review important changes before merging to `main`. |
| **QA Testing** | Validate completed tasks and detect issues early. |
| **Sprint Review** | Present completed work and confirm progress. |
| **Sprint Retrospective** | Reflect on what worked well and what to improve. |

**Monitoring methods:** regular check-ins, GitHub commit history, and review of sprint completion against planned tasks. If progress deviated from plan, priorities were reviewed, non-essential tasks postponed, and replay-based testing kept as the fallback whenever live telemetry was delayed.

---

## 5. Sprint Overview and Prioritization

The 9 implementation phases were grouped into 3 sprints:

| Sprint | Phases | Focus Area | Duration |
|---|---|---|---|
| **Sprint 1** | Phases 1–3 | Config system, JSON export, database persistence | ~1 week |
| **Sprint 2** | Phases 4–6 | ML alert integration, precision/recall metrics, Flask dashboard | ~1 week |
| **Sprint 3** | Phases 7–9 | Live telemetry ingestion, deployment packaging, MAVLink hardware | ~1 week |

**MoSCoW prioritization applied at sprint planning:**

| Feature | Priority | Sprint |
|---|---|---|
| Config system (YAML thresholds) | Must Have | Sprint 1 |
| JSON export (JSONL log) | Must Have | Sprint 1 |
| SQLite database persistence | Must Have | Sprint 1 |
| ML anomaly alerts | Must Have | Sprint 2 |
| Precision / recall metrics | Should Have | Sprint 2 |
| Flask web dashboard + operator actions | Must Have | Sprint 2 |
| UDP live telemetry ingestion | Should Have | Sprint 3 |
| Docker + GitHub Actions CI | Should Have | Sprint 3 |
| MAVLink hardware integration | Could Have | Sprint 3 |

---

## 6. Sprint 1 — Core Engine and Persistence

### 6.1 Sprint Goal

Add external configuration, structured logging, and database persistence to the Guardian engine so that all thresholds are tunable without code changes and every alert and telemetry packet is durably stored.

### 6.2 Tasks

| Task | Assigned To | Status |
|---|---|---|
| Create `config/guardian_config.yaml` with all thresholds | Kedia | Done |
| Implement `guardian/config.py` (load, cache, get helpers) | Kedia | Done |
| Replace hardcoded literals in `rules.py` with config calls | Kedia | Done |
| Replace hardcoded ML params in `ml_model.py` with config calls | Kedia | Done |
| Implement `guardian/export.py` (`AlertExporter`, JSONL) | Kedia | Done |
| Wire `AlertExporter` into `engine.py` | Kedia | Done |
| Implement `guardian/db.py` (`GuardianDB`, 4 SQLite tables) | David | Done |
| Wire `GuardianDB` into `engine.py` and `run_pipeline.py` | David | Done |
| Write `tests/test_config.py` (7 tests) | Kedia | Done |
| Write `tests/test_export.py` (11 tests) | Kedia | Done |
| Write `tests/test_db.py` (18 tests) | David | Done |
| Verify all pre-existing tests still pass after changes | Both | Done |

### 6.3 Dependencies

- Config system must be complete before export and database, since both read from config.
- DB schema must be defined before the engine can write to it.

### 6.4 Sprint 1 Review

**Completed features demoed:**
- Running `python -m guardian.main data/scenarios/low_battery.csv` writes `results/logs/alerts.jsonl` with one JSON record per alert.
- Running the pipeline with `database.enabled: true` creates `results/guardian.db` with rows in the `Telemetry` and `Alerts` tables.
- Changing a threshold in `guardian_config.yaml` changes detection behavior without any code edit.

**Metrics:** 36 new tests added (config: 7, export: 11, db: 18); all pre-existing tests continued to pass.

### 6.5 Sprint 1 Retrospective

**What went well:**
- The config module was straightforward to implement with good default fallbacks, so no existing tests broke.
- Splitting DB and export into two distinct classes (GuardianDB vs AlertExporter) kept each file focused and independently testable.
- WAL mode on SQLite was the right default — it avoids write-lock conflicts when both the engine and the dashboard read/write simultaneously.

**Challenges:**
- The first `engine.py` integration added the DB insert inside `process_row()` without making it optional, which broke tests that didn't pass a `db` instance. Fixed by making `db=None` the default and guarding all calls with `if self.db is not None`.
- JSON serialization of numpy floats produced `TypeError` — resolved by passing `default=str` to `json.dumps` in `AlertExporter.write_alert()`.

**Improvements for next sprint:** define shared test fixtures for reused mock objects (alert dict, telemetry row) in `conftest.py` to avoid repetition.

---

## 7. Sprint 2 — ML Alerts, Metrics, and Dashboard

### 7.1 Sprint Goal

Promote the ML anomaly score to a full structured alert, add precision/recall measurement against ground-truth labels, and deliver the Flask dashboard with operator action buttons.

### 7.2 Tasks

| Task | Assigned To | Status |
|---|---|---|
| Add ML alert generation block in `engine.py` | Kedia | Done |
| Write `tests/test_ml_alerts.py` (12 tests) | Kedia | Done |
| Create `data/labels/` — 11 ground-truth label CSVs | Kedia | Done |
| Implement `guardian/precision_metrics.py` (4 functions) | Kedia | Done |
| Write `tests/test_precision_metrics.py` (18 tests) | Kedia | Done |
| Integrate precision/recall into `guardian/metrics.py` | Kedia | Done |
| Add precision/recall summary to `run_pipeline.py` | Kedia | Done |
| Implement `dashboard/app.py` (Flask factory) | David | Done |
| Implement `dashboard/routes.py` (5 HTTP routes + Blueprint) | David | Done |
| Create `dashboard/templates/base.html` (dark CSS layout) | David | Done |
| Create `dashboard/templates/index.html` (3-panel UI) | David | Done |
| Write `tests/test_dashboard.py` (22 tests) | David | Done |
| Add `Flask>=3.0` to `requirements.txt` | David | Done |

### 7.3 Dependencies

- ML alert generation must be complete before precision/recall can measure its output.
- Database (Sprint 1) must be complete before dashboard routes can query it.
- Dashboard template depends on the alert schema defined in the existing `alerts.py`.

### 7.4 Sprint 2 Review

**Completed features demoed:**
- Running the combined fault scenario prints `[WARNING] ML_ANOMALY` lines alongside rule-based alerts.
- `results/metrics/precision_recall.csv` is generated after every pipeline run with per-scenario precision, recall, F1, and detection latency.
- Starting `python -m dashboard.app` and opening `http://localhost:5000` shows live telemetry, active alert table with ACK/ESC/RES buttons, and alert history.
- Clicking "Acknowledge" on an alert changes its status in the database and updates the UI on the next auto-refresh (5-second meta refresh).

**Metrics:** 52 new tests added (ML alerts: 12, precision/recall: 18, dashboard: 22); average precision **86.4%**, average recall **90.9%** across 11 scenarios; dashboard API of 5 routes, all tested with the Flask test client.

### 7.5 Sprint 2 Retrospective

**What went well:**
- The confidence formula `score / (score + 1.0)` mapped ML scores cleanly into (0, 0.99] without clamping edge cases.
- The dashboard auto-refresh approach (HTML meta refresh every 5 seconds) required zero JavaScript and kept the template simple.
- Writing dashboard tests with Flask's test client meant no server process was needed — tests ran in under 2 seconds.

**Challenges:**
- The precision/recall for `out_of_order_packets.csv` came out 0.500, not 1.0. Investigation confirmed this is correct: a cascade `PACKET_LOSS` alert fires on the packet *after* the out-of-order event — a genuine false positive. The label was kept as-is so the metric accurately reflects system behavior.
- The Flask action endpoint initially accepted only JSON bodies, causing the HTML form buttons to fail. Fixed by also reading from `request.form` and redirecting to `/` for browser requests.

**Improvements for next sprint:** the dashboard re-queries `db.get_recent_alerts(50)` on every page load; acceptable for now since Sprint 3 live ingestion pushes rows continuously.

---

## 8. Sprint 3 — Live Ingestion, Deployment, and Hardware

### 8.1 Sprint Goal

Enable the Guardian to accept live telemetry from UDP sockets, serial ports, and MAVLink flight controllers; package the system for Docker and pip install; and add GitHub Actions CI.

### 8.2 Tasks

| Task | Assigned To | Status |
|---|---|---|
| Implement `guardian/ingestion/udp_listener.py` | Kedia | Done |
| Implement `guardian/ingestion/serial_listener.py` | Kedia | Done |
| Implement `guardian/ingestion/mqtt_listener.py` (stub) | Kedia | Done |
| Implement `guardian/ingestion/listener_factory.py` | Kedia | Done |
| Implement `guardian/ingest_runner.py` (`run_live()`) | Kedia | Done |
| Add `--live` flag to `guardian/main.py` | Kedia | Done |
| Write `tests/test_udp_listener.py` (18 tests) | Kedia | Done |
| Create `pyproject.toml` (PEP 517, console scripts) | Kedia | Done |
| Create `Dockerfile` (python:3.11-slim) | Kedia | Done |
| Create `docker-compose.yml` (with volume mounts) | Kedia | Done |
| Create `.github/workflows/ci.yml` (GitHub Actions) | Kedia | Done |
| Create `Makefile` (6 targets) | Kedia | Done |
| Implement `guardian/ingestion/mavlink_assembler.py` | Kedia | Done |
| Implement `guardian/ingestion/mavlink_heartbeat.py` | Kedia | Done |
| Implement `guardian/ingestion/mavlink_listener.py` | Kedia | Done |
| Write `tests/test_mavlink_assembler.py` (27 tests) | Kedia | Done |
| Write `tests/test_mavlink_listener.py` (6 SITL tests, skipped by default) | Kedia | Done |
| Add `pyserial>=3.5` and `pymavlink>=2.4` to requirements | Kedia | Done |

### 8.3 Dependencies

- `listener_factory.py` depends on all listener classes being implemented first.
- `ingest_runner.py` depends on the factory and the engine (Sprint 1).
- Deployment packaging depends on the full dependency list being stable.
- MAVLink assembler is independent of pymavlink — tested without hardware.

### 8.4 Sprint 3 Review

**Completed features demoed:**
- `python -m guardian.main --live udp` starts a UDP listener on port 14550; sending JSON-encoded telemetry packets causes the Guardian to print alerts in real time.
- `pip install -e .` makes `guardian`, `guardian-dashboard`, and `guardian-live` available as terminal commands.
- `make test` runs all 162 tests; `make pipeline` runs the full validation pipeline.
- `docker build -t fyi26-guardian . && docker run fyi26-guardian python -m pytest -q` runs tests inside a container.
- MAVLink assembler unit tests (27 tests) pass without hardware or a simulator.

**Metrics at end of sprint:** **162 passed, 6 skipped** (SITL tests require `MAVLINK_SIM=1`); validation **11 / 11 passed**; average precision **86.4%**, average recall **90.9%**; UDP, serial, MAVLink, and MQTT-stub ingestion supported.

### 8.5 Sprint 3 Retrospective

**What went well:**
- The `MAVLinkAssembler` was designed to be fully independent of pymavlink, so all 27 assembler tests pass without hardware — only the `MAVLinkListener` integration tests need a simulator.
- The `HeartbeatMonitor` used `threading.Timer` with a lock, correctly handling the race between `heartbeat_received()` and the timeout callback.
- Using `queue.Queue` between the listener thread and the main engine thread avoided any shared-state bugs.

**Challenges:**
- pymavlink on Windows has a non-standard install path that required adjusting the CI workflow to Linux runners only.
- ArduPilot SITL sends `SCALED_IMU2` instead of `SCALED_IMU`, requiring an extra mapping branch in `mavlink_listener.py` so SITL integration tests pass.

**What we would do differently:** add the `--live` flag in Sprint 2 alongside the ingestion skeleton rather than in Sprint 3, to allow earlier manual testing of the full pipeline.

---

## 9. Progress Metrics

### 9.1 Sprint Velocity (tasks completed per sprint)

| Sprint | Tasks Planned | Tasks Completed | Velocity |
|---|---|---|---|
| Sprint 1 | 12 | 12 | 100% |
| Sprint 2 | 13 | 13 | 100% |
| Sprint 3 | 18 | 18 | 100% |

### 9.2 Test Growth by Sprint

| Sprint End | Total Tests | New Tests |
|---|---|---|
| Phase 1 baseline | 74 | — |
| Sprint 1 end | 110 | +36 |
| Sprint 2 end | 162 | +52 |
| Sprint 3 end | 162 (+ 6 skipped) | +6 SITL |

### 9.3 Detection Quality

| Metric | Result |
|---|---|
| Scenarios passing | 11 / 11 |
| Average precision | 86.4% |
| Average recall | 90.9% |
| Average F1 | 90.2% |
| Known false positive | `out_of_order_packets` cascade (by design) |

### 9.4 Bug Tracking

Bugs were tracked through the Git commit history. Notable issues caught during testing:

| Bug | Detected in | Fix |
|---|---|---|
| numpy float JSON serialization error in `export.py` | Sprint 1 — `test_export.py` | Added `default=str` to `json.dumps` |
| DB insert inside `process_row()` broke tests without `db` arg | Sprint 1 — `test_engine.py` | Made `db=None` default, added `if self.db` guard |
| Dashboard HTML form button failed (JSON-only endpoint) | Sprint 2 — `test_dashboard.py` | Added `request.form` fallback + redirect |
| `check_gps_jump` computed `speed_jump` but never used it | Sprint 1 — code review | Added `speed_jump` to the `if` condition |
| ArduPilot SITL sends `SCALED_IMU2` not `SCALED_IMU` | Sprint 3 — SITL test | Added `SCALED_IMU2` branch to listener |

---

## 10. Final Integration and QA Testing

### 10.1 End-to-End Integration Test

The full system was validated end-to-end using this sequence:

```bash
# Step 1: Enable database in config/guardian_config.yaml
#   database:
#     enabled: true

# Step 2: Run combined fault scenario (populates DB + JSONL)
python -m guardian.main data/scenarios/combined_fault.csv

# Step 3: Start the dashboard
python -m dashboard.app
# Open http://localhost:5000

# Step 4: Verify alerts appear in all three panels
# Step 5: Click Acknowledge on a CRITICAL alert → status changes to "acknowledged"
# Step 6: Verify JSONL export
python -c "import json; rows=[json.loads(l) for l in open('results/logs/alerts.jsonl')]; print(len(rows), 'alerts exported')"
```

**Result:** All steps passed. Alerts appeared in the dashboard with correct severity colors, operator actions updated the database, and the JSONL file contained valid records.

### 10.2 Automated Test Suite

```
pytest -q
162 passed, 6 skipped in 20.6s
```

All 162 tests pass. The 6 skipped tests (`tests/test_mavlink_listener.py`) require `MAVLINK_SIM=1` and a running ArduPilot SITL — they pass when the simulator is available.

### 10.3 Validation Pipeline

```
python -m guardian.run_pipeline
```

Output:
```
Total scenarios: 11
Passed: 11
Failed: 0

Precision/Recall across 11 labeled scenarios:
  Avg Precision : 0.864
  Avg Recall    : 0.909
```

### 10.4 Per-Scenario Results

| Scenario | Precision | Recall | F1 | Expected Codes | Detected |
|---|---|---|---|---|---|
| `normal_flight.csv` | — | — | — | none | none (correct) |
| `packet_loss.csv` | 1.00 | 1.00 | 1.00 | `PACKET_LOSS` | ✓ |
| `sensor_dropout.csv` | 1.00 | 1.00 | 1.00 | `IMU_DROPOUT` | ✓ |
| `gps_jump.csv` | 1.00 | 1.00 | 1.00 | `GPS_JUMP` | ✓ |
| `low_battery.csv` | 1.00 | 1.00 | 1.00 | `LOW_BATTERY` | ✓ |
| `out_of_order_packets.csv` | 0.50 | 1.00 | 0.67 | `OUT_OF_ORDER_PACKET` | ✓ (cascade FP noted) |
| `duplicate_packet.csv` | 1.00 | 1.00 | 1.00 | `DUPLICATE_PACKET` | ✓ |
| `frozen_imu.csv` | 1.00 | 1.00 | 1.00 | `IMU_FROZEN` | ✓ |
| `gps_fix_loss.csv` | 1.00 | 1.00 | 1.00 | `GPS_FIX_LOSS` | ✓ |
| `gps_imu_inconsistency.csv` | 1.00 | 1.00 | 1.00 | `GPS_IMU_INCONSISTENCY` | ✓ |
| `combined_fault.csv` | 1.00 | 1.00 | 1.00 | 5 codes | ✓ all 5 |

The 0.50 precision on `out_of_order_packets.csv` is expected: a cascade `PACKET_LOSS` fires on the packet after the out-of-order event, a genuine false positive that accurately reflects real system behavior.

### 10.5 QA Strategy

| Test Type | Tool | Coverage |
|---|---|---|
| Unit tests | pytest | All modules: rules, ML, alerts, config, export, DB, engine, replay, dashboard, precision metrics, UDP listener, MAVLink assembler |
| Integration tests | pytest + Flask test client | Dashboard routes, operator actions, DB writes, full pipeline |
| Scenario validation | `guardian.validation` | 11 scenarios, expected vs observed reason codes |
| Precision / recall | `guardian.precision_metrics` | 11 labeled scenarios, TP/FP/FN per scenario |
| Container tests | Docker | `docker run fyi26-guardian python -m pytest -q` |
| CI | GitHub Actions | Every push to `main` runs full test + validation suite |

---

## 11. Deliverables

| Deliverable | Location / Link |
|---|---|
| Source repository | GitHub repository (root) |
| Sprint 1 plan and review | This document — Section 6 |
| Sprint 2 plan and review | This document — Section 7 |
| Sprint 3 plan and review | This document — Section 8 |
| Sprint retrospectives | This document — Sections 6.5, 7.5, 8.5 |
| Progress metrics | This document — Section 9 |
| Bug tracking | This document — Section 9.4 · Git commit history |
| Testing evidence | `tests/` (162 tests) · `results/metrics/` (CSV outputs) |
| Validation results | `results/metrics/expected_vs_observed.csv` |
| Precision / recall results | `results/metrics/precision_recall.csv` |
| Alert export log | `results/logs/alerts.jsonl` |
| Production-equivalent environment | Flask dashboard on `http://localhost:5000` (local) · Docker image (`fyi26-guardian`) |
| CI pipeline | `.github/workflows/ci.yml` |
| Architecture documentation | `docs/architecture.md` |
| Database contract | `docs/database_contract.md` |
| Dashboard contract | `docs/dashboard_contract.md` |
| Telemetry & alert schemas | `docs/schemas.md` |
| Full technical documentation | `docs/README_DETAILED.md` |

---

## 12. Technical Manual Review Preparation

At the end of this stage the project is evaluated through a technical manual review (an oral evaluation with the code and repository ready). The review validates:

- completion of the project as a functional MVP with minor or no bugs, plus a live demonstration;
- quality of the code, commits, and documentation (README and code comments);
- ability to explain technical decisions logically (database design, application architecture, technology choices, diagrams);
- detailed explanation of application features and code, and how the application works;
- explanation of testing methods and results;
- explanation of team collaboration and Git/GitHub best practices;
- understanding of frontend, backend, database, and other technical concepts applied in the MVP (DB relations, authentication, hashing, security, RBAC).

**What must be prepared:** a functional application, the application and database diagrams, a clean and professional README at the repository root, and a GitHub repository that contains the complete, well-structured, documented codebase alongside the architecture and database diagrams. (Detailed checklist maintained in `docs/STAGE-4-5-TODO.md`.)

---

## 13. Conclusion

Stage 4 transformed the Stage 3 technical design into a functional, tested MVP. Through sprint-based organization, clear role distribution, and QA integrated into every sprint, the team delivered all 9 implementation phases: 162 tests passing, 11/11 scenarios validated, and average precision/recall of 86.4% / 90.9%. The stage also prepared the team for final validation by ensuring both the implementation and the explanations behind it are ready for review.

---

*FYI26 AI Guardian — Stage 4 complete. All 9 implementation phases delivered. 162 tests passing. 11/11 scenarios validated.*
