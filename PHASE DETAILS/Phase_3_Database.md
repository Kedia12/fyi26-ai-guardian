# Phase 3 — Database Persistence
**Fixes Gap 3: No database persistence — all data is lost when the program exits**

---

## Why This Phase Comes Third

The JSON exporter (Phase 2) gives you a flat file that accumulates alerts. But to build a dashboard (Phase 6) you need to query alerts by ID, update their status, and fetch recent records efficiently. A flat file cannot do that. SQLite is the right tool here: it is a proper relational database, it requires zero server setup, and its driver (`sqlite3`) is built into Python's standard library.

This phase builds the entire database layer that the dashboard will read from and write to.

---

## Prerequisites

- Phase 1 (config system) must be complete — this phase reads `config["database"]["enabled"]` and `config["database"]["path"]`
- Phase 2 (JSON export) must be complete — the engine pattern from Phase 2 is extended here

---

## Files You Will Create

```
guardian/db.py                   ← GuardianDB class with all CRUD methods
tests/test_db.py                 ← tests for every database operation
```

## Files You Will Modify

```
guardian/engine.py               ← add optional db parameter, call insert methods
guardian/run_pipeline.py         ← instantiate GuardianDB if enabled in config
```

## No new pip dependencies

`sqlite3` is part of Python's standard library. Nothing to install.

---

## Step 1 — Create `guardian/db.py`

Create the file `guardian/db.py` with the following content. Every method is explained with docstrings and inline comments.

```python
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# SQL schema definition
# ---------------------------------------------------------------------------
# This string contains all CREATE TABLE statements. They use IF NOT EXISTS
# so calling _init_schema() multiple times (e.g. across runs) is safe.

DB_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS Telemetry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms    INTEGER,
    packet_id       INTEGER,
    node_id         TEXT,
    accel_x_g       REAL,
    accel_y_g       REAL,
    accel_z_g       REAL,
    gyro_x_dps      REAL,
    gyro_y_dps      REAL,
    gyro_z_dps      REAL,
    temperature_c   REAL,
    pressure_hpa    REAL,
    altitude_est_m  REAL,
    battery_voltage_v REAL,
    low_power_flag  INTEGER,
    gps_lat_deg     REAL,
    gps_lon_deg     REAL,
    gps_alt_m       REAL,
    gps_speed_mps   REAL,
    gps_fix_status  INTEGER,
    satellite_count INTEGER,
    link_status     TEXT,
    mode_state      TEXT,
    ml_anomaly_score REAL,
    ingested_at     TEXT
);

CREATE TABLE IF NOT EXISTS Alerts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms        INTEGER,
    packet_id           INTEGER,
    node_id             TEXT,
    severity            TEXT,
    confidence          REAL,
    reason_code         TEXT,
    reason_text         TEXT,
    recommended_action  TEXT,
    alert_status        TEXT DEFAULT 'active',
    ml_source           INTEGER DEFAULT 0,
    created_at          TEXT
);

CREATE TABLE IF NOT EXISTS Operator_Actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id        INTEGER REFERENCES Alerts(id),
    timestamp_ms    INTEGER,
    packet_id       INTEGER,
    node_id         TEXT,
    reason_code     TEXT,
    action_type     TEXT,
    operator_note   TEXT,
    acted_at        TEXT
);

CREATE TABLE IF NOT EXISTS Validation_Metrics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario                TEXT,
    rows_processed          INTEGER,
    alerts_generated        INTEGER,
    warning_alerts          INTEGER,
    critical_alerts         INTEGER,
    observed_reason_codes   TEXT,
    expected_reason_codes   TEXT,
    match                   TEXT,
    run_at                  TEXT
);
"""


# ---------------------------------------------------------------------------
# GuardianDB class
# ---------------------------------------------------------------------------

class GuardianDB:
    """SQLite-backed persistence layer for the Guardian system.

    Stores telemetry rows, alerts, operator actions, and validation metrics.
    Uses WAL (Write-Ahead Logging) journal mode so the dashboard can read
    while the engine is writing without blocking.

    Parameters
    ----------
    path : str or Path
        Path to the SQLite database file. Created if it does not exist.
        Parent directories are created automatically.
    """

    def __init__(self, path):
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False allows the connection to be used from
        # the Flask dashboard thread and the engine thread simultaneously.
        # WAL mode (set in DB_SCHEMA) handles the concurrency safely.
        self.conn = sqlite3.connect(str(resolved), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # rows behave like dicts

        self._init_schema()

    def _init_schema(self):
        """Create all tables if they do not already exist."""
        self.conn.executescript(DB_SCHEMA)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Insert methods
    # ------------------------------------------------------------------

    def insert_telemetry(self, row):
        """Insert one telemetry row into the Telemetry table.

        Parameters
        ----------
        row : dict
            A telemetry row dict with the 22 standard fields. Extra keys
            (e.g. ml_anomaly_score added by the engine) are also stored.

        Returns
        -------
        int
            The rowid (primary key) of the inserted record.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO Telemetry (
                timestamp_ms, packet_id, node_id,
                accel_x_g, accel_y_g, accel_z_g,
                gyro_x_dps, gyro_y_dps, gyro_z_dps,
                temperature_c, pressure_hpa, altitude_est_m,
                battery_voltage_v, low_power_flag,
                gps_lat_deg, gps_lon_deg, gps_alt_m, gps_speed_mps,
                gps_fix_status, satellite_count,
                link_status, mode_state,
                ml_anomaly_score, ingested_at
            ) VALUES (
                :timestamp_ms, :packet_id, :node_id,
                :accel_x_g, :accel_y_g, :accel_z_g,
                :gyro_x_dps, :gyro_y_dps, :gyro_z_dps,
                :temperature_c, :pressure_hpa, :altitude_est_m,
                :battery_voltage_v, :low_power_flag,
                :gps_lat_deg, :gps_lon_deg, :gps_alt_m, :gps_speed_mps,
                :gps_fix_status, :satellite_count,
                :link_status, :mode_state,
                :ml_anomaly_score, :ingested_at
            )
            """,
            {**row, "ingested_at": now, "ml_anomaly_score": row.get("ml_anomaly_score")},
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_alert(self, alert, ml_source=False):
        """Insert one alert into the Alerts table.

        Parameters
        ----------
        alert : dict
            An alert dict with the 9 standard fields from alert_schema.md.
        ml_source : bool
            True if this alert was generated by the ML model (ML_ANOMALY),
            False if generated by a deterministic rule.

        Returns
        -------
        int
            The rowid (primary key) of the inserted record.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO Alerts (
                timestamp_ms, packet_id, node_id,
                severity, confidence, reason_code,
                reason_text, recommended_action,
                alert_status, ml_source, created_at
            ) VALUES (
                :timestamp_ms, :packet_id, :node_id,
                :severity, :confidence, :reason_code,
                :reason_text, :recommended_action,
                :alert_status, :ml_source, :created_at
            )
            """,
            {
                **alert,
                "ml_source": 1 if ml_source else 0,
                "created_at": now,
            },
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_operator_action(self, action):
        """Insert one operator action into the Operator_Actions table.

        Parameters
        ----------
        action : dict
            Must contain: alert_id, action_type.
            Optional keys: timestamp_ms, packet_id, node_id,
                           reason_code, operator_note.

        Returns
        -------
        int
            The rowid of the inserted record.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO Operator_Actions (
                alert_id, timestamp_ms, packet_id, node_id,
                reason_code, action_type, operator_note, acted_at
            ) VALUES (
                :alert_id, :timestamp_ms, :packet_id, :node_id,
                :reason_code, :action_type, :operator_note, :acted_at
            )
            """,
            {
                "alert_id": action.get("alert_id"),
                "timestamp_ms": action.get("timestamp_ms"),
                "packet_id": action.get("packet_id"),
                "node_id": action.get("node_id"),
                "reason_code": action.get("reason_code"),
                "action_type": action.get("action_type"),
                "operator_note": action.get("operator_note", ""),
                "acted_at": now,
            },
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_validation_metric(self, metric):
        """Insert one validation metric record.

        Parameters
        ----------
        metric : dict
            Keys: scenario, rows_processed, alerts_generated,
                  warning_alerts, critical_alerts, observed_reason_codes,
                  expected_reason_codes, match.

        Returns
        -------
        int
            The rowid of the inserted record.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO Validation_Metrics (
                scenario, rows_processed, alerts_generated,
                warning_alerts, critical_alerts,
                observed_reason_codes, expected_reason_codes,
                match, run_at
            ) VALUES (
                :scenario, :rows_processed, :alerts_generated,
                :warning_alerts, :critical_alerts,
                :observed_reason_codes, :expected_reason_codes,
                :match, :run_at
            )
            """,
            {**metric, "run_at": now},
        )
        self.conn.commit()
        return cursor.lastrowid

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_recent_alerts(self, limit=50):
        """Return the most recent alerts in descending timestamp order.

        Parameters
        ----------
        limit : int
            Maximum number of alerts to return.

        Returns
        -------
        list[dict]
            List of alert dicts with all Alerts table columns.
        """
        cursor = self.conn.execute(
            "SELECT * FROM Alerts ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_telemetry(self, limit=1):
        """Return the most recently ingested telemetry rows.

        Parameters
        ----------
        limit : int
            Maximum number of rows to return.

        Returns
        -------
        list[dict]
            List of telemetry row dicts.
        """
        cursor = self.conn.execute(
            "SELECT * FROM Telemetry ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_alert_by_id(self, alert_id):
        """Fetch a single alert by its primary key.

        Parameters
        ----------
        alert_id : int
            The Alerts.id value.

        Returns
        -------
        dict or None
            Alert dict, or None if not found.
        """
        cursor = self.conn.execute(
            "SELECT * FROM Alerts WHERE id = ?",
            (alert_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_active_alerts(self):
        """Return all alerts with status 'active', newest first.

        Returns
        -------
        list[dict]
        """
        cursor = self.conn.execute(
            "SELECT * FROM Alerts WHERE alert_status = 'active' ORDER BY id DESC",
        )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Update methods
    # ------------------------------------------------------------------

    def update_alert_status(self, alert_id, new_status):
        """Change the alert_status field of a specific alert.

        Valid status values: 'active', 'acknowledged', 'escalated',
                             'resolved'.

        Parameters
        ----------
        alert_id : int
            The Alerts.id primary key.
        new_status : str
            The new status string.
        """
        self.conn.execute(
            "UPDATE Alerts SET alert_status = ? WHERE id = ?",
            (new_status, alert_id),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Close the database connection.

        Safe to call multiple times.
        """
        if self.conn:
            self.conn.close()
```

---

## Step 2 — Create `tests/test_db.py`

Create the file `tests/test_db.py` with the following content.

```python
import pytest
from guardian.db import GuardianDB


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_telemetry_row(**overrides):
    """Return a minimal telemetry row dict for testing."""
    row = {
        "timestamp_ms": 1000, "packet_id": 1, "node_id": "node_01",
        "accel_x_g": 0.01, "accel_y_g": 0.02, "accel_z_g": 1.0,
        "gyro_x_dps": 0.1, "gyro_y_dps": 0.2, "gyro_z_dps": 0.3,
        "temperature_c": 25.0, "pressure_hpa": 1013.0, "altitude_est_m": 10.0,
        "battery_voltage_v": 11.8, "low_power_flag": 0,
        "gps_lat_deg": 43.5, "gps_lon_deg": -79.3, "gps_alt_m": 10.0,
        "gps_speed_mps": 5.0, "gps_fix_status": 1, "satellite_count": 8,
        "link_status": "ok", "mode_state": "AUTO",
    }
    row.update(overrides)
    return row


def make_alert(**overrides):
    """Return a minimal alert dict for testing."""
    alert = {
        "timestamp_ms": 1000, "packet_id": 1, "node_id": "node_01",
        "severity": "WARNING", "confidence": 0.85,
        "reason_code": "TEST_ALERT", "reason_text": "Test.",
        "recommended_action": "CHECK_LINK", "alert_status": "active",
    }
    alert.update(overrides)
    return alert


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_init_creates_all_four_tables(tmp_path):
    """Connecting to a new DB must create all 4 required tables."""
    db = GuardianDB(tmp_path / "test.db")
    cursor = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    db.close()

    assert "Telemetry" in tables
    assert "Alerts" in tables
    assert "Operator_Actions" in tables
    assert "Validation_Metrics" in tables


def test_init_idempotent_does_not_error_on_second_call(tmp_path):
    """Connecting to an existing DB must not raise an error."""
    db_path = tmp_path / "test.db"
    db1 = GuardianDB(db_path)
    db1.close()
    db2 = GuardianDB(db_path)   # second connection to same file
    db2.close()


# ---------------------------------------------------------------------------
# Telemetry insert tests
# ---------------------------------------------------------------------------

def test_insert_telemetry_returns_positive_rowid(tmp_path):
    """insert_telemetry() must return a positive integer rowid."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_telemetry(make_telemetry_row())
    db.close()
    assert isinstance(rowid, int)
    assert rowid > 0


def test_insert_telemetry_stores_all_fields(tmp_path):
    """The stored row must match the input dict for key fields."""
    db = GuardianDB(tmp_path / "test.db")
    db.insert_telemetry(make_telemetry_row(packet_id=42, battery_voltage_v=11.1))
    rows = db.get_recent_telemetry(limit=1)
    db.close()

    assert len(rows) == 1
    assert rows[0]["packet_id"] == 42
    assert abs(rows[0]["battery_voltage_v"] - 11.1) < 0.001


# ---------------------------------------------------------------------------
# Alert insert and query tests
# ---------------------------------------------------------------------------

def test_insert_alert_returns_positive_rowid(tmp_path):
    """insert_alert() must return a positive integer rowid."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_alert(make_alert())
    db.close()
    assert isinstance(rowid, int)
    assert rowid > 0


def test_get_recent_alerts_returns_correct_count(tmp_path):
    """get_recent_alerts(limit=2) must return at most 2 rows when 3 exist."""
    db = GuardianDB(tmp_path / "test.db")
    for i in range(3):
        db.insert_alert(make_alert(packet_id=i))
    result = db.get_recent_alerts(limit=2)
    db.close()
    assert len(result) == 2


def test_get_recent_alerts_returns_newest_first(tmp_path):
    """get_recent_alerts() must return rows in descending id order."""
    db = GuardianDB(tmp_path / "test.db")
    db.insert_alert(make_alert(packet_id=1))
    db.insert_alert(make_alert(packet_id=2))
    result = db.get_recent_alerts(limit=2)
    db.close()
    # First item should have the higher id (newest)
    assert result[0]["id"] > result[1]["id"]


def test_get_alert_by_id_returns_correct_record(tmp_path):
    """get_alert_by_id() must return the alert with the matching id."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_alert(make_alert(reason_code="SPECIFIC_CODE"))
    found = db.get_alert_by_id(rowid)
    db.close()

    assert found is not None
    assert found["reason_code"] == "SPECIFIC_CODE"
    assert found["id"] == rowid


def test_get_alert_by_id_returns_none_for_missing(tmp_path):
    """get_alert_by_id() must return None when the id does not exist."""
    db = GuardianDB(tmp_path / "test.db")
    result = db.get_alert_by_id(99999)
    db.close()
    assert result is None


# ---------------------------------------------------------------------------
# Status update tests
# ---------------------------------------------------------------------------

def test_update_alert_status_changes_field(tmp_path):
    """update_alert_status() must change the alert_status field."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_alert(make_alert())
    db.update_alert_status(rowid, "acknowledged")
    updated = db.get_alert_by_id(rowid)
    db.close()
    assert updated["alert_status"] == "acknowledged"


def test_update_alert_status_to_escalated(tmp_path):
    """update_alert_status() must support 'escalated' status."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_alert(make_alert())
    db.update_alert_status(rowid, "escalated")
    updated = db.get_alert_by_id(rowid)
    db.close()
    assert updated["alert_status"] == "escalated"


# ---------------------------------------------------------------------------
# Operator action tests
# ---------------------------------------------------------------------------

def test_insert_operator_action_stores_note(tmp_path):
    """insert_operator_action() must store the operator_note field."""
    db = GuardianDB(tmp_path / "test.db")
    alert_id = db.insert_alert(make_alert())
    db.insert_operator_action({
        "alert_id": alert_id,
        "action_type": "acknowledge",
        "operator_note": "Reviewed by operator A",
    })
    cursor = db.conn.execute(
        "SELECT operator_note FROM Operator_Actions WHERE alert_id = ?",
        (alert_id,)
    )
    row = cursor.fetchone()
    db.close()
    assert row is not None
    assert row[0] == "Reviewed by operator A"


def test_insert_operator_action_returns_positive_rowid(tmp_path):
    """insert_operator_action() must return a positive rowid."""
    db = GuardianDB(tmp_path / "test.db")
    alert_id = db.insert_alert(make_alert())
    rowid = db.insert_operator_action({
        "alert_id": alert_id,
        "action_type": "resolve",
    })
    db.close()
    assert rowid > 0


# ---------------------------------------------------------------------------
# Validation metrics tests
# ---------------------------------------------------------------------------

def test_insert_validation_metric_returns_rowid(tmp_path):
    """insert_validation_metric() must return a positive rowid."""
    db = GuardianDB(tmp_path / "test.db")
    rowid = db.insert_validation_metric({
        "scenario": "low_battery.csv",
        "rows_processed": 20,
        "alerts_generated": 5,
        "warning_alerts": 3,
        "critical_alerts": 2,
        "observed_reason_codes": "LOW_BATTERY",
        "expected_reason_codes": "LOW_BATTERY",
        "match": "PASS",
    })
    db.close()
    assert rowid > 0


# ---------------------------------------------------------------------------
# Active alerts test
# ---------------------------------------------------------------------------

def test_get_all_active_alerts_excludes_acknowledged(tmp_path):
    """get_all_active_alerts() must not include acknowledged alerts."""
    db = GuardianDB(tmp_path / "test.db")
    id1 = db.insert_alert(make_alert())
    id2 = db.insert_alert(make_alert())
    db.update_alert_status(id2, "acknowledged")

    active = db.get_all_active_alerts()
    db.close()

    active_ids = {a["id"] for a in active}
    assert id1 in active_ids
    assert id2 not in active_ids
```

---

## Step 3 — Modify `guardian/engine.py`

Open `guardian/engine.py`. You need to add an optional `db` parameter and call insert methods.

### 3a — Add import at the top

```python
from guardian.config import get_config
```

(You may already have this from Phase 2. If so, skip this line.)

### 3b — Add `db=None` parameter to `__init__()`

Find the `__init__` method signature:
```python
def __init__(self):
```
Change it to:
```python
def __init__(self, db=None):
```
Then add this line inside `__init__`, after the existing code:
```python
    self.db = db
```

### 3c — Call DB insert methods in `process_row()`

Find the end of `process_row()`, just before the export call you added in Phase 2. Add:

```python
    # Persist to database if one was provided.
    if self.db is not None:
        self.db.insert_telemetry(row)
        is_ml_alert = lambda a: a.get("reason_code") == "ML_ANOMALY"
        for alert in alerts:
            self.db.insert_alert(alert, ml_source=is_ml_alert(alert))
```

The full end of `process_row()` now looks like this:

```python
    # Update previous row tracking
    self.prev_row = row

    # Persist to database
    if self.db is not None:
        self.db.insert_telemetry(row)
        for alert in alerts:
            self.db.insert_alert(alert, ml_source=(alert.get("reason_code") == "ML_ANOMALY"))

    # Export to JSONL
    if self.exporter:
        self.exporter.write_batch(alerts, row)

    return alerts, anomaly_score
```

---

## Step 4 — Modify `guardian/run_pipeline.py`

Open `guardian/run_pipeline.py`. Find the `main()` function. Add the following logic at the beginning of `main()`, before the pipeline steps run:

```python
from guardian.config import get_config
from guardian.db import GuardianDB

def main():
    cfg = get_config()
    db_cfg = cfg.get("database", {})
    db = None
    if db_cfg.get("enabled", False):
        db_path = db_cfg.get("path", "results/guardian.db")
        db = GuardianDB(db_path)
        print(f"Database persistence enabled: {db_path}")

    # ... rest of the existing pipeline steps ...
```

And at the end of `main()`, close the DB if it was opened:
```python
    if db is not None:
        db.close()
```

---

## Step 5 — Run Tests

```bash
# Run the new database tests
pytest tests/test_db.py -v
```

Expected: all tests pass.

```bash
# Run full suite
pytest -q
```

Expected: zero failures.

---

## Step 6 — Test the Database End-to-End

Open `config/guardian_config.yaml` and change:
```yaml
database:
  enabled: false
```
to:
```yaml
database:
  enabled: true
```

Then run:
```bash
python -m guardian.main data/scenarios/combined_fault.csv
```

Then query the database to verify data was saved:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('results/guardian.db')
alerts = conn.execute('SELECT id, severity, reason_code, alert_status FROM Alerts').fetchall()
tele = conn.execute('SELECT COUNT(*) FROM Telemetry').fetchone()
print(f'Telemetry rows: {tele[0]}')
print(f'Alerts stored: {len(alerts)}')
for a in alerts:
    print(f'  [{a[1]}] {a[2]} | status={a[3]}')
conn.close()
"
```

Change `database.enabled` back to `false` when done testing so it does not slow down regular test runs.

---

## Checklist — Phase 3 Complete When:

- [ ] `guardian/db.py` exists with `GuardianDB` class and all 10 methods
- [ ] `guardian/db.py` defines `DB_SCHEMA` with all 4 `CREATE TABLE` statements
- [ ] `tests/test_db.py` exists with all tests passing
- [ ] `guardian/engine.py` accepts optional `db=None` parameter in `__init__()`
- [ ] `guardian/engine.py` `process_row()` calls `db.insert_telemetry()` and `db.insert_alert()` when db is not None
- [ ] `guardian/run_pipeline.py` instantiates `GuardianDB` when `database.enabled: true`
- [ ] Setting `database.enabled: true` and running a scenario creates `results/guardian.db` with data
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
guardian/
├── db.py                        ← NEW — GuardianDB class + DB_SCHEMA
├── engine.py                    ← MODIFIED — db parameter, insert calls
└── run_pipeline.py              ← MODIFIED — instantiates GuardianDB

tests/
└── test_db.py                   ← NEW — all CRUD tests

results/
└── guardian.db                  ← GENERATED at runtime when enabled
```

---

## Proceed to Phase 4 →

Phase 4 makes the ML model generate real structured alerts — the same `build_alert()` dicts that the database and exporter already handle. Since the database is now in place, ML alerts will be automatically persisted.
