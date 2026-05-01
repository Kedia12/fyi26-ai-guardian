# Human-in-the-Loop AI Guardian for Connected Aerospace Systems

## Overview

This project is an ongoing end-of-year school project focused on building a **Human-in-the-Loop AI Guardian** for connected aerospace systems.

The goal is to monitor telemetry from an RC aircraft testbed, detect suspicious anomalies or inconsistencies, and generate structured alerts that support safer human decision-making.

The system combines:
- an **RC aircraft telemetry source**
- a **Python-based Guardian module**
- **rule-based anomaly detection**
- a lightweight **unsupervised anomaly score** using Isolation Forest
- a **database and dashboard layer**
- a **human-in-the-loop alert workflow**

---

## Problem Statement

Connected aerospace systems increasingly depend on continuous data exchange between onboard sensors, communication links, and ground-side monitoring tools. While this improves visibility and performance, it also creates risks when data becomes delayed, inconsistent, corrupted, or misleading.

Examples of issues include:
- packet loss
- delayed or out-of-order telemetry
- sensor dropout
- GPS jumps or spoofing-like behavior
- GPS / IMU inconsistency
- low battery instability

If such issues are not detected early, operators may make poor decisions.  
This project aims to address that problem by building a system that can:
- monitor telemetry
- validate data consistency
- detect anomalies
- generate understandable alerts
- recommend safe actions
- keep a human involved in critical decisions

---

## Project Objectives

The main objectives of this MVP are:

1. Build a working telemetry monitoring pipeline using replayed scenario data and later real aircraft data.
2. Detect multiple anomaly scenarios such as packet loss, sensor dropout, GPS jumps, GPS/IMU inconsistency, and low battery.
3. Generate structured alerts with:
   - severity
   - reason code
   - confidence score
   - recommended action
4. Provide outputs that can be visualized in a dashboard.
5. Keep the operator in the loop for final interpretation and action.

---

## MVP Feature Overview

| Feature | Notes | Feasibility | Risks | Priority |
|---|---|---|---|---|
| Telemetry ingestion | Receive and process telemetry from the RC aircraft testbed or replayed scenario files. | High | Hardware delays or inconsistent data format. | High |
| Rule-based anomaly detection | Detect known issues such as packet loss, sensor dropout, GPS jumps, low battery, and GPS/IMU inconsistency. | High | Thresholds may need tuning to reduce false alerts. | High |
| Unsupervised anomaly scoring | Use Isolation Forest to compute a supporting anomaly score from telemetry patterns. | Medium | Small dataset may limit performance and anomaly separation. | Medium |
| Human-in-the-loop alerting | Generate alerts with severity, reason code, confidence, and recommended action for operator review. | High | Alerts may become too frequent if not well calibrated. | High |
| Web dashboard | Display telemetry, alert history, and system state in a browser interface. | Medium | Integration may take time if backend contracts are not fixed early. | High |
| Database storage | Store telemetry, alerts, and operator actions for traceability and replay. | High | Schema changes during development may require refactoring. | Medium |
| Replay mode | Replay CSV scenarios to test the Guardian before full aircraft readiness. | High | Test scenarios may be simpler than real flight data. | High |
| RC aircraft testbed integration | Connect real onboard telemetry from the aircraft to the Guardian system. | Medium | Aircraft readiness, sensor integration, and communication reliability may delay testing. | High |

---

## User Journey MVP

The following diagram shows the basic MVP journey from telemetry generation to operator action.

```mermaid
flowchart TD
    A[RC Aircraft / Replay Scenario] --> B[Telemetry Sent]
    B --> C[Guardian Receives Data]
    C --> D[Rule-Based Checks]
    C --> E[Isolation Forest Anomaly Score]
    D --> F[Alert Decision]
    E --> F[Alert Decision]
    F --> G[Generate Alert]
    G --> H[Store in Database]
    H --> I[Display on Dashboard]
    I --> J[Operator Reviews Alert]
    J --> K[Acknowledge]
    J --> L[Override]
    J --> M[Escalate]
    K --> N[Log Operator Action]
    L --> N[Log Operator Action]
    M --> N[Log Operator Action]


Simple explanation

1. Telemetry comes from the aircraft or replayed scenario files.
2. The Guardian receives and analyzes the data.
3. Rule-based checks and the anomaly score are applied.
4. If suspicious behavior is detected, an alert is generated.
5. The alert is stored and displayed on the dashboard.
6. The operator reviews the alert and can acknowledge, override, or escalate it.
7. The operator action is logged for traceability.

System Architecture

High-Level Flow

Aircraft / Replay Data → Guardian → Database → 

Dashboard → Operator Action

Main Components

• RC aircraft / telemetry source
• Telemetry replay scenarios
• Guardian engine
• Database
• Dashboard
• Human operator

Telemetry Fields

The Guardian works with telemetry fields such as:

• timestamp_ms
• packet_id
• node_id
• accel_x_g
• accel_y_g
• accel_z_g
• gyro_x_dps
• gyro_y_dps
• gyro_z_dps
• temperature_c
• pressure_hpa
• altitude_est_m
• battery_voltage_v
• low_power_flag
• gps_lat_deg
• gps_lon_deg
• gps_alt_m
• gps_speed_mps
• gps_fix_status
• satellite_count
• link_status
• mode_state

These fields help the system analyze:

• motion
• rotation
• altitude
• battery health
• GPS behavior
• communication state
• operating mode

Current Detection Capabilities

The current Guardian prototype can detect:

• PACKET_LOSS
• IMU_DROPOUT
• LOW_BATTERY
• GPS_JUMP
• GPS_IMU_INCONSISTENCY

It also computes a supporting ML anomaly score using Isolation Forest.

Validation Scenarios

The MVP currently relies on replayed CSV scenarios to validate its behavior.

Scenarios
• normal_flight.csv
• packet_loss.csv
• sensor_dropout.csv
• low_battery.csv
• gps_jump.csv

Purpose

These scenarios allow the Guardian to be tested before full aircraft flight readiness.

Tech Stack
Embedded / Hardware
• Arduino / ESP32
• IMU
• GPS module
• barometric sensor
• battery sensing

Software

• Python
• Pandas
• NumPy
• scikit-learn

Database / Backend

• MariaDB / MySQL
• optional Redis

Interface
• Web dashboard
• browser-based monitoring interface

Tools
• GitHub
• Discord

Team
Kedia Ihogoza
• Project lead
• RC aircraft testbed
• telemetry architecture
• anomaly detection logic
• machine learning integration
• system design and coordination

Davi Roset

• Database development
• dashboard development
• data storage structure
• integration support

Scope
In Scope

• RC aircraft telemetry testbed
• replayed telemetry scenario testing
• rule-based anomaly detection
• unsupervised anomaly scoring
• structured alerts
• database support
• dashboard integration

Out of Scope

• full autonomous flight control
• advanced certified avionics
• production-scale deployment
• large supervised ML classification pipeline
• full industrial cybersecurity infrastructure

Risks and Mitigation

Risk	Description	Mitigation
Limited ML experience	The ML part may be difficult to tune at first.	Start with rule-based detection and keep ML lightweight and supportive.
Hardware delays	Aircraft or sensor integration may take more time than expected.	Continue development with replayed CSV scenarios in parallel.
Small team size	A 2-person team has limited capacity.	Keep the MVP focused and clearly divide responsibilities.
Scope expansion	The project may become too broad.	Limit the MVP to telemetry anomaly detection and alerting.
False alerts	Detection thresholds may be too sensitive or not sensitive enough.	Test multiple scenarios and adjust thresholds progressively.

Current Progress
Completed

• project structure set up on GitHub
• telemetry schema defined
• replay-based Guardian testing implemented
• rule-based anomaly detection implemented
• validation scenarios created
• Isolation Forest integrated as a supporting anomaly score

In Progress

• RC aircraft telemetry development
• dashboard and database implementation
• alert visualization workflow
• live integration between components

Planned

• full dashboard integration
• database-backed traceability
• live telemetry ingestion from aircraft
• expanded anomaly scenarios
• improved user interaction flow

Roadmap

Stage 1

• team formation
• idea selection
• MVP definition
• documentation

Stage 2

• telemetry replay system
• Guardian logic
• anomaly scenarios
• first validation tests

Stage 3

• dashboard and database integration
• alert display and traceability
• operator interaction workflow

Stage 4
• aircraft integration
• real telemetry tests
• final evaluation and presentation

Why This Project Matters

This project is not only about detecting anomalies.
It is also about designing a system that supports trustworthy monitoring, clear alerts, and human-centered decision-making in connected aerospace environments.

It brings together:

• embedded systems
• telemetry
• anomaly detection
• data integrity
• interface design
• traceability
• human-in-the-loop system thinking

Status

Ongoing project

This project is actively being developed as an end-of-year school project.
