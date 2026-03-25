# Telemetry Schema

The aircraft sends telemetry packets with the following fields.

## Packet and timing fields
- `timestamp_ms` — telemetry timestamp in milliseconds
- `packet_id` — sequential packet number
- `node_id` — identifier of the onboard telemetry node

## IMU / motion fields
- `accel_x_g` — acceleration on X axis in g
- `accel_y_g` — acceleration on Y axis in g
- `accel_z_g` — acceleration on Z axis in g
- `gyro_x_dps` — angular velocity on X axis in degrees per second
- `gyro_y_dps` — angular velocity on Y axis in degrees per second
- `gyro_z_dps` — angular velocity on Z axis in degrees per second

## Environmental / altitude fields
- `temperature_c` — temperature in degrees Celsius
- `pressure_hpa` — pressure in hectopascals
- `altitude_est_m` — estimated altitude in meters derived from pressure

## Power / health fields
- `battery_voltage_v` — battery voltage in volts
- `low_power_flag` — low battery indicator (0 = normal, 1 = low power)

## GPS / navigation fields
- `gps_lat_deg` — GPS latitude in decimal degrees
- `gps_lon_deg` — GPS longitude in decimal degrees
- `gps_alt_m` — GPS altitude in meters
- `gps_speed_mps` — GPS speed in meters per second
- `gps_fix_status` — GPS fix state
- `satellite_count` — number of satellites currently used or visible

## Link / operating state fields
- `link_status` — telemetry link state
- `mode_state` — current operating mode of the aircraft or telemetry node

## Notes
- All telemetry packets should include a timestamp and packet ID.
- Packet order and timing are important for detecting missing transmissions, delays, and out-of-order data.
- GPS fields may be unavailable if no fix is present; this should be handled explicitly in the data pipeline.
- `mode_state` can represent states such as normal, degraded, safe, or test depending on the prototype configuration.
- `link_status` can represent states such as connected, weak, lost, or recovered depending on implementation.

## Example telemetry packet

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