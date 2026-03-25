def _safe_int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_alert(row, severity, confidence, reason_code, reason_text, recommended_action):
    return {
        "timestamp_ms": _safe_int(row.get("timestamp_ms")),
        "packet_id": _safe_int(row.get("packet_id")),
        "node_id": row.get("node_id", "unknown"),
        "severity": severity,
        "confidence": _safe_float(confidence),
        "reason_code": reason_code,
        "reason_text": reason_text,
        "recommended_action": recommended_action,
        "alert_status": "active",
    }
