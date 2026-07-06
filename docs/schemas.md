# Data Schemas

This document defines the two core data structures used across the AI Guardian: the **telemetry** packets ingested from the aircraft, and the **alerts** produced by the Guardian engine.

- [Telemetry Schema](#telemetry-schema)
- [Alert Schema](#alert-schema)

---

## Telemetry Schema

The aircraft sends telemetry packets with the following fields.

### Packet and timing fields
- `timestamp_ms` — telemetry timestamp in milliseconds
- `packet_id` — sequential packet number
- `node_id` — identifier of the onboard telemetry node

### IMU / motion fields
- `accel_x_g` — acceleration on X axis in g
- `accel_y_g` — acceleration on Y axis in g
- `accel_z_g` — acceleration on Z axis in g
- `gyro_x_dps` — angular velocity on X axis in degrees per second
- `gyro_y_dps` — angular velocity on Y axis in degrees per second
- `gyro_z_dps` — angular velocity on Z axis in degrees per second

### Environment / power fields
- `temperature_c` — onboard temperature in Celsius
- `pressure_hpa` — barometric pressure in hectopascals
- `altitude_est_m` — estimated altitude in meters
- `battery_voltage_v` — battery voltage in volts
- `low_power_flag` — flag indicating a low-power condition (0 / 1)

### GPS fields
- `gps_lat_deg` — GPS latitude in degrees
- `gps_lon_deg` — GPS longitude in degrees
- `gps_alt_m` — GPS altitude in meters
- `gps_speed_mps` — GPS ground speed in meters per second
- `gps_fix_status` — GPS fix status (e.g. 0 = no fix, 1 = fix)
- `satellite_count` — number of satellites in view

### Link / mode fields
- `link_status` — link state such as connected, weak, lost, or recovered
- `mode_state` — operating mode such as normal, degraded, safe, or test

### Notes
- All telemetry packets should include a timestamp and packet ID.
- Packet order and timing are important for detecting missing transmissions, delays, and out-of-order data.
- GPS fields may be unavailable if no fix is present; this should be handled explicitly in the data pipeline.
- `mode_state` can represent states such as normal, degraded, safe, or test depending on the prototype configuration.
- `link_status` can represent states such as connected, weak, lost, or recovered depending on implementation.

### Example telemetry packet

```json
{
  "timestamp_ms": 152340,
  "packet_id": 248,
  "node_id": "aircraft_01",
  "accel_x_g": 0.02,
  "accel_y_g": -0.01,
  "accel_z_g": 1.03,
  "gyro_x_dps": 0.8,
  "gyro_y_dps": -1.4,
  "gyro_z_dps": 0.3,
  "temperature_c": 26.4,
  "pressure_hpa": 1008.7,
  "altitude_est_m": 42.1,
  "battery_voltage_v": 7.2,
  "low_power_flag": 0,
  "gps_lat_deg": -1.9441,
  "gps_lon_deg": 30.0619,
  "gps_alt_m": 43.0,
  "gps_speed_mps": 12.6,
  "gps_fix_status": 1,
  "satellite_count": 8,
  "link_status": "connected",
  "mode_state": "normal"
}
```

---

## Alert Schema

The Guardian outputs alerts with the following fields.

### Core alert fields
- `timestamp_ms` — timestamp of the telemetry packet associated with the alert
- `packet_id` — packet number associated with the detected event
- `node_id` — identifier of the source telemetry node
- `severity` — alert level, such as info, warning, or critical
- `confidence` — confidence score for the detection, typically between 0.0 and 1.0
- `reason_code` — short machine-readable label for the anomaly type
- `reason_text` — human-readable explanation of why the alert was generated
- `recommended_action` — suggested safe response for the operator or system
- `alert_status` — current alert state, such as active, acknowledged, resolved, or escalated

### Notes
- `severity` should communicate operational importance clearly and consistently.
- `confidence` helps the operator judge how strongly the system believes an anomaly is present.
- `reason_code` is intended for structured filtering, analytics, and repeatable handling logic.
- `reason_text` should remain concise and understandable under time pressure.
- `recommended_action` should guide safe next steps without removing human responsibility for critical decisions.
- `alert_status` supports the human-in-the-loop workflow by tracking what happened after the alert was issued.

### Example alert

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
```
