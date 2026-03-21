# FYI26 AI Guardian

This project is a prototype for the Airbus Fly Your Ideas 2026 challenge.

## Goal
Build a Human-in-the-Loop AI Guardian for connected aerospace systems.

The Guardian:
- receives telemetry from an RC aircraft testbed
- checks data integrity and physical consistency
- detects suspicious anomalies
- generates alerts with severity, confidence, reason code, and recommended action
- supports human decisions through a web dashboard

## Project structure
- `docs/` → architecture and schemas
- `data/scenarios/` → fake telemetry CSV files
- `guardian/` → Guardian Python code
- `tests/` → tests