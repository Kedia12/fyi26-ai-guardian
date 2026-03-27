# Validation Summary

## normal_flight.csv
Expected:
- no critical anomaly alerts

Observed:
- replay completed successfully
- no major anomaly alerts expected in nominal flight

Notes:
- useful as baseline scenario for comparison

## packet_loss.csv
Expected:
- `PACKET_LOSS`

Observed:
- `PACKET_LOSS`

Notes:
- validates packet continuity checking

## sensor_dropout.csv
Expected:
- `IMU_DROPOUT`

Observed:
- `IMU_DROPOUT`

Notes:
- validates zero-value sensor dropout detection

## gps_jump.csv
Expected:
- `GPS_JUMP` and/or `GPS_IMU_INCONSISTENCY`

Observed:
- scenario should trigger abrupt navigation anomaly logic

Notes:
- useful for navigation integrity validation

## low_battery.csv
Expected:
- `LOW_BATTERY`

Observed:
- `LOW_BATTERY`

Notes:
- validates battery threshold alerting

## out_of_order_packets.csv
Expected:
- `OUT_OF_ORDER_PACKET`
- possible `PACKET_LOSS`

Observed:
- `OUT_OF_ORDER_PACKET`
- `PACKET_LOSS`

Notes:
- sequence break can trigger multiple communication-related alerts

## duplicate_packet.csv
Expected:
- `DUPLICATE_PACKET`
- possible `PACKET_LOSS` and `IMU_FROZEN`

Observed:
- `DUPLICATE_PACKET`
- `PACKET_LOSS`
- `IMU_FROZEN`

Notes:
- repeated packet content can trigger more than one rule

## frozen_imu.csv
Expected:
- `IMU_FROZEN`

Observed:
- `IMU_FROZEN`

Notes:
- validates repeated IMU reading detection

## gps_fix_loss.csv
Expected:
- `GPS_FIX_LOSS`

Observed:
- `GPS_FIX_LOSS`

Notes:
- validates degraded GPS reliability handling

## combined_fault.csv
Expected:
- multiple simultaneous alerts

Observed:
- `LOW_BATTERY`
- `PACKET_LOSS`
- `IMU_DROPOUT`
- `DUPLICATE_PACKET`
- `IMU_FROZEN`
- `GPS_FIX_LOSS`
- `GPS_JUMP`

Notes:
- useful as a compound anomaly stress scenario
