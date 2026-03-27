## Scenario-based validation

### normal_flight.csv
Expected result:
- no critical anomaly alerts
- stable ML anomaly scores
- normal telemetry flow

### packet_loss.csv
Expected result:
- `PACKET_LOSS` alert

### sensor_dropout.csv
Expected result:
- `IMU_DROPOUT` alert

### gps_jump.csv
Expected result:
- `GPS_JUMP` alert and/or `GPS_IMU_INCONSISTENCY`

### low_battery.csv
Expected result:
- `LOW_BATTERY` alert

### out_of_order_packets.csv
Expected result:
- `OUT_OF_ORDER_PACKET` alert
- may also trigger `PACKET_LOSS` because sequence continuity is broken

### duplicate_packet.csv
Expected result:
- `DUPLICATE_PACKET` alert
- may also trigger `PACKET_LOSS` and `IMU_FROZEN` if repeated telemetry values are identical

### frozen_imu.csv
Expected result:
- `IMU_FROZEN` alert

### gps_fix_loss.csv
Expected result:
- `GPS_FIX_LOSS` alert

### combined_fault.csv
Expected result:
- multiple simultaneous alerts, potentially including:
  - `LOW_BATTERY`
  - `PACKET_LOSS`
  - `IMU_DROPOUT`
  - `DUPLICATE_PACKET`
  - `IMU_FROZEN`
  - `GPS_FIX_LOSS`
  - `GPS_JUMP`
  