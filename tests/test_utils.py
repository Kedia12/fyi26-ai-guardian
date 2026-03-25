from guardian.utils import format_alert


def test_format_alert_returns_string():
    alert = {
        "severity": "WARNING",
        "reason_code": "PACKET_LOSS",
        "confidence": 0.85,
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    }

    result = format_alert(alert)

    assert isinstance(result, str)
    assert "PACKET_LOSS" in result
    assert "CHECK_LINK" in result
    