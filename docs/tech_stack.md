# Tech Stack

Full list of technologies used in the AI Guardian project and what each is used for.

## Architecture Flow

```
Aircraft Sensors → Ground Receiver (MAVLink/UDP/Serial/MQTT) → Guardian Engine
  → Rules + ML Anomaly Detection → SQLite → Flask API → React Dashboard + Claude AI Report
```

## Technologies

| # | Technology | Category | Purpose |
|---|---|---|---|
| 1 | React 18.3 | Frontend | UI framework for dashboard components |
| 2 | TypeScript 5.6 | Frontend | Type-safe frontend code |
| 3 | Vite 6.0 | Frontend | Dev server/build tool, proxies `/api/*` to Flask |
| 4 | Tailwind CSS 3.4 | Frontend | Utility-first styling |
| 5 | PostCSS + Autoprefixer | Frontend | CSS processing for Tailwind |
| 6 | Leaflet / React-Leaflet | Frontend | Interactive map showing live aircraft position |
| 7 | Flask 3.0 | Backend | REST API + dashboard server |
| 8 | Python 3.10+ | Backend | Core runtime language |
| 9 | SQLite (WAL mode) | Database | Stores telemetry, alerts, operator actions, validation metrics |
| 10 | scikit-learn (IsolationForest) | ML / Anomaly Detection | Unsupervised anomaly detection on sensor data |
| 11 | pandas / NumPy | ML / Data | Feature engineering, rolling-window trend analysis |
| 12 | Custom rules engine | ML / Anomaly Detection | Deterministic checks (packet loss, GPS jumps, battery limits, IMU health) |
| 13 | Predictor module (linear regression) | ML / Anomaly Detection | Forecasts battery depletion & IMU drift |
| 14 | Anthropic SDK (Claude Sonnet 4.6) | AI / LLM | Generates human-readable post-flight safety reports |
| 15 | pymavlink (MAVLink protocol) | Data Ingestion | Parses autopilot telemetry (ArduPilot/PX4) |
| 16 | pyserial | Data Ingestion | Serial port telemetry communication |
| 17 | paho-mqtt | Data Ingestion | MQTT broker-based telemetry (optional) |
| 18 | UDP sockets | Data Ingestion | Raw UDP telemetry listener |
| 19 | PyYAML | Config | Parses `guardian_config.yaml` |
| 20 | setuptools | Config | Packaging & CLI entry points (`guardian`, `guardian-dashboard`, etc.) |
| 21 | pytest | Testing | Unit/integration tests (22 test files) |
| 22 | Docker + docker-compose | DevOps | Containerized deployment |
| 23 | GitHub Actions | CI/CD | Automated test + validation pipeline |
| 24 | Makefile | DevOps | Build automation shortcuts |
