# Alert Schema

The Guardian outputs alerts with the following fields.

## Core alert fields
- `timestamp_ms` — timestamp of the telemetry packet associated with the alert
- `packet_id` — packet number associated with the detected event
- `node_id` — identifier of the source telemetry node
- `severity` — alert level, such as info, warning, or critical
- `confidence` — confidence score for the detection, typically between 0.0 and 1.0
- `reason_code` — short machine-readable label for the anomaly type
- `reason_text` — human-readable explanation of why the alert was generated
- `recommended_action` — suggested safe response for the operator or system
- `alert_status` — current alert state, such as active, acknowledged, resolved, or escalated

## Notes
- `severity` should communicate operational importance clearly and consistently.
- `confidence` helps the operator judge how strongly the system believes an anomaly is present.
- `reason_code` is intended for structured filtering, analytics, and repeatable handling logic.
- `reason_text` should remain concise and understandable under time pressure.
- `recommended_action` should guide safe next steps without removing human responsibility for critical decisions.
- `alert_status` supports the human-in-the-loop workflow by tracking what happened after the alert was issued.

## Example alert

```json
{
  "timestamp_ms": 152340,
  "packet_id": 248,
  "node_id": "aircraft_01",
  "severity": "warning",
  "confidence": 0.87,
  "reason_code": "GPS_JUMP",
  "reason_text": "Detected an implausible change in GPS position compared with recent motion trend.",
  "recommended_action": "REQUEST_VERIFICATION",
  "alert_status": "active"
}
