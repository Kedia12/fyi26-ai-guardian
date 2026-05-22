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
- exploring both isolated and combined anomaly scenarios

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
```

Run a specific scenario:

```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

Start live UDP ingestion (listens on port 14550):

```bash
python -m guardian.main --live udp
```

## Installation

Install as an editable package (recommended for development):

```bash
pip install -e .
```

This registers three console scripts:

| Command             | Action                                      |
|---------------------|---------------------------------------------|
| `guardian`          | Replay a CSV scenario or start live mode    |
| `guardian-dashboard`| Start the Flask web dashboard               |
| `guardian-live`     | Start live UDP/serial ingestion directly    |

Install all runtime + dev dependencies at once:

```bash
pip install -r requirements.txt
```

## Dashboard

Enable the database in `config/guardian_config.yaml`:

```yaml
database:
  enabled: true
  path: results/guardian.db
```

Populate it by replaying a scenario, then start the dashboard:

```bash
python -m guardian.main data/scenarios/combined_fault.csv
python -m dashboard.app          # open http://localhost:5000
```

## Docker

Build and run the full stack with Docker Compose:

```bash
docker-compose up --build
```

Open `http://localhost:5000` for the dashboard.

Or build and run the image manually:

```bash
docker build -t fyi26-guardian .
docker run -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/config:/app/config \
  fyi26-guardian
```

Override the default command to run tests inside the container:

```bash
docker run fyi26-guardian python -m pytest -q
```

## CI

The project uses GitHub Actions for continuous integration (`.github/workflows/ci.yml`).

On every push and pull request to `main`:
1. Install dependencies from `requirements.txt`
2. Run the full test suite with `pytest -q`
3. Generate scenario metrics (`guardian.metrics`)
4. Run expected-vs-observed validation (`guardian.validation`)

## Makefile shortcuts

```bash
make test          # run pytest
make pipeline      # full pipeline: metrics → validation → tests → summary
make dashboard     # start Flask dashboard
make docker-build  # build Docker image
make docker-run    # run container with data/results/config mounts
make install       # pip install -e .
```
