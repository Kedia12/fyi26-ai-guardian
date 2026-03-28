# Expected Results

This document summarizes the primary expected alert outcome for each replay scenario.

## Expected scenario outcomes

- `normal_flight.csv`
  - expected: no anomaly alerts

- `packet_loss.csv`
  - expected: `PACKET_LOSS`

- `sensor_dropout.csv`
  - expected: `IMU_DROPOUT`

- `gps_jump.csv`
  - expected: `GPS_JUMP`

- `low_battery.csv`
  - expected: `LOW_BATTERY`

- `out_of_order_packets.csv`
  - expected: `OUT_OF_ORDER_PACKET`
  - possible additional alert: `PACKET_LOSS`

- `duplicate_packet.csv`
  - expected: `DUPLICATE_PACKET`
  - possible additional alerts depending on repeated values: `PACKET_LOSS`, `IMU_FROZEN`

- `frozen_imu.csv`
  - expected: `IMU_FROZEN`

- `gps_fix_loss.csv`
  - expected: `GPS_FIX_LOSS`

- `gps_imu_inconsistency.csv`
  - expected: `GPS_IMU_INCONSISTENCY`
  - possible additional alert: `GPS_JUMP`

- `combined_fault.csv`
  - expected: multiple alerts, including:
    - `LOW_BATTERY`
    - `PACKET_LOSS`
    - `IMU_DROPOUT`
    - `GPS_FIX_LOSS`
    - `GPS_JUMP`

## Notes
Some scenarios are intentionally isolated, while others are designed to show realistic rule interaction. For this reason, some files may trigger more than one alert type.
