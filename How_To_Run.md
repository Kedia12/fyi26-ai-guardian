# How To Run — AI Guardian

AI Guardian is a drone telemetry anomaly-detection system. It reads flight data (CSV replay or live UDP/serial stream), applies rule-based checks and a machine-learning Isolation Forest, and emits alerts for anomalies such as GPS jumps, packet loss, low battery, or frozen IMU sensors.

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

> A legacy `.vm/` virtual environment may also be present in the repo root. The commands above create a fresh one; use whichever you prefer.

### 2. Install dependencies

```bash
# Install runtime + dev dependencies
pip install -r requirements.txt
```

Or install the project as an **editable package** (registers the `guardian` console script on your PATH):

```bash
pip install -e .
```

With the editable install you can run `guardian` instead of `python -m guardian.main` anywhere.

---

## Configuration

All tuneable thresholds, feature flags, and paths live in [config/guardian_config.yaml](config/guardian_config.yaml). You never need to touch Python code to change behaviour.

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
| `ingestion.udp_port` | `14550` | UDP port for live modes |
| `ingestion.serial_port` | `/dev/ttyUSB0` | Serial device for `serial` / `mavlink` modes |

---

## Running a scenario (CSV replay mode)

```bash
python -m guardian.main
```

**What this does:** Loads the default CSV scenario (`data/scenarios/low_battery.csv`), feeds each row through the rule engine and the ML model one at a time (simulating a live stream), and prints alerts to the terminal. When finished it prints a summary of total packets processed and total alerts raised. If `database.enabled: true` in the config, every packet and alert is also written to SQLite.

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
| `combined_fault.csv` | Multiple fault types injected at once |

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

The dashboard visualises telemetry and alerts stored in the SQLite database.

**Step 1 — Ensure the database is enabled** in [config/guardian_config.yaml](config/guardian_config.yaml):
```yaml
database:
  enabled: true
```

**Step 2 — Populate the database** by running a scenario:
```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

**Step 3 — Start the dashboard server:**
```bash
python -m dashboard.app
# or via Makefile:
make dashboard
```

**What this does:** Starts a Flask web server on `http://localhost:5000`. The dashboard reads from `results/guardian.db` and displays a table of recent alerts, per-scenario packet counts, and anomaly score trends.

Open your browser and go to: **http://localhost:5000**

---

## Live ingestion modes

Instead of replaying a CSV, Guardian can process a real-time data stream.

### UDP (e.g. from a flight controller or simulator)

```bash
python -m guardian.main --live udp
```

**What this does:** Binds a UDP socket on `0.0.0.0:14550` (configurable via `ingestion.udp_port`) and processes incoming telemetry packets in real time. Every packet is run through the same rule + ML pipeline as in replay mode and alerts are printed immediately.

### Serial port (direct hardware connection)

Set `ingestion.serial_port` and `ingestion.serial_baud` in the config, then:
```bash
python -m guardian.main --live serial
```

### MAVLink over UDP

```bash
python -m guardian.main --live mavlink
```

**What this does:** Same as UDP mode but parses the incoming bytes as MAVLink frames before feeding them to the engine. Requires `pymavlink` (included in `requirements.txt`).

---

## Full pipeline (metrics → validation → tests → summary)

```bash
python -m guardian.run_pipeline
# or via Makefile:
make pipeline
```

**What this does — step by step:**

1. **Generate scenario metrics** (`guardian.metrics`) — runs every scenario CSV and writes per-scenario precision/recall numbers to `results/metrics/precision_recall.csv`.
2. **Generate expected-vs-observed validation** (`guardian.validation`) — compares the alerts Guardian actually raised against the ground-truth label files in `data/labels/` and writes `results/metrics/expected_vs_observed.csv`.
3. **Run the test suite** (`pytest -q`) — executes all unit and integration tests.
4. **Print a final summary** — shows validation pass/fail counts and average precision/recall across all scenarios.

Use this command before committing to confirm the full system is healthy.

---

## Tests

```bash
python -m pytest -q
# or via Makefile:
make test
```

**What this does:** Discovers and runs all test files under `tests/`. The `-q` flag suppresses verbose per-test output and shows only failures and the final count. Tests cover individual components (rules engine, ML model, database contract, dashboard routes, ingestion listeners).

---

## Docker (containerised full stack)

### Build and start with docker-compose

```bash
docker-compose up --build
```

**What this does:** Builds a Docker image from [Dockerfile](Dockerfile) (Python 3.11-slim base, installs `requirements.txt`, copies the project), then starts a container that runs `python -m dashboard.app`. The dashboard is accessible at **http://localhost:5000**. The `data/`, `results/`, and `config/` directories are bind-mounted so the container reads your local scenario files and writes results back to your filesystem.

### Override the container command to run a scenario instead

```bash
docker-compose run guardian python -m guardian.main data/scenarios/combined_fault.csv
```

### Build and run manually (without docker-compose)

```bash
# Build the image
docker build -t fyi26-guardian .
# or via Makefile:
make docker-build

# Run it (dashboard)
docker run -p 5000:5000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/results:/app/results" \
  -v "$(pwd)/config:/app/config" \
  fyi26-guardian
# or via Makefile:
make docker-run

# Run a specific scenario in the container
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/results:/app/results" \
  -v "$(pwd)/config:/app/config" \
  fyi26-guardian python -m guardian.main data/scenarios/low_battery.csv
```

---

## Output files

After running, Guardian writes results to the `results/` directory:

| Path | Contents |
|---|---|
| `results/guardian.db` | SQLite database with all telemetry rows and alerts (when `database.enabled: true`) |
| `results/logs/alerts.jsonl` | Newline-delimited JSON log; one entry per alert (when `logging.json_export_enabled: true`) |
| `results/metrics/precision_recall.csv` | Per-scenario precision and recall (written by `make pipeline`) |
| `results/metrics/expected_vs_observed.csv` | Pass/fail comparison against ground-truth labels (written by `make pipeline`) |

---

## Makefile shortcuts

```bash
make install     # pip install -e .  (editable install + console scripts)
make test        # python -m pytest -q
make pipeline    # metrics → validation → tests → summary
make dashboard   # python -m dashboard.app  (start Flask on port 5000)
make docker-build  # docker build -t fyi26-guardian .
make docker-run    # docker run with data/results/config volumes bound
```
