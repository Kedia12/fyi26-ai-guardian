import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardian.report_generator import (
    build_summary,
    generate_report,
    load_alerts,
)


def _make_alert(severity="WARNING", reason_code="PACKET_LOSS", status="active", ts=1000):
    return {
        "timestamp_ms": ts,
        "severity": severity,
        "reason_code": reason_code,
        "reason_text": "Test alert.",
        "recommended_action": "CHECK_LINK",
        "alert_status": status,
    }


# --- load_alerts ---

def test_load_alerts_returns_empty_for_missing_file(tmp_path):
    alerts = load_alerts(tmp_path / "nonexistent.jsonl")
    assert alerts == []


def test_load_alerts_parses_valid_jsonl(tmp_path):
    log = tmp_path / "alerts.jsonl"
    log.write_text(
        json.dumps(_make_alert()) + "\n" + json.dumps(_make_alert(severity="CRITICAL")) + "\n",
        encoding="utf-8",
    )
    alerts = load_alerts(log)
    assert len(alerts) == 2
    assert alerts[1]["severity"] == "CRITICAL"


def test_load_alerts_skips_malformed_lines(tmp_path):
    log = tmp_path / "alerts.jsonl"
    log.write_text('{"ok": true}\nnot-json\n{"ok": true}\n', encoding="utf-8")
    alerts = load_alerts(log)
    assert len(alerts) == 2


# --- build_summary ---

def test_build_summary_empty():
    summary = build_summary([])
    assert summary["total"] == 0
    assert summary["by_severity"] == {}


def test_build_summary_counts_correctly():
    alerts = [
        _make_alert("CRITICAL", "GPS_JUMP", "active", 1000),
        _make_alert("WARNING", "PACKET_LOSS", "acknowledged", 2000),
        _make_alert("CRITICAL", "LOW_BATTERY", "resolved", 3000),
    ]
    summary = build_summary(alerts)
    assert summary["total"] == 3
    assert summary["by_severity"]["CRITICAL"] == 2
    assert summary["by_severity"]["WARNING"] == 1
    assert summary["by_reason_code"]["GPS_JUMP"] == 1
    assert summary["by_status"]["active"] == 1
    assert summary["first_alert_ts"] == 1000
    assert summary["last_alert_ts"] == 3000


# --- generate_report (mocked API) ---

def _mock_anthropic_client(report_text: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=report_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


def test_generate_report_with_alerts(tmp_path):
    log = tmp_path / "alerts.jsonl"
    log.write_text(
        json.dumps(_make_alert("CRITICAL", "GPS_JUMP", "active", 1000)) + "\n"
        + json.dumps(_make_alert("WARNING", "LOW_BATTERY", "resolved", 5000)) + "\n",
        encoding="utf-8",
    )
    report_path = tmp_path / "post_flight_report.md"
    expected_text = "## Summary\nAll systems nominal."

    mock_client = _mock_anthropic_client(expected_text)
    with patch("guardian.report_generator.anthropic.Anthropic", return_value=mock_client):
        result = generate_report(log_path=log, report_path=report_path, api_key="test-key")

    assert expected_text in result
    assert report_path.exists()
    assert "Post-Flight AI Report" in report_path.read_text(encoding="utf-8")


def test_generate_report_with_empty_log(tmp_path):
    log = tmp_path / "empty.jsonl"
    log.write_text("", encoding="utf-8")
    report_path = tmp_path / "report.md"
    mock_client = _mock_anthropic_client("No anomalies recorded.")

    with patch("guardian.report_generator.anthropic.Anthropic", return_value=mock_client):
        result = generate_report(log_path=log, report_path=report_path, api_key="test-key")

    assert "No anomalies recorded." in result


def test_generate_report_raises_without_api_key(tmp_path):
    log = tmp_path / "alerts.jsonl"
    log.write_text("", encoding="utf-8")
    report_path = tmp_path / "report.md"

    with patch.dict("os.environ", {}, clear=True):
        # Ensure ANTHROPIC_API_KEY is absent
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            generate_report(log_path=log, report_path=report_path, api_key="")
