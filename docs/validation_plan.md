# Validation Plan

## Goal
Validate that the Guardian detects key connected-system anomalies and produces explainable alerts with consistent recommended actions.

## Scenario-based validation

### normal_flight.csv
Expected result:
- no critical anomaly alerts
- stable ML anomaly scores
- normal telemetry flow

### packet_loss.csv
Expected result:
- `PACKET_LOSS` alert
- recommended action related to link checking

### sensor_dropout.csv
Expected result:
- `IMU_DROPOUT` alert
- recommended action related to sensor checking

### gps_jump.csv
Expected result:
- `GPS_JUMP` alert and/or `GPS_IMU_INCONSISTENCY`
- recommended operator verification or degraded mode response

### low_battery.csv
Expected result:
- `LOW_BATTERY` alert
- warning or critical severity depending on voltage threshold

## Metrics
The prototype will later be evaluated using:
- detection latency
- false-alarm rate
- missed detections
- alert consistency
- operator response time

## Current scope
Current validation is based on replayable CSV scenarios and automated unit tests. Later phases will include live telemetry from an RC aircraft testbed.
