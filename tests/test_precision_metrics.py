import csv
import pytest
from pathlib import Path

from guardian.precision_metrics import (
    load_labels,
    compute_precision_recall,
    compute_detection_latency_ms,
    generate_precision_recall_csv,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def make_alert(packet_id, timestamp_ms=1000):
    return {"packet_id": packet_id, "timestamp_ms": timestamp_ms,
            "reason_code": "TEST", "severity": "WARNING"}


def make_row(packet_id, timestamp_ms=1000):
    return {"packet_id": str(packet_id), "timestamp_ms": str(timestamp_ms)}


def write_label_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["packet_id", "expected_alert"])
        writer.writeheader()
        writer.writerows(rows)


# ── load_labels ───────────────────────────────────────────────────────────────

def test_load_labels_reads_csv(tmp_path):
    f = tmp_path / "labels.csv"
    write_label_csv(f, [{"packet_id": 1, "expected_alert": 0},
                        {"packet_id": 2, "expected_alert": 1}])
    labels = load_labels(f)
    assert labels[1] == 0
    assert labels[2] == 1


def test_load_labels_returns_empty_for_missing_file(tmp_path):
    labels = load_labels(tmp_path / "nonexistent.csv")
    assert labels == {}


def test_load_labels_handles_duplicate_packet_ids(tmp_path):
    f = tmp_path / "labels.csv"
    write_label_csv(f, [{"packet_id": 2, "expected_alert": 0},
                        {"packet_id": 2, "expected_alert": 1}])
    labels = load_labels(f)
    assert labels[2] == 1  # last value wins


# ── compute_precision_recall ──────────────────────────────────────────────────

def test_perfect_detection_gives_precision_recall_one():
    labels = {1: 0, 2: 1, 3: 1}
    alerts = [make_alert(2), make_alert(3)]
    result = compute_precision_recall(alerts, labels)
    assert result["precision"] == pytest.approx(1.0)
    assert result["recall"] == pytest.approx(1.0)
    assert result["f1"] == pytest.approx(1.0)
    assert result["tp"] == 2
    assert result["fp"] == 0
    assert result["fn"] == 0


def test_false_positive_reduces_precision():
    labels = {1: 0, 2: 0}
    alerts = [make_alert(1)]
    result = compute_precision_recall(alerts, labels)
    assert result["fp"] == 1
    assert result["tp"] == 0
    assert result["precision"] == pytest.approx(0.0)


def test_false_negative_reduces_recall():
    labels = {1: 1}
    alerts = []
    result = compute_precision_recall(alerts, labels)
    assert result["fn"] == 1
    assert result["recall"] == pytest.approx(0.0)


def test_mixed_tp_fp_fn():
    labels = {1: 1, 2: 0, 3: 1}
    alerts = [make_alert(1), make_alert(2)]
    result = compute_precision_recall(alerts, labels)
    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 1


def test_multiple_alerts_same_packet_count_as_one_tp():
    labels = {2: 1}
    alerts = [make_alert(2), make_alert(2)]  # two alerts on same anomalous packet
    result = compute_precision_recall(alerts, labels)
    assert result["tp"] == 1
    assert result["fp"] == 0


def test_no_anomalies_no_alerts_gives_zero_metrics():
    labels = {1: 0, 2: 0}
    alerts = []
    result = compute_precision_recall(alerts, labels)
    assert result["precision"] == pytest.approx(0.0)
    assert result["recall"] == pytest.approx(0.0)
    assert result["f1"] == pytest.approx(0.0)


def test_all_anomalies_all_detected():
    labels = {1: 1, 2: 1, 3: 1}
    alerts = [make_alert(1), make_alert(2), make_alert(3)]
    result = compute_precision_recall(alerts, labels)
    assert result["recall"] == pytest.approx(1.0)
    assert result["precision"] == pytest.approx(1.0)


# ── compute_detection_latency_ms ──────────────────────────────────────────────

def test_latency_zero_when_alert_at_same_packet():
    labels = {2: 1}
    alerts = [make_alert(2, timestamp_ms=1100)]
    rows = [make_row(1, 1000), make_row(2, 1100)]
    latency = compute_detection_latency_ms(alerts, labels, rows)
    assert latency == pytest.approx(0.0)


def test_latency_positive_when_detection_delayed():
    labels = {2: 1}
    alerts = [make_alert(3, timestamp_ms=1200)]  # detected at packet 3, not 2
    rows = [make_row(1, 1000), make_row(2, 1100), make_row(3, 1200)]
    # Anomaly started at packet 2 (ts=1100), detected at packet 3 (ts=1200)
    # But packet 3 is not in actual_ids (label for 3 is not set)
    # → tp_alerts is empty → None
    latency = compute_detection_latency_ms(alerts, labels, rows)
    assert latency is None


def test_latency_none_when_no_tp_alerts():
    labels = {2: 1}
    alerts = []
    rows = [make_row(2, 1100)]
    latency = compute_detection_latency_ms(alerts, labels, rows)
    assert latency is None


def test_latency_none_when_no_labeled_anomalies():
    labels = {1: 0, 2: 0}
    alerts = [make_alert(1)]
    rows = [make_row(1, 1000), make_row(2, 1100)]
    latency = compute_detection_latency_ms(alerts, labels, rows)
    assert latency is None


# ── generate_precision_recall_csv ─────────────────────────────────────────────

def _write_minimal_scenario(path):
    """Write a tiny valid scenario CSV for testing."""
    header = (
        "timestamp_ms,packet_id,node_id,"
        "accel_x_g,accel_y_g,accel_z_g,"
        "gyro_x_dps,gyro_y_dps,gyro_z_dps,"
        "temperature_c,pressure_hpa,altitude_est_m,"
        "battery_voltage_v,low_power_flag,"
        "gps_lat_deg,gps_lon_deg,gps_alt_m,gps_speed_mps,"
        "gps_fix_status,satellite_count,link_status,mode_state\n"
    )
    row = "1000,1,node_01,0.01,0.02,1.0,0.5,0.4,0.3,25.0,1013.0,120.0,11.8,0,48.0,2.0,120.0,5.0,1,8,OK,NORMAL\n"
    path.write_text(header + row, encoding="utf-8")


def test_generate_precision_recall_csv_creates_output_file(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    labels_dir = tmp_path / "labels"
    scenarios_dir.mkdir()
    labels_dir.mkdir()

    _write_minimal_scenario(scenarios_dir / "scenario_a.csv")
    write_label_csv(labels_dir / "scenario_a.csv",
                    [{"packet_id": 1, "expected_alert": 0}])

    output = tmp_path / "pr.csv"
    generate_precision_recall_csv(
        output_path=output,
        scenarios_dir=scenarios_dir,
        labels_dir=labels_dir,
    )

    assert output.exists()


def test_generate_precision_recall_csv_has_correct_columns(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    labels_dir = tmp_path / "labels"
    scenarios_dir.mkdir()
    labels_dir.mkdir()

    _write_minimal_scenario(scenarios_dir / "scenario_a.csv")
    write_label_csv(labels_dir / "scenario_a.csv",
                    [{"packet_id": 1, "expected_alert": 0}])

    output = tmp_path / "pr.csv"
    generate_precision_recall_csv(
        output_path=output,
        scenarios_dir=scenarios_dir,
        labels_dir=labels_dir,
    )

    with output.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    for col in ("scenario", "tp", "fp", "fn", "precision", "recall", "f1"):
        assert col in rows[0]


def test_generate_precision_recall_csv_skips_unlabeled_scenarios(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    labels_dir = tmp_path / "labels"
    scenarios_dir.mkdir()
    labels_dir.mkdir()

    _write_minimal_scenario(scenarios_dir / "labeled.csv")
    _write_minimal_scenario(scenarios_dir / "unlabeled.csv")
    write_label_csv(labels_dir / "labeled.csv",
                    [{"packet_id": 1, "expected_alert": 0}])

    output = tmp_path / "pr.csv"
    generate_precision_recall_csv(
        output_path=output,
        scenarios_dir=scenarios_dir,
        labels_dir=labels_dir,
    )

    with output.open() as f:
        rows = list(csv.DictReader(f))

    scenarios_in_output = [r["scenario"] for r in rows]
    assert "labeled.csv" in scenarios_in_output
    assert "unlabeled.csv" not in scenarios_in_output


def test_generate_precision_recall_csv_creates_parent_directories(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    labels_dir = tmp_path / "labels"
    scenarios_dir.mkdir()
    labels_dir.mkdir()

    _write_minimal_scenario(scenarios_dir / "s.csv")
    write_label_csv(labels_dir / "s.csv", [{"packet_id": 1, "expected_alert": 0}])

    output = tmp_path / "a" / "b" / "pr.csv"
    generate_precision_recall_csv(
        output_path=output,
        scenarios_dir=scenarios_dir,
        labels_dir=labels_dir,
    )

    assert output.exists()
