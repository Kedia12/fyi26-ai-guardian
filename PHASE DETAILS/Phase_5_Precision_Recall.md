# Phase 5 — Precision, Recall & Detection Latency Metrics
**Fixes Gap 7: No false-positive / false-negative metrics — no way to measure detection quality**

---

## Why This Matters

Right now the validation pipeline only checks whether expected reason codes appear in the output. That answers "did the rule fire?" but not "how often did it fire falsely?" or "how quickly did it fire?". For a competition submission — especially one claiming Human-in-the-Loop safety — you need real ML evaluation metrics:

- **Precision** = of all the alerts we raised, what fraction were on rows that actually had a fault?
- **Recall** = of all the rows that actually had a fault, what fraction did we alert on?
- **F1** = harmonic mean of precision and recall (the single most useful summary number)
- **Detection latency** = how many milliseconds elapsed between the first anomalous row and the first alert on it?

This phase creates ground-truth label files for all 11 scenarios and computes these metrics automatically.

---

## Prerequisites

- Phase 1 (config) must be complete
- Phase 4 (ML alerts) must be complete — so ML_ANOMALY appears in observed alerts and is included in metrics

---

## Files You Will Create

```
data/labels/normal_flight_labels.csv
data/labels/packet_loss_labels.csv
data/labels/sensor_dropout_labels.csv
data/labels/gps_jump_labels.csv
data/labels/low_battery_labels.csv
data/labels/out_of_order_packets_labels.csv
data/labels/duplicate_packet_labels.csv
data/labels/frozen_imu_labels.csv
data/labels/gps_fix_loss_labels.csv
data/labels/gps_imu_inconsistency_labels.csv
data/labels/combined_fault_labels.csv

guardian/precision_metrics.py
tests/test_precision_metrics.py
```

## Files You Will Modify

```
guardian/metrics.py              ← call generate_precision_recall_csv() at the end
guardian/run_pipeline.py         ← print precision/recall totals in final summary
```

---

## Step 1 — Create the `data/labels/` directory

```bash
mkdir data/labels
```

---

## Step 2 — Create the 11 Label CSV Files

Each label file has exactly two columns: `packet_id` and `expected_alert`.
- `0` means the row is normal (no fault expected)
- `1` means the row has a fault (an alert should be raised)

You must open each scenario CSV in `data/scenarios/` and look at which `packet_id` values correspond to anomalous rows. The label files below reflect what each scenario is designed to test.

**`data/labels/normal_flight_labels.csv`** — All rows are normal. No faults.

This file will have `0` for every packet_id in `normal_flight.csv`. If your normal_flight.csv has packets 1–50, create one row per packet_id, all with `expected_alert=0`.

Example format (adapt packet_ids to match your actual CSV):
```csv
packet_id,expected_alert
1,0
2,0
3,0
```

**`data/labels/packet_loss_labels.csv`** — The row immediately after the gap is the anomalous one. Label the packet_id of the row that follows the sequence gap with `1`, all others `0`.

```csv
packet_id,expected_alert
```
_(Fill with 0s except the packet_id immediately after the gap — set that to 1)_

**`data/labels/sensor_dropout_labels.csv`** — Rows where all IMU values are 0.0 are anomalous. Label those packet_ids with `1`.

**`data/labels/gps_jump_labels.csv`** — The row where GPS coordinates make an abrupt jump. Label that packet_id with `1`.

**`data/labels/low_battery_labels.csv`** — Rows where `battery_voltage_v < 10.5`. Label those packet_ids with `1`.

**`data/labels/out_of_order_packets_labels.csv`** — The packet whose `packet_id` is less than the previous packet's `packet_id`. Label that row with `1`.

**`data/labels/duplicate_packet_labels.csv`** — The second occurrence of a repeated `packet_id`. Label that row with `1`.

**`data/labels/frozen_imu_labels.csv`** — The row(s) where IMU values are identical to the previous row. Label those rows with `1`.

**`data/labels/gps_fix_loss_labels.csv`** — Rows where `gps_fix_status=0`. Label those with `1`.

**`data/labels/gps_imu_inconsistency_labels.csv`** — The row where GPS changes significantly without corresponding IMU motion. Label with `1`.

**`data/labels/combined_fault_labels.csv`** — Label every row that has any fault with `1`. In combined_fault.csv, this will be most rows.

### How to generate label files automatically

Instead of editing each file by hand, you can run this helper script once to generate label files based on the actual CSV content. Save it as `scripts/generate_labels.py` and run it once:

```python
"""One-time script to generate ground-truth label files from scenario CSVs.
Run from project root: python scripts/generate_labels.py
"""
import csv
from pathlib import Path

SCENARIOS_DIR = Path("data/scenarios")
LABELS_DIR = Path("data/labels")
LABELS_DIR.mkdir(exist_ok=True)


def read_scenario(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_labels(name, rows, anomalous_packet_ids):
    out = LABELS_DIR / f"{name}_labels.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["packet_id", "expected_alert"])
        for row in rows:
            pid = int(row["packet_id"])
            label = 1 if pid in anomalous_packet_ids else 0
            writer.writerow([pid, label])
    print(f"Written: {out}")


# --- normal_flight: all normal ---
rows = read_scenario(SCENARIOS_DIR / "normal_flight.csv")
write_labels("normal_flight", rows, set())

# --- packet_loss: find rows after sequence gaps ---
rows = read_scenario(SCENARIOS_DIR / "packet_loss.csv")
anomalous = set()
for i in range(1, len(rows)):
    prev_id = int(rows[i-1]["packet_id"])
    curr_id = int(rows[i]["packet_id"])
    if curr_id - prev_id > 1:
        anomalous.add(curr_id)
write_labels("packet_loss", rows, anomalous)

# --- sensor_dropout: rows where all IMU values are exactly 0 ---
rows = read_scenario(SCENARIOS_DIR / "sensor_dropout.csv")
imu_fields = ["accel_x_g","accel_y_g","accel_z_g","gyro_x_dps","gyro_y_dps","gyro_z_dps"]
anomalous = {int(r["packet_id"]) for r in rows if all(float(r[f])==0.0 for f in imu_fields)}
write_labels("sensor_dropout", rows, anomalous)

# --- gps_jump: rows with abrupt GPS changes ---
rows = read_scenario(SCENARIOS_DIR / "gps_jump.csv")
anomalous = set()
for i in range(1, len(rows)):
    dlat = abs(float(rows[i]["gps_lat_deg"]) - float(rows[i-1]["gps_lat_deg"]))
    dlon = abs(float(rows[i]["gps_lon_deg"]) - float(rows[i-1]["gps_lon_deg"]))
    if dlat > 0.001 or dlon > 0.001:
        anomalous.add(int(rows[i]["packet_id"]))
write_labels("gps_jump", rows, anomalous)

# --- low_battery: rows below warning threshold ---
rows = read_scenario(SCENARIOS_DIR / "low_battery.csv")
anomalous = {int(r["packet_id"]) for r in rows if float(r["battery_voltage_v"]) < 10.5}
write_labels("low_battery", rows, anomalous)

# --- out_of_order_packets: rows where packet_id < previous ---
rows = read_scenario(SCENARIOS_DIR / "out_of_order_packets.csv")
anomalous = set()
for i in range(1, len(rows)):
    if int(rows[i]["packet_id"]) < int(rows[i-1]["packet_id"]):
        anomalous.add(int(rows[i]["packet_id"]))
write_labels("out_of_order_packets", rows, anomalous)

# --- duplicate_packet: second occurrence of repeated packet_id ---
rows = read_scenario(SCENARIOS_DIR / "duplicate_packet.csv")
seen = set()
anomalous = set()
for r in rows:
    pid = int(r["packet_id"])
    if pid in seen:
        anomalous.add(pid)
    seen.add(pid)
write_labels("duplicate_packet", rows, anomalous)

# --- frozen_imu: rows where IMU is identical to previous ---
rows = read_scenario(SCENARIOS_DIR / "frozen_imu.csv")
imu_fields = ["accel_x_g","accel_y_g","accel_z_g","gyro_x_dps","gyro_y_dps","gyro_z_dps"]
anomalous = set()
for i in range(1, len(rows)):
    if all(rows[i][f] == rows[i-1][f] for f in imu_fields):
        anomalous.add(int(rows[i]["packet_id"]))
write_labels("frozen_imu", rows, anomalous)

# --- gps_fix_loss: rows where gps_fix_status = 0 ---
rows = read_scenario(SCENARIOS_DIR / "gps_fix_loss.csv")
anomalous = {int(r["packet_id"]) for r in rows if int(r["gps_fix_status"]) == 0}
write_labels("gps_fix_loss", rows, anomalous)

# --- gps_imu_inconsistency: rows with GPS jump but low IMU motion ---
rows = read_scenario(SCENARIOS_DIR / "gps_imu_inconsistency.csv")
anomalous = set()
for i in range(1, len(rows)):
    dlat = abs(float(rows[i]["gps_lat_deg"]) - float(rows[i-1]["gps_lat_deg"]))
    dlon = abs(float(rows[i]["gps_lon_deg"]) - float(rows[i-1]["gps_lon_deg"]))
    if dlat > 0.001 or dlon > 0.001:
        anomalous.add(int(rows[i]["packet_id"]))
write_labels("gps_imu_inconsistency", rows, anomalous)

# --- combined_fault: label any row that has any detectable fault ---
rows = read_scenario(SCENARIOS_DIR / "combined_fault.csv")
anomalous = set(int(r["packet_id"]) for r in rows)  # all rows in combined are anomalous
write_labels("combined_fault", rows, anomalous)

print("All label files generated.")
```

Run the script:
```bash
python scripts/generate_labels.py
```

---

## Step 3 — Create `guardian/precision_metrics.py`

Create the file `guardian/precision_metrics.py` with the following content.

```python
import csv
from pathlib import Path

# Maps scenario CSV names to their label CSV names.
SCENARIO_LABEL_MAP = {
    "normal_flight.csv":           "normal_flight_labels.csv",
    "packet_loss.csv":             "packet_loss_labels.csv",
    "sensor_dropout.csv":          "sensor_dropout_labels.csv",
    "gps_jump.csv":                "gps_jump_labels.csv",
    "low_battery.csv":             "low_battery_labels.csv",
    "out_of_order_packets.csv":    "out_of_order_packets_labels.csv",
    "duplicate_packet.csv":        "duplicate_packet_labels.csv",
    "frozen_imu.csv":              "frozen_imu_labels.csv",
    "gps_fix_loss.csv":            "gps_fix_loss_labels.csv",
    "gps_imu_inconsistency.csv":   "gps_imu_inconsistency_labels.csv",
    "combined_fault.csv":          "combined_fault_labels.csv",
}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCENARIOS_DIR = _PROJECT_ROOT / "data" / "scenarios"
_LABELS_DIR = _PROJECT_ROOT / "data" / "labels"
_METRICS_DIR = _PROJECT_ROOT / "results" / "metrics"


def load_labels(labels_path):
    """Read a label CSV file and return a dict mapping packet_id to label.

    Parameters
    ----------
    labels_path : Path or str
        Path to a label CSV with columns: packet_id, expected_alert.

    Returns
    -------
    dict[int, int]
        Maps packet_id (int) to expected_alert (0 or 1).
    """
    labels = {}
    with open(labels_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[int(row["packet_id"])] = int(row["expected_alert"])
    return labels


def compute_precision_recall(alerts, labels):
    """Compute precision, recall, and F1 for a set of alerts vs ground truth.

    Parameters
    ----------
    alerts : list[dict]
        List of alert dicts. Each must have a "packet_id" key.
    labels : dict[int, int]
        Ground-truth labels: {packet_id: 0_or_1}.

    Returns
    -------
    dict with keys:
        tp (int)        — true positives: alert raised on a labeled-1 packet
        fp (int)        — false positives: alert raised on a labeled-0 packet
        fn (int)        — false negatives: labeled-1 packet with no alert
        precision (float) — tp / (tp + fp), or None if no alerts
        recall (float)  — tp / (tp + fn), or None if no labeled-1 rows
        f1 (float)      — harmonic mean of precision and recall, or None
    """
    # Build set of packet_ids that received at least one alert
    alerted_packet_ids = {int(a["packet_id"]) for a in alerts}

    # Build set of packet_ids that are labeled as anomalous
    anomalous_packet_ids = {pid for pid, label in labels.items() if label == 1}

    tp = len(alerted_packet_ids & anomalous_packet_ids)
    fp = len(alerted_packet_ids - anomalous_packet_ids)
    fn = len(anomalous_packet_ids - alerted_packet_ids)

    # Precision: what fraction of our alerts were correct?
    if (tp + fp) > 0:
        precision = tp / (tp + fp)
    else:
        precision = None  # no alerts raised at all

    # Recall: what fraction of faults did we catch?
    if (tp + fn) > 0:
        recall = tp / (tp + fn)
    else:
        recall = None  # no labeled anomalies in the scenario

    # F1: harmonic mean of precision and recall
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None

    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def compute_detection_latency_ms(alerts, labels, telemetry_rows):
    """Compute mean detection latency in milliseconds.

    Detection latency = timestamp_ms of first alert on a packet - timestamp_ms
    of that packet's telemetry row.

    For each anomalous packet_id that received an alert, we find the first
    alert's timestamp_ms and the telemetry row's timestamp_ms for that packet.
    The latency is the difference. We return the mean across all detected faults.

    Parameters
    ----------
    alerts : list[dict]
        Alert dicts with "packet_id" and "timestamp_ms".
    labels : dict[int, int]
        Ground-truth labels: {packet_id: 0_or_1}.
    telemetry_rows : list[dict]
        Telemetry row dicts with "packet_id" and "timestamp_ms".

    Returns
    -------
    float or None
        Mean detection latency in milliseconds, or None if no TP detections.
    """
    # Build lookup: packet_id → telemetry timestamp_ms
    tele_ts = {}
    for row in telemetry_rows:
        pid = int(row["packet_id"])
        if pid not in tele_ts:
            tele_ts[pid] = int(row["timestamp_ms"])

    # Build lookup: packet_id → first alert timestamp_ms
    first_alert_ts = {}
    for alert in alerts:
        pid = int(alert["packet_id"])
        ts = int(alert["timestamp_ms"])
        if pid not in first_alert_ts or ts < first_alert_ts[pid]:
            first_alert_ts[pid] = ts

    # Compute latency for each true positive
    latencies = []
    anomalous_pids = {pid for pid, label in labels.items() if label == 1}
    for pid in anomalous_pids:
        if pid in first_alert_ts and pid in tele_ts:
            latency = first_alert_ts[pid] - tele_ts[pid]
            latencies.append(latency)

    if not latencies:
        return None

    return sum(latencies) / len(latencies)


def generate_precision_recall_csv(output_path=None):
    """Run precision/recall/latency computation for all 11 scenarios and
    write the results to a CSV file.

    Parameters
    ----------
    output_path : Path or str, optional
        Output CSV file path. Defaults to results/metrics/precision_recall.csv.
    """
    from guardian.engine import GuardianEngine
    from guardian.replay import replay_csv

    if output_path is None:
        output_path = _METRICS_DIR / "precision_recall.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario", "tp", "fp", "fn",
        "precision", "recall", "f1",
        "mean_latency_ms",
    ]

    rows_out = []

    for scenario_name, label_name in SCENARIO_LABEL_MAP.items():
        scenario_path = _SCENARIOS_DIR / scenario_name
        label_path = _LABELS_DIR / label_name

        if not scenario_path.exists():
            print(f"  [SKIP] {scenario_name} — scenario file not found")
            continue
        if not label_path.exists():
            print(f"  [SKIP] {label_name} — label file not found")
            continue

        # Run the engine on this scenario
        engine = GuardianEngine()
        all_alerts = []
        all_rows = []
        for row in replay_csv(scenario_path, sleep_enabled=False):
            alerts, _ = engine.process_row(row)
            all_alerts.extend(alerts)
            all_rows.append(row)

        # Load labels
        labels = load_labels(label_path)

        # Compute metrics
        metrics = compute_precision_recall(all_alerts, labels)
        latency = compute_detection_latency_ms(all_alerts, labels, all_rows)

        def fmt(v):
            """Format a float to 4 decimal places, or 'N/A' if None."""
            return f"{v:.4f}" if v is not None else "N/A"

        rows_out.append({
            "scenario": scenario_name,
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
            "precision": fmt(metrics["precision"]),
            "recall": fmt(metrics["recall"]),
            "f1": fmt(metrics["f1"]),
            "mean_latency_ms": fmt(latency),
        })
        print(
            f"  {scenario_name:<40} "
            f"P={fmt(metrics['precision'])}  R={fmt(metrics['recall'])}  "
            f"F1={fmt(metrics['f1'])}  latency={fmt(latency)}ms"
        )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nPrecision/recall CSV written to: {output_path}")
```

---

## Step 4 — Create `tests/test_precision_metrics.py`

Create the file `tests/test_precision_metrics.py` with the following content.

```python
import pytest
import csv
from pathlib import Path
from guardian.precision_metrics import (
    load_labels,
    compute_precision_recall,
    compute_detection_latency_ms,
    generate_precision_recall_csv,
)


def write_labels_csv(path, rows):
    """Helper: write a label CSV file for testing."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["packet_id", "expected_alert"])
        writer.writeheader()
        writer.writerows(rows)


def test_load_labels_returns_dict(tmp_path):
    """load_labels() must return a dict mapping int packet_id to int label."""
    label_file = tmp_path / "labels.csv"
    write_labels_csv(label_file, [
        {"packet_id": 1, "expected_alert": 0},
        {"packet_id": 2, "expected_alert": 1},
    ])
    labels = load_labels(label_file)
    assert labels == {1: 0, 2: 1}


def test_compute_precision_recall_perfect_detection():
    """All alerts on anomalous rows → precision=1.0, recall=1.0, f1=1.0."""
    alerts = [{"packet_id": 2}, {"packet_id": 3}]
    labels = {1: 0, 2: 1, 3: 1}
    result = compute_precision_recall(alerts, labels)
    assert result["tp"] == 2
    assert result["fp"] == 0
    assert result["fn"] == 0
    assert abs(result["precision"] - 1.0) < 0.001
    assert abs(result["recall"] - 1.0) < 0.001
    assert abs(result["f1"] - 1.0) < 0.001


def test_compute_precision_recall_false_positive():
    """Alert on a normal row → fp=1, precision < 1.0."""
    alerts = [{"packet_id": 1}]  # packet_id 1 is labeled 0 (normal)
    labels = {1: 0, 2: 1}
    result = compute_precision_recall(alerts, labels)
    assert result["fp"] == 1
    assert result["tp"] == 0
    assert result["fn"] == 1
    assert result["precision"] == 0.0


def test_compute_precision_recall_false_negative():
    """Missed anomalous row → fn=1, recall < 1.0."""
    alerts = []  # no alerts raised
    labels = {1: 0, 2: 1}  # packet 2 is anomalous but no alert was raised
    result = compute_precision_recall(alerts, labels)
    assert result["fn"] == 1
    assert result["tp"] == 0
    assert result["recall"] == 0.0


def test_compute_precision_recall_no_anomalies_in_scenario():
    """When no rows are labeled anomalous (normal_flight), recall is None."""
    alerts = []
    labels = {1: 0, 2: 0, 3: 0}
    result = compute_precision_recall(alerts, labels)
    assert result["recall"] is None
    assert result["f1"] is None


def test_compute_precision_recall_no_alerts_all_anomalous():
    """When all rows are anomalous but no alerts raised → recall=0, precision=None."""
    alerts = []
    labels = {1: 1, 2: 1}
    result = compute_precision_recall(alerts, labels)
    assert result["fn"] == 2
    assert result["precision"] is None
    assert result["recall"] == 0.0


def test_compute_detection_latency_returns_float():
    """compute_detection_latency_ms() must return a float for matched TP."""
    alerts = [{"packet_id": 2, "timestamp_ms": 1050}]
    labels = {1: 0, 2: 1}
    telemetry = [
        {"packet_id": 1, "timestamp_ms": 900},
        {"packet_id": 2, "timestamp_ms": 1000},
    ]
    latency = compute_detection_latency_ms(alerts, labels, telemetry)
    assert isinstance(latency, float)
    assert abs(latency - 50.0) < 0.001  # alert at 1050 - telemetry at 1000 = 50ms


def test_compute_detection_latency_returns_none_when_no_tp():
    """Returns None when no true positives exist."""
    alerts = [{"packet_id": 1, "timestamp_ms": 1000}]  # packet 1 is labeled 0
    labels = {1: 0, 2: 1}
    telemetry = [{"packet_id": 1, "timestamp_ms": 900}]
    result = compute_detection_latency_ms(alerts, labels, telemetry)
    assert result is None


def test_generate_precision_recall_csv_creates_file(tmp_path, monkeypatch):
    """generate_precision_recall_csv() must create the output CSV file."""
    # We monkeypatch the scenario/label dirs to use empty CSVs in tmp_path
    # This only tests that the file is created, not the full computation.
    output_file = tmp_path / "pr.csv"

    import guardian.precision_metrics as pm
    # Point scenario and label maps to empty dirs so no scenarios are found
    monkeypatch.setattr(pm, "SCENARIO_LABEL_MAP", {})

    generate_precision_recall_csv(output_path=output_file)

    assert output_file.exists(), "Output CSV file was not created."


def test_generate_precision_recall_csv_has_correct_header(tmp_path, monkeypatch):
    """The output CSV must have the correct column headers."""
    import guardian.precision_metrics as pm
    monkeypatch.setattr(pm, "SCENARIO_LABEL_MAP", {})

    output_file = tmp_path / "pr.csv"
    generate_precision_recall_csv(output_path=output_file)

    with open(output_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert "scenario" in reader.fieldnames
        assert "precision" in reader.fieldnames
        assert "recall" in reader.fieldnames
        assert "f1" in reader.fieldnames
        assert "mean_latency_ms" in reader.fieldnames
```

---

## Step 5 — Modify `guardian/metrics.py`

Open `guardian/metrics.py`. Find the `generate_metrics_csv()` function. At the very end of the function, after it writes `scenario_metrics.csv`, add these lines:

```python
    # Also compute and write precision/recall metrics
    from guardian.precision_metrics import generate_precision_recall_csv
    print("\nGenerating precision/recall metrics...")
    generate_precision_recall_csv()
```

---

## Step 6 — Modify `guardian/run_pipeline.py`

Open `guardian/run_pipeline.py`. Find the section that reads the validation summary CSV and prints a final summary. After printing the existing summary, add:

```python
    # Print precision/recall summary
    pr_csv = Path("results/metrics/precision_recall.csv")
    if pr_csv.exists():
        import csv
        print("\n--- Precision / Recall Summary ---")
        with open(pr_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                print(
                    f"  {row['scenario']:<40} "
                    f"P={row['precision']}  R={row['recall']}  "
                    f"F1={row['f1']}  latency={row['mean_latency_ms']}ms"
                )
```

---

## Step 7 — Run Tests

```bash
pytest tests/test_precision_metrics.py -v
```

Expected: all tests pass.

```bash
pytest -q
```

Expected: zero failures.

---

## Step 8 — Generate Metrics End-to-End

```bash
python -m guardian.metrics
```

Look for `results/metrics/precision_recall.csv`. Open it and verify:
- `normal_flight.csv` has `precision=N/A` and `recall=N/A` (no anomalies expected, no alerts raised = correct)
- `low_battery.csv` has `precision=1.0000` and `recall=1.0000` if detection is perfect
- Any `fp > 0` means a false alarm is occurring — this is useful information for tuning thresholds

---

## Checklist — Phase 5 Complete When:

- [ ] `data/labels/` directory exists with 11 label CSV files
- [ ] `guardian/precision_metrics.py` exists with 4 functions
- [ ] `tests/test_precision_metrics.py` exists with 9 tests, all passing
- [ ] `guardian/metrics.py` calls `generate_precision_recall_csv()` at the end
- [ ] `guardian/run_pipeline.py` prints precision/recall summary
- [ ] `python -m guardian.metrics` creates `results/metrics/precision_recall.csv`
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
data/
└── labels/                      ← NEW directory with 11 label CSV files

guardian/
├── precision_metrics.py         ← NEW — precision/recall/latency computation
├── metrics.py                   ← MODIFIED — calls generate_precision_recall_csv()
└── run_pipeline.py              ← MODIFIED — prints PR summary

results/metrics/
└── precision_recall.csv         ← GENERATED at runtime

tests/
└── test_precision_metrics.py    ← NEW — 9 tests
```

---

## Proceed to Phase 6 →

Phase 6 builds the Flask dashboard. It reads from the SQLite database (Phase 3) and needs the alert schema to be stable (which Phase 4 completed). Precision/recall data from this phase will be displayed on the dashboard's metrics panel.
