# How To Run — AI Guardian

AI Guardian is a drone telemetry anomaly-detection system. It reads flight data (CSV replay or live UDP/serial stream), applies rule-based checks and a machine-learning Isolation Forest, and emits alerts for anomalies such as GPS jumps, packet loss, low battery, or frozen IMU sensors.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup (first time)](#setup-first-time)
3. [Configuration](#configuration)
4. [Running a scenario (CSV replay)](#running-a-scenario-csv-replay-mode)
5. [Dashboard (web UI)](#dashboard-web-ui)
6. [Live ingestion modes](#live-ingestion-modes)
7. [Compatible aircraft apps](#compatible-aircraft-apps)
8. [Full pipeline](#full-pipeline-metrics--validation--tests--summary)
9. [Tests](#tests)
10. [Docker](#docker-containerised-full-stack)
11. [Output files](#output-files)
12. [Makefile shortcuts](#makefile-shortcuts)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11 or newer
- `pip` available on your PATH
- Docker Desktop (optional — only needed for the containerised stack)

---

## Setup (first time)

### 1. Create and activate a virtual environment

**Windows — PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows — Git Bash / WSL:**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

> A legacy `.vm/` directory may be present in the repo root. The commands above create a fresh `.venv`; use whichever you prefer.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or install the project as an **editable package** (registers the `guardian` console script so you can type `guardian` instead of `python -m guardian.main` anywhere):

```bash
pip install -e .
```

---

## Configuration

All tuneable thresholds, feature flags, and paths live in [config/guardian_config.yaml](config/guardian_config.yaml). Edit that file to change behaviour without touching any Python code.

Key settings explained:

| Setting | Default | What it controls |
|---|---|---|
| `rules.packet_loss_gap_ms` | `200` | Timestamp gap (ms) that triggers a PACKET_LOSS alert |
| `rules.battery_warning_v` | `10.5` | Voltage below which a WARNING is raised |
| `rules.battery_critical_v` | `10.2` | Voltage below which a CRITICAL alert is raised |
| `rules.gps_jump_threshold_deg` | `0.001` | Max lat/lon change (°) between packets before GPS_JUMP fires |
| `rules.min_satellites` | `4` | Fewer satellites triggers GPS_FIX_LOSS |
| `ml.contamination` | `0.05` | Fraction of rows assumed anomalous when training the Isolation Forest |
| `ml.alert_threshold` | `0.1` | Anomaly score above this value generates an ML_ANOMALY alert |
| `database.enabled` | `true` | Write telemetry rows and alerts to SQLite (required for the dashboard) |
| `database.path` | `results/guardian.db` | SQLite file location |
| `logging.json_export_enabled` | `true` | Append every alert to a `.jsonl` log file |
| `logging.json_export_path` | `results/logs/alerts.jsonl` | Alert log location |
| `ingestion.mode` | `replay` | Active data source: `replay`, `udp`, `serial`, or `mavlink` |
| `ingestion.udp_host` | `0.0.0.0` | Host to bind for UDP / MAVLink live modes |
| `ingestion.udp_port` | `14550` | UDP port for live modes |
| `ingestion.serial_port` | `/dev/ttyUSB0` | Serial device path for `serial` / `mavlink` modes |
| `ingestion.serial_baud` | `57600` | Baud rate for the serial connection |

---

## Running a scenario (CSV replay mode)

```bash
python -m guardian.main
```

**What this does:** Loads the default CSV scenario (`data/scenarios/low_battery.csv`), feeds each row through the rule engine and the ML model one at a time (simulating a live stream), and prints every packet and any alerts to the terminal. When finished it prints a replay summary (total packets processed and total alerts raised). If `database.enabled: true`, every packet and alert is also written to SQLite for later use by the dashboard.

**Run a specific scenario:**
```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

**Available scenarios and what they test:**

| Scenario file | What it injects |
|---|---|
| `normal_flight.csv` | Clean baseline — should produce zero alerts |
| `packet_loss.csv` | Large timestamp gaps between packets |
| `sensor_dropout.csv` | Missing / null sensor readings |
| `gps_jump.csv` | Sudden large position change |
| `low_battery.csv` | Voltage dropping below warning and critical thresholds |
| `out_of_order_packets.csv` | Packets arriving with non-monotonic sequence numbers |
| `duplicate_packet.csv` | Repeated packet IDs |
| `frozen_imu.csv` | IMU values stuck at constant readings |
| `gps_fix_loss.csv` | Satellite count dropping below `min_satellites` |
| `combined_fault.csv` | Multiple fault types injected simultaneously |

**Example terminal output:**
```
════════════ AI GUARDIAN ════════════
packet=1  ml_anomaly_score=0.0312
packet=2  ml_anomaly_score=0.0289
packet=3  ml_anomaly_score=0.1521  [ALERT] LOW_BATTERY  severity=WARNING  voltage=10.48
...
Processed 120 packets | 4 alerts raised
Alerts exported to: results/logs/alerts.jsonl
```

---

## Dashboard (web UI)

The dashboard visualises telemetry and alerts stored in the SQLite database. It ships with a **React 18 + TypeScript** frontend (Header, TelemetryPanel, ActiveAlerts, AlertHistory, AircraftMap). Flask serves the compiled React build automatically when it exists; otherwise it falls back to the Jinja2 template.

**Step 1 — Ensure the database is enabled** in [config/guardian_config.yaml](config/guardian_config.yaml):
```yaml
database:
  enabled: true
```

**Step 2 — Populate the database** by running any scenario:
```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

**Step 3 (optional) — Build the React UI:**
```bash
cd dashboard/ui
npm install
npm run build
cd ../..
```

This produces `dashboard/ui/dist/`. Flask will serve it automatically on the next start. Skip this step to use the Jinja2 fallback instead.

**Step 4 — Start the dashboard server:**

```bash
python -m dashboard.app
# or via Makefile:
make dashboard
```

**What this does:** Starts a Flask web server on port 5000. The dashboard reads from `results/guardian.db` and displays live telemetry, active alerts, alert history, and an aircraft map.

Open your browser at: **http://localhost:5000**

---

## Live ingestion modes

Instead of replaying a CSV, Guardian can process a real-time data stream.

### UDP

```bash
python -m guardian.main --live udp
```

**What this does:** Binds a UDP socket on `0.0.0.0:14550` (configurable via `ingestion.udp_host` and `ingestion.udp_port`) and processes incoming telemetry packets in real time. Every packet is run through the same rule + ML pipeline as replay mode and alerts are printed immediately. Press **Ctrl+C** to stop.

### Serial port (direct hardware connection)

Set `ingestion.serial_port` and `ingestion.serial_baud` in the config, then:
```bash
python -m guardian.main --live serial
```

### MAVLink over UDP

```bash
python -m guardian.main --live mavlink
```

**What this does:** Same as UDP mode but decodes the incoming bytes as MAVLink frames and assembles them into telemetry rows before feeding them to the engine. Requires `pymavlink` (included in `requirements.txt`).

You can also invoke the live runner directly (equivalent):
```bash
python -m guardian.ingest_runner
```

---

## Compatible aircraft apps

Guardian speaks MAVLink — the protocol used by ArduPilot, PX4, and all major ground control stations. The steps below show how to connect each app to Guardian's live MAVLink mode.

**Guardian config for all MAVLink connections:**
```yaml
ingestion:
  mode: mavlink
  udp_host: 0.0.0.0
  udp_port: 14550
```

Then start Guardian:
```bash
python -m guardian.main --live mavlink
```

---

### QGroundControl (QGC)

**Platform:** Windows, macOS, Linux, Android, iOS

QGC streams MAVLink over UDP by default on port 14550 — the same port Guardian listens on.

| Step | Action |
|---|---|
| 1 | Open QGC → **Application Settings → Comm Links → Add** |
| 2 | Type: `UDP`, Port: `14550`, Target host: your Guardian machine IP |
| 3 | Click **Connect** |
| 4 | Guardian receives `HEARTBEAT`, `SCALED_IMU`, `GPS_RAW_INT`, `SYS_STATUS`, and `VFR_HUD` messages and begins emitting assembled rows |

---

### Mission Planner (ArduPilot)

**Platform:** Windows only

Mission Planner connects to a flight controller and can forward MAVLink to Guardian via a UDP output.

| Step | Action |
|---|---|
| 1 | Connect Mission Planner to your flight controller (USB or telemetry radio) |
| 2 | Go to **Config → Planner → Output** and add a UDP output to `127.0.0.1:14550` |
| 3 | Guardian receives the forwarded MAVLink stream on port 14550 |

---

### MAVProxy (command-line bridge)

**Install:** `pip install MAVProxy`

MAVProxy fans out one MAVLink source to multiple consumers simultaneously (e.g. both a GCS and Guardian at the same time).

```bash
# Bridge SITL TCP output to Guardian UDP + QGC UDP
mavproxy.py --master tcp:127.0.0.1:5760 \
            --out udp:127.0.0.1:14550 \
            --out udp:127.0.0.1:14551
```

Guardian listens on port `14550` and QGC on `14551`.

---

### ArduPilot SITL (software simulator — no hardware needed)

SITL lets you test Guardian against a fully simulated aircraft.

```bash
# Terminal 1 — start ArduPlane SITL
sim_vehicle.py -v ArduPlane --console --map

# Terminal 2 — bridge SITL to Guardian's port
mavproxy.py --master tcp:127.0.0.1:5760 --out udp:127.0.0.1:14550

# Terminal 3 — start Guardian in MAVLink mode
python -m guardian.main --live mavlink

# Terminal 4 — run MAVLink integration tests against the live simulator
# PowerShell:
$env:MAVLINK_SIM = "1"
pytest tests/test_mavlink_listener.py -v
# Bash / WSL:
MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v
```

---

### PX4 Autopilot

PX4 outputs standard MAVLink on UDP port 14550 by default. Guardian connects directly.

```bash
# Start PX4 SITL (Gazebo)
make px4_sitl gazebo

# Guardian connects directly — no bridge needed
python -m guardian.main --live mavlink
```

---

### Direct serial (Pixhawk / flight controller via USB)

Update the config for a physical board:

```yaml
ingestion:
  mode: mavlink
  serial_port: COM3          # Windows — check Device Manager for your port
  serial_baud: 57600
  # serial_port: /dev/ttyUSB0  # Linux / macOS
```

Then run:
```bash
python -m guardian.main --live mavlink
```

Guardian waits for a MAVLink heartbeat, then begins assembling telemetry rows from the incoming message stream.

---

### Connection summary

| Source | Protocol | Guardian port | Config |
|---|---|---|---|
| QGroundControl | UDP MAVLink | 14550 | `udp_host: 0.0.0.0`, `udp_port: 14550` |
| Mission Planner | UDP MAVLink | 14550 | `udp_host: 0.0.0.0`, `udp_port: 14550` |
| MAVProxy bridge | UDP MAVLink | 14550 | `udp_host: 0.0.0.0`, `udp_port: 14550` |
| ArduPilot SITL (via MAVProxy) | UDP MAVLink | 14550 | `udp_host: 0.0.0.0`, `udp_port: 14550` |
| PX4 SITL (Gazebo) | UDP MAVLink | 14550 | `udp_host: 0.0.0.0`, `udp_port: 14550` |
| Pixhawk USB (Windows) | Serial MAVLink | COM3 | `serial_port: COM3`, `serial_baud: 57600` |
| Pixhawk USB (Linux) | Serial MAVLink | ttyUSB0 | `serial_port: /dev/ttyUSB0`, `serial_baud: 57600` |

---

## Full pipeline (metrics → validation → tests → summary)

```bash
python -m guardian.run_pipeline
# or via Makefile:
make pipeline
```

**What this does — step by step:**

1. **Generate scenario metrics** — runs every scenario CSV and writes per-scenario precision/recall numbers to `results/metrics/precision_recall.csv`.
2. **Generate expected-vs-observed validation** — compares the alerts Guardian actually raised against ground-truth label files in `data/labels/` and writes `results/metrics/expected_vs_observed.csv`.
3. **Run the test suite** (`pytest -q`) — executes all unit and integration tests.
4. **Print a final summary** — shows validation pass/fail counts and average precision/recall across all scenarios.

Run this before committing to confirm the full system is healthy.

---

## Tests

```bash
python -m pytest -q
# or via Makefile:
make test
```

**What this does:** Discovers and runs all test files under `tests/`. The `-q` flag shows only failures and the final count. Tests cover the rules engine, ML model, database, dashboard routes, UDP listener, MAVLink assembler, and ingestion listeners.

Run a single test file:
```bash
python -m pytest tests/test_rules.py -v
```

---

## Docker (containerised full stack)

### Build and start with docker-compose

```bash
docker-compose up --build
```

**What this does:** Builds an image from [Dockerfile](Dockerfile) (Python 3.11-slim, installs `requirements.txt`, copies the project), then starts a container running `python -m dashboard.app`. Dashboard is at **http://localhost:5000**. The `data/`, `results/`, and `config/` directories are bind-mounted so the container reads your local files and writes results back to your filesystem.

### Run a scenario inside the container

```bash
docker-compose run guardian python -m guardian.main data/scenarios/combined_fault.csv
```

### Build and run manually (without docker-compose)

```bash
# Build the image
docker build -t fyi26-guardian .
# or: make docker-build

# Run the dashboard
# Bash / WSL:
docker run -p 5000:5000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/results:/app/results" \
  -v "$(pwd)/config:/app/config" \
  fyi26-guardian

# PowerShell:
docker run -p 5000:5000 `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/results:/app/results" `
  -v "${PWD}/config:/app/config" `
  fyi26-guardian

# or: make docker-run

# Run a specific scenario inside the container
docker run --rm `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/results:/app/results" `
  -v "${PWD}/config:/app/config" `
  fyi26-guardian python -m guardian.main data/scenarios/low_battery.csv
```

---

## Output files

After running, Guardian writes results to the `results/` directory:

| Path | Contents |
|---|---|
| `results/guardian.db` | SQLite database with all telemetry rows and alerts (requires `database.enabled: true`) |
| `results/logs/alerts.jsonl` | Newline-delimited JSON; one entry per alert (requires `logging.json_export_enabled: true`) |
| `results/post_flight_report.md` | Plain-language AI report generated by `guardian-report` |
| `results/metrics/precision_recall.csv` | Per-scenario precision and recall (written by `make pipeline`) |
| `results/metrics/expected_vs_observed.csv` | Pass/fail comparison against ground-truth labels (written by `make pipeline`) |

---

## Post-Flight AI Report

After a flight session, generate a plain-language summary of all recorded alerts using Claude AI:

```bash
# Set your Anthropic API key first
export ANTHROPIC_API_KEY=sk-ant-...   # macOS / Linux / Git Bash
$env:ANTHROPIC_API_KEY="sk-ant-..."   # Windows PowerShell

# Generate the report (reads results/logs/alerts.jsonl)
python -m guardian.report_generator
# or, after pip install -e .
guardian-report
```

The report is saved to `results/post_flight_report.md` and can also be triggered from the dashboard's **"Generate Report"** button at the bottom of the page.

---

## Makefile shortcuts

```bash
make install       # pip install -e .  (editable install + registers 'guardian' command)
make test          # python -m pytest -q
make pipeline      # metrics → validation → tests → summary
make dashboard     # python -m dashboard.app  (Flask on port 5000)
make docker-build  # docker build -t fyi26-guardian .
make docker-run    # docker run with data/results/config volumes bound
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'guardian'`**
Your virtual environment is not activated or you haven't installed the package yet.
```bash
# Activate (PowerShell)
.venv\Scripts\Activate.ps1
# Then install
pip install -e .
```

**`OSError: [Errno 98] Address already in use` (port 14550)**
Another process is already listening on the UDP port. Change `ingestion.udp_port` in the config or stop the conflicting process:
```bash
# Windows — find the process using port 14550
netstat -ano | findstr :14550
# Linux / macOS
lsof -i :14550
```

**Dashboard shows no data**
The database must be populated before starting the dashboard. Run a scenario first:
```bash
python -m guardian.main data/scenarios/combined_fault.csv
python -m dashboard.app
```
Also confirm `database.enabled: true` in [config/guardian_config.yaml](config/guardian_config.yaml).

**`database` or `results/` directory not found**
Guardian creates these automatically on first run. If they are missing, run any scenario once and they will be created.

**Docker: `$(pwd)` not recognised in PowerShell**
Use `${PWD}` (PowerShell variable) instead of `$(pwd)` (bash substitution). See the [Docker section](#docker-containerised-full-stack) above for the PowerShell-specific commands.

**MAVLink mode receives no packets**
- Confirm the flight controller or simulator is outputting MAVLink on the port specified in `ingestion.udp_port`.
- Check that your firewall is not blocking UDP on that port.
- Use MAVProxy to verify the stream is active before connecting Guardian.
