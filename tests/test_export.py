import json
import pytest
from guardian.export import AlertExporter


def make_alert(**overrides):
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "severity": "WARNING",
        "confidence": 0.85,
        "reason_code": "TEST_ALERT",
        "reason_text": "Test alert for unit testing.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    }
    base.update(overrides)
    return base


def make_row(**overrides):
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "accel_x_g": 0.01,
        "battery_voltage_v": 11.8,
    }
    base.update(overrides)
    return base


def test_write_alert_creates_file(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()
    assert output_file.exists()


def test_write_alert_produces_valid_json_line(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert isinstance(parsed, dict)


def test_write_alert_record_has_required_top_level_keys(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert(), telemetry_row=make_row())
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert "alert" in record
    assert "telemetry" in record
    assert "exported_at" in record


def test_write_alert_includes_telemetry_row_when_provided(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    row = make_row(battery_voltage_v=9.9)
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert(), telemetry_row=row)
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert float(record["telemetry"]["battery_voltage_v"]) == pytest.approx(9.9)


def test_write_alert_telemetry_is_null_when_not_provided(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert record["telemetry"] is None


def test_write_batch_produces_one_line_per_alert(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    alerts = [make_alert(reason_code=f"CODE_{i}") for i in range(3)]
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_batch(alerts)
    exporter.close()

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_write_batch_empty_list_writes_nothing(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_batch([])
    exporter.close()

    content = output_file.read_text(encoding="utf-8").strip()
    assert content == ""


def test_disabled_exporter_creates_no_file(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=False)
    exporter.write_alert(make_alert())
    exporter.close()
    assert not output_file.exists()


def test_context_manager_closes_file(tmp_path):
    output_file = tmp_path / "alerts.jsonl"
    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert())

    assert exp._handle is None
    assert output_file.exists()


def test_append_mode_accumulates_across_calls(tmp_path):
    output_file = tmp_path / "alerts.jsonl"

    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert(reason_code="FIRST"))

    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert(reason_code="SECOND"))

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    codes = [json.loads(l)["alert"]["reason_code"] for l in lines]
    assert "FIRST" in codes
    assert "SECOND" in codes


def test_creates_parent_directories_automatically(tmp_path):
    nested_path = tmp_path / "a" / "b" / "c" / "alerts.jsonl"
    exporter = AlertExporter(path=nested_path, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()
    assert nested_path.exists()
