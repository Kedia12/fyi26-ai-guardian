def build_alert(row, severity, confidence, reason_code, reason_text, recommended_action):
    return {
        "timestamp_ms": int(row["timestamp_ms"]),
        "packet_id": int(row["packet_id"]),
        "node_id": row["node_id"],
        "severity": severity,
        "confidence": float(confidence),
        "reason_code": reason_code,
        "reason_text": reason_text,
        "recommended_action": recommended_action,
        "alert_status": "NEW",
    }