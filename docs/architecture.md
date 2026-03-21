# Architecture

## High-level flow

RC Aircraft + Sensors
→ Telemetry Sender
→ Ground Receiver
→ Guardian Module
→ Database / Messaging
→ Web Dashboard
→ Operator Action

## Guardian responsibilities
- read telemetry
- detect anomalies
- generate alerts
- support safe operator decisions