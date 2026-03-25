# Architecture

## High-level flow

RC Aircraft + Sensors
→ Telemetry Sender
→ Ground Receiver
→ Guardian Module
→ Database / Messaging
→ Web Dashboard
→ Operator Action

## System blocks

### RC Aircraft + Sensors
The RC aircraft acts as the onboard telemetry source. It is intended to carry a lightweight embedded sensor node that collects motion, navigation, environmental, and health data during operation.

### Telemetry Sender
The telemetry sender packages sensor readings into structured messages with timestamps and packet IDs, then transmits them to the ground system. This layer is responsible for sending data consistently and preserving packet order as much as possible.

### Ground Receiver
The ground receiver collects incoming telemetry, performs basic parsing and format checks, and forwards valid data to the Guardian pipeline for analysis.

### Guardian Module
The Guardian is the anomaly detection and decision-support core of the system. It analyzes incoming telemetry using deterministic integrity checks, physical-consistency rules, and lightweight anomaly detection methods. When abnormal behavior is detected, it generates alerts with severity, confidence, reason codes, and recommended safe responses.

### Database / Messaging
This layer stores telemetry, anomaly scores, alerts, and operator actions for traceability, replay, and evaluation. It can also support real-time communication between the Guardian and the dashboard.

### Web Dashboard
The dashboard provides a real-time view of telemetry, anomaly status, and alert history. It is designed to present prioritized alerts clearly, reduce alert fatigue, and support rapid understanding during abnormal situations.

### Operator Action
The operator remains part of the decision loop. Depending on the situation, the operator may acknowledge an alert, override a recommendation, escalate a case, or request verification.

## Guardian responsibilities
- read telemetry
- detect anomalies
- generate alerts
- support safe operator decisions

## Human-in-the-Loop Control
The Guardian does not replace human judgment for critical decisions. Instead, it provides explainable alerts and recommended actions while keeping the operator responsible for validation in high-impact situations. This human-in-the-loop design is intended to improve trust, traceability, and safety in connected aerospace operations.

## Telemetry categories
The prototype is designed to process the following categories of data:
- packet and timing data
- IMU / motion data
- GPS / navigation data
- environmental data
- battery / health data
- link / operating state data

## Guardian outputs
For each detected anomaly or suspicious event, the Guardian may produce:
- alert severity
- confidence score
- reason code
- anomaly score
- recommended safe response

## Current prototype scope
The current prototype uses replayable telemetry scenarios stored as CSV files to validate detection logic and alert generation. In later phases, the same architecture is intended to connect to a real RC aircraft testbed with onboard sensors and live telemetry transmission.

## Example flow
A telemetry packet is received from the aircraft or from a replay scenario. The Ground Receiver parses the message and forwards it to the Guardian Module. If the Guardian detects packet loss, a GPS jump, sensor inconsistency, or another abnormal pattern, it generates an alert with severity, confidence, and reason code. The alert is stored in the data layer, displayed on the dashboard, and made available for operator acknowledgement, override, escalation, or verification.
