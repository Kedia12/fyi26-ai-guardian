# FYI26 AI Guardian — Project Overview

A newcomer's guide to what this project is, how data flows through it, and the one concept most worth understanding deeply enough to explain to someone else.

## What the project actually is

FYI26 AI Guardian (built for Airbus's Fly Your Ideas 2026 challenge) is a **human-in-the-loop safety co-pilot for drones/UAVs**. It sits between raw flight telemetry (MAVLink from ArduPilot/PX4/Pixhawk/SITL) and a human ground operator, watching for anomalies and surfacing explainable alerts on a live dashboard. It deliberately does **not** autonomously control the aircraft — it informs a human who acknowledges/escalates/resolves alerts.

## The data flow

1. **Ingestion** — listeners (MAVLink/serial/UDP/MQTT/CSV replay) normalize incoming data into a standard telemetry row. The tricky part: MAVLink spreads one aircraft's state across multiple message types arriving at different rates, so an "assembler" has to stitch partial updates into one coherent row before it's usable.
2. **Engine** (`guardian/engine.py`) — runs every row through detection logic, producing alerts.
3. **Persistence** — telemetry + alerts go into SQLite (`GuardianDB`) and a JSONL export log.
4. **Dashboard** — Flask + React/TSX frontend polls the DB for live telemetry, alerts, and an aircraft map.
5. **Reporting** — after a flight, an LLM (Claude) turns the alert history into a plain-language post-flight safety report.

## The single most important thing to understand

**There are three distinct layers of "intelligence," and the differentiator is the predictive layer, not the plumbing:**

1. **Rule engine** — 10 deterministic threshold checks (packet loss, battery low, GPS fix loss, geofence breach, etc.). This is reactive: it fires *after* a bad condition exists.
2. **ML anomaly scoring** — an Isolation Forest flags statistically unusual telemetry combinations no single rule covers. The project's own docs admit this is a secondary/minimally-tuned layer.
3. **Predictive forecasting** — *this is the genuinely novel part.* A rolling window of recent readings feeds a lightweight linear regression on things like battery voltage trend and gyro drift, producing alerts like `PREDICTED_LOW_BATTERY` **before** the reactive threshold would ever fire. This is what turns the system from "alarm when something's already wrong" into "warn before it goes wrong" — the actual value proposition of a "guardian."

If you can only explain one thing to someone else, explain **why prediction is different from detection**, and point to `predictor.py`'s rolling-window regression as the concrete mechanism.

## Supporting concepts worth knowing

- **MAVLink** — the telemetry protocol, and why message reassembly is nontrivial.
- **Alert schema** — severity (WARNING/CRITICAL) + confidence score + status (active/acknowledged/escalated/resolved) — this state machine is the human-in-the-loop workflow.
- **Geofencing** — polygon breach detection via ray-casting, shown on the Leaflet map.
- **Validation harness** — labeled fault-scenario CSVs measuring precision/recall (~86%/~91% per the README) — the detection quality is measured, not just assumed, which is unusually rigorous for a prototype.

## Layer reference

| Layer | File | Nature | Example alert |
|---|---|---|---|
| Rule engine | `guardian/rules.py` | Reactive, deterministic | `GPS_FIX_LOST`, `GEOFENCE_BREACH` |
| ML anomaly scoring | `guardian/ml_model.py` | Reactive, statistical (Isolation Forest) | `ML_ANOMALY` |
| Predictive forecasting | `guardian/predictor.py` | Anticipatory, rolling-window regression | `PREDICTED_LOW_BATTERY`, `PREDICTED_IMU_DRIFT` |
| Post-flight reporting | `guardian/report_generator.py` | LLM-generated summary | Markdown safety report with Safe/Caution/Unsafe verdict |
