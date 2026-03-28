# Dashboard and Database Contract

## Purpose
This document defines the technical interface between the Guardian module, the dashboard, and the database layer.

It is intended to help team members build their parts in parallel while using the same data structure and field names.

## 1. Telemetry input contract

The Guardian processes telemetry rows with the following fields.

### Packet and timing
- `timestamp_ms`
- `packet_id`
- `node_id`

### IMU / motion
- `accel_x_g`
- `accel_y_g`
- `accel_z_g`
- `gyro_x_dps`
- `gyro_y_dps`
- `gyro_z_dps`

### Environmental / altitude
- `temperature_c`
- `pressure_hpa`
- `altitude_est_m`

### Power / health
- `battery_voltage_v`
- `low_power_flag`

### GPS / navigation
- `gps_lat_deg`
- `gps_lon_deg`
- `gps_alt_m`
- `gps_speed_mps`
- `gps_fix_status`
- `satellite_count`

### Link / state
- `link_status`
- `mode_state`

## Example telemetry row

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

2. Guardian alert output contract

The Guardian generates alert objects with the following fields:

• timestamp_ms
• packet_id
• node_id
• severity
• confidence
• reason_code
• reason_text
• recommended_action
• alert_status

Field meanings

• severity
  Alert importance level. Current values used:
    • WARNING
    • CRITICAL

• confidence
Detection confidence score as a float, typically between 0.0 and 1.0

• reason_code
Machine-readable anomaly label, for example:

  • PACKET_LOSS
  • IMU_DROPOUT
  • LOW_BATTERY
  • GPS_JUMP
  • GPS_IMU_INCONSISTENCY
  • OUT_OF_ORDER_PACKET
  • DUPLICATE_PACKET
  • IMU_FROZEN
  • GPS_FIX_LOSS

• reason_text
Human-readable explanation for the alert

• recommended_action
Suggested safe response, for example:
 • CHECK_LINK
 • CHECK_SENSOR
 • ENTER_SAFE_MODE
 • REQUEST_VERIFICATION
 • VERIFY_OPERATOR
 • VERIFY_OPERATOR_AND_ENTER_DEGRADED_MODE

• alert_status
Current alert lifecycle state. Current default:

  • active

Planned future states may include:

  • acknowledged
  • escalated
  • resolved

Example alert object

{
  "timestamp_ms": 152340,
  "packet_id": 248,
  "node_id": "aircraft_01",
  "severity": "CRITICAL",
  "confidence": 0.96,
  "reason_code": "GPS_IMU_INCONSISTENCY",
  "reason_text": "GPS changed significantly without matching IMU motion.",
  "recommended_action": "VERIFY_OPERATOR_AND_ENTER_DEGRADED_MODE",
  "alert_status": "active"
}

3. Dashboard requirements

The dashboard should be able to display:

• live telemetry values
• anomaly alerts
• alert severity
• confidence score
• reason code
• reason text
• recommended action
• alert status
• alert history / timeline

Minimum useful dashboard views

Live telemetry panel

Should show:

 • packet / timestamp
 • battery voltage
 • GPS speed
 • altitude estimate
 • GPS fix status
 • link status
 • mode state

Alert panel

Should show:

 • severity
 • reason code
 • reason text
 • confidence
 • recommended action
 • status

Incident timeline

Should show:

• alert sequence over time
• packet/timestamp reference
• operator actions when available

4. Operator action contract

The dashboard may later send operator actions back to the system or database.

Suggested fields:

• timestamp_ms
• packet_id
• node_id
• reason_code
• action_type
• operator_note

Suggested action_type values:

• acknowledge
• override
• escalate
• request_verification
• resolve

Example operator action object

{
  "timestamp_ms": 152500,
  "packet_id": 248,
  "node_id": "aircraft_01",
  "reason_code": "GPS_IMU_INCONSISTENCY",
  "action_type": "acknowledge",
  "operator_note": "Alert reviewed by operator."
}

5. Database storage suggestions

The database team may want to store data in separate logical tables or collections such as:

Telemetry

Store:

• all telemetry row fields
Alerts

Store:

• all alert object fields
Operator actions

Store:

• operator action fields
• reference to related alert if needed

Validation / metrics

Store or export:

• scenario name
• rows processed
• alerts generated
• warning alerts
• critical alerts
• observed reason codes
• pass/fail validation status

6. Integration notes

• Field names should be kept consistent across Guardian, dashboard, and database.
• reason_code should be treated as the main machine-readable alert category.
• reason_text should be displayed directly to users.
• confidence should be stored as a numeric value, not text.
• alert_status should be stored so alert lifecycle can evolve later.
• Some scenarios can legitimately trigger more than one alert type.

7. Current project phase

At the current prototype stage:

• telemetry is replayed from CSV scenarios
• the Guardian generates structured alerts
• validation and metrics artifacts are generated automatically

In later phases:

• live telemetry will replace replayed-only input
• dashboard actions may become interactive
• database storage may become persistent and queryable