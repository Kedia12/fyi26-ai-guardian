# Guardian Phase 1 Checklist

## Core software
- [x] Rule-based anomaly detection implemented
- [x] ML anomaly scoring implemented
- [x] Replay pipeline implemented
- [x] Engine integrates rules and ML
- [x] Schema validation helpers added

## Scenario coverage
- [x] normal_flight.csv
- [x] packet_loss.csv
- [x] sensor_dropout.csv
- [x] gps_jump.csv
- [x] low_battery.csv
- [x] out_of_order_packets.csv
- [x] duplicate_packet.csv
- [x] frozen_imu.csv
- [x] gps_fix_loss.csv
- [x] gps_imu_inconsistency.csv
- [x] combined_fault.csv

## Validation
- [x] Unit tests added
- [x] Sample alert logs generated
- [x] Validation summary added
- [x] Scenario metrics automated
- [x] Expected vs observed validation automated

## Status
Guardian Phase 1 is focused on replay-based anomaly detection, validation, and evidence generation.

## Next phase candidates
- dashboard integration
- database-backed alert history
- live telemetry ingestion
- RC aircraft sensor integration
- operator workflow refinement
