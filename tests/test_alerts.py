from guardian.alerts import build_alert


def test_build_alert_returns_expected_fields():
    row = {
        "timestamp_ms": 1000,
        "packet_id": 5,
        "node_id": "aircraft_01",
    }

    alert = build_alert(
        row=row,
        severity="WARNING",
        confidence=0.85,
        reason_code="PACKET_LOSS",
        reason_text="Missing packet sequence detected.",
        recommended_action="CHECK_LINK",
    )

    assert alert["timestamp_ms"] == 1000
    assert alert["packet_id"] == 5
    assert alert["node_id"] == "aircraft_01"
    assert alert["severity"] == "WARNING"
    assert alert["confidence"] == 0.85
    assert alert["reason_code"] == "PACKET_LOSS"
    assert alert["recommended_action"] == "CHECK_LINK"
    assert alert["alert_status"] == "active"


def test_build_alert_handles_missing_values():
    row = {}

    alert = build_alert(
        row=row,
        severity="CRITICAL",
        confidence="0.97",
        reason_code="GPS_JUMP",
        reason_text="Abrupt GPS change detected.",
        recommended_action="REQUEST_VERIFICATION",
    )

    assert alert["timestamp_ms"] == -1
    assert alert["packet_id"] == -1
    assert alert["node_id"] == "unknown"
    assert alert["confidence"] == 0.97
    assert alert["alert_status"] == "active"
    