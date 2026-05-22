import csv
from pathlib import Path

from guardian.engine import GuardianEngine
from guardian.replay import replay_csv


def load_labels(path):
    """Load a label CSV into {packet_id: expected_alert} dict.

    CSV must have columns 'packet_id' and 'expected_alert' (0 or 1).
    Duplicate packet_ids are resolved by taking the last value seen.
    Returns empty dict if the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        return {}
    labels = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                labels[int(row["packet_id"])] = int(row["expected_alert"])
            except (KeyError, ValueError):
                continue
    return labels


def compute_precision_recall(alerts, labels):
    """Compare detected alerts against ground-truth labels.

    Uses set-based matching by packet_id to avoid double-counting when
    multiple alerts fire for the same packet.

    Returns dict with keys: tp, fp, fn, precision, recall, f1.
    """
    detected_ids = {int(a["packet_id"]) for a in alerts}
    actual_ids = {pid for pid, lbl in labels.items() if lbl == 1}

    tp = len(detected_ids & actual_ids)
    fp = len(detected_ids - actual_ids)
    fn = len(actual_ids - detected_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


def compute_detection_latency_ms(alerts, labels, telemetry_rows):
    """Return milliseconds between the first ground-truth anomaly and first TP alert.

    Returns None if there are no labeled anomalies or no TP alerts.
    """
    actual_ids = {pid for pid, lbl in labels.items() if lbl == 1}
    if not actual_ids:
        return None

    anomaly_rows = [r for r in telemetry_rows
                    if int(r.get("packet_id", -1)) in actual_ids]
    if not anomaly_rows:
        return None
    first_anomaly_ts = min(int(r["timestamp_ms"]) for r in anomaly_rows)

    tp_alerts = [a for a in alerts
                 if int(a.get("packet_id", -1)) in actual_ids]
    if not tp_alerts:
        return None
    first_detection_ts = min(int(a["timestamp_ms"]) for a in tp_alerts)

    return float(first_detection_ts - first_anomaly_ts)


def generate_precision_recall_csv(output_path=None, scenarios_dir=None, labels_dir=None):
    """Run every labeled scenario through the engine and write a PR metrics CSV.

    Skips scenarios that have no matching label file in labels_dir.
    """
    project_root = Path(__file__).resolve().parent.parent

    if scenarios_dir is None:
        scenarios_dir = project_root / "data" / "scenarios"
    if labels_dir is None:
        labels_dir = project_root / "data" / "labels"
    if output_path is None:
        output_path = project_root / "results" / "metrics" / "precision_recall.csv"

    scenarios_dir = Path(scenarios_dir)
    labels_dir = Path(labels_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario", "tp", "fp", "fn",
        "precision", "recall", "f1", "detection_latency_ms",
    ]
    rows = []

    for scenario_file in sorted(scenarios_dir.glob("*.csv")):
        label_file = labels_dir / scenario_file.name
        if not label_file.exists():
            continue

        labels = load_labels(label_file)
        engine = GuardianEngine()
        all_alerts = []
        all_rows = []

        for row in replay_csv(scenario_file, sleep_enabled=False):
            alerts, _ = engine.process_row(row)
            all_alerts.extend(alerts)
            all_rows.append(row)

        metrics = compute_precision_recall(all_alerts, labels)
        latency = compute_detection_latency_ms(all_alerts, labels, all_rows)

        rows.append({
            "scenario": scenario_file.name,
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
            "precision": f"{metrics['precision']:.3f}",
            "recall": f"{metrics['recall']:.3f}",
            "f1": f"{metrics['f1']:.3f}",
            "detection_latency_ms": latency if latency is not None else "N/A",
        })

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Precision/recall metrics written to: {output_path}")
    return rows


if __name__ == "__main__":
    generate_precision_recall_csv()
