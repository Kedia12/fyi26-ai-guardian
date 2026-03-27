# FYI26 AI Guardian

This project is a prototype for the Airbus Fly Your Ideas 2026 challenge.

## Goal
Build a Human-in-the-Loop AI Guardian for connected aerospace systems.

The Guardian:
- receives telemetry from an RC aircraft testbed or replayed scenario files
- checks data integrity and physical consistency
- detects suspicious anomalies
- generates alerts with severity, confidence, reason code, and recommended action
- supports human decisions through a web dashboard workflow

## Problem statement
Connected aerospace systems rely on continuous data exchange between sensors, onboard systems, operators, and connected infrastructure. This improves efficiency and awareness, but also increases vulnerability to bad data, missing transmissions, spoofed navigation inputs, sensor failures, and other anomalies that can affect decision-making and safety.

## Core idea
The project proposes a Human-in-the-Loop AI Guardian: a lightweight monitoring and decision-support layer that combines:
- deterministic integrity and physical-consistency checks
- lightweight anomaly detection with Isolation Forest
- explainable alert generation
- operator-oriented safe response guidance

The objective is not only to detect anomalies, but to turn them into explainable and auditable decisions that a human operator can trust and validate.

## Current prototype scope
The current prototype is focused on:
- replaying telemetry scenarios from CSV files
- applying rule-based anomaly checks
- scoring telemetry with a lightweight ML anomaly model
- generating structured alerts
- validating core logic through automated tests

In later phases, the same architecture is intended to connect to a real RC aircraft telemetry node with onboard sensors.

## Implemented features
- rule-based anomaly detection for:
  - packet loss
  - out-of-order packets
  - duplicate packets
  - IMU dropout
  - frozen IMU
  - low battery
  - GPS fix loss
  - GPS jump
  - GPS / IMU inconsistency
- ML anomaly scoring using Isolation Forest
- scenario replay from CSV
- telemetry and alert schema validation helpers
- command-line runner
- automated unit tests

## Project structure
- `docs/` → architecture and schemas
- `data/scenarios/` → replayable telemetry CSV files
- `guardian/` → Guardian Python code
- `tests/` → automated tests

## Scenario files
Current replay scenarios include:
- `normal_flight.csv`
- `packet_loss.csv`
- `sensor_dropout.csv`
- `gps_jump.csv`
- `low_battery.csv`
- `out_of_order_packets.csv`
- `duplicate_packet.csv`
- `frozen_imu.csv`
- `gps_fix_loss.csv`
- `combined_fault.csv`

## Tech stack
- Python
- pandas
- scikit-learn
- pytest
- CSV-based scenario replay
- planned RC aircraft telemetry integration

## How to run
Run the default scenario:

```bash
python -m guardian.main