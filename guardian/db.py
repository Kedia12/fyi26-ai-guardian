import sqlite3
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS Telemetry (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_ms        INTEGER,
    packet_id           INTEGER,
    node_id             TEXT,
    accel_x_g           REAL,
    accel_y_g           REAL,
    accel_z_g           REAL,
    gyro_x_dps          REAL,
    gyro_y_dps          REAL,
    gyro_z_dps          REAL,
    altitude_est_m      REAL,
    gps_lat_deg         REAL,
    gps_lon_deg         REAL,
    gps_speed_mps       REAL,
    satellite_count     INTEGER,
    gps_fix_status      INTEGER,
    battery_voltage_v   REAL,
    low_power_flag      INTEGER,
    temperature_c       REAL,
    pressure_hpa        REAL,
    ml_anomaly_score    REAL,
    inserted_at         TEXT
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
    confirmed           INTEGER NOT NULL DEFAULT 0,
    ml_source           INTEGER DEFAULT 0,
    inserted_at         TEXT
);

CREATE TABLE IF NOT EXISTS Operator_Actions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id            INTEGER,
    action_type         TEXT,
    operator_note       TEXT,
    acted_at            TEXT,
    FOREIGN KEY (alert_id) REFERENCES Alerts(id)
);

CREATE TABLE IF NOT EXISTS Validation_Metrics (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario            TEXT,
    total_rows          INTEGER,
    total_alerts        INTEGER,
    rule_alerts         INTEGER,
    ml_alerts           INTEGER,
    recorded_at         TEXT
);
"""


class GuardianDB:
    def __init__(self, path):
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(resolved), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self):
        existing = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(Alerts)").fetchall()
        }
        if "confirmed" not in existing:
            self._conn.execute(
                "ALTER TABLE Alerts ADD COLUMN confirmed INTEGER NOT NULL DEFAULT 0"
            )

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def insert_telemetry(self, row):
        cols = [
            "timestamp_ms", "packet_id", "node_id",
            "accel_x_g", "accel_y_g", "accel_z_g",
            "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
            "altitude_est_m", "gps_lat_deg", "gps_lon_deg",
            "gps_speed_mps", "satellite_count", "gps_fix_status",
            "battery_voltage_v", "low_power_flag",
            "temperature_c", "pressure_hpa", "ml_anomaly_score",
        ]
        values = [row.get(c) for c in cols]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        cur = self._conn.execute(
            f"INSERT INTO Telemetry ({col_names}, inserted_at) VALUES ({placeholders}, ?)",
            values + [self._now()],
        )
        self._conn.commit()
        return cur.lastrowid

    def insert_alert(self, alert, ml_source=False):
        cols = [
            "timestamp_ms", "packet_id", "node_id",
            "severity", "confidence", "reason_code",
            "reason_text", "recommended_action", "alert_status",
        ]
        values = [alert.get(c) for c in cols]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        cur = self._conn.execute(
            f"INSERT INTO Alerts ({col_names}, ml_source, inserted_at) "
            f"VALUES ({placeholders}, ?, ?)",
            values + [int(ml_source), self._now()],
        )
        self._conn.commit()
        return cur.lastrowid

    def insert_operator_action(self, action):
        cur = self._conn.execute(
            "INSERT INTO Operator_Actions (alert_id, action_type, operator_note, acted_at) "
            "VALUES (?, ?, ?, ?)",
            [
                action.get("alert_id"),
                action.get("action_type"),
                action.get("operator_note", ""),
                self._now(),
            ],
        )
        self._conn.commit()
        return cur.lastrowid

    def update_alert_status(self, alert_id, new_status):
        self._conn.execute(
            "UPDATE Alerts SET alert_status = ? WHERE id = ?",
            [new_status, alert_id],
        )
        self._conn.commit()

    def update_alert_confirmed(self, alert_id, confirmed: bool):
        self._conn.execute(
            "UPDATE Alerts SET confirmed = ? WHERE id = ?",
            [int(confirmed), alert_id],
        )
        self._conn.commit()

    def get_recent_alerts(self, limit=50):
        cur = self._conn.execute(
            "SELECT * FROM Alerts ORDER BY id DESC LIMIT ?", [limit]
        )
        return [dict(row) for row in cur.fetchall()]

    def get_recent_telemetry(self, limit=1):
        cur = self._conn.execute(
            "SELECT * FROM Telemetry ORDER BY id DESC LIMIT ?", [limit]
        )
        return [dict(row) for row in cur.fetchall()]

    def get_alert_by_id(self, alert_id):
        cur = self._conn.execute(
            "SELECT * FROM Alerts WHERE id = ?", [alert_id]
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_aircraft_positions(self):
        cur = self._conn.execute("""
            SELECT t.* FROM Telemetry t
            INNER JOIN (
                SELECT node_id, MAX(id) AS max_id FROM Telemetry GROUP BY node_id
            ) latest ON t.id = latest.max_id
            WHERE t.gps_lat_deg IS NOT NULL AND t.gps_lon_deg IS NOT NULL
            ORDER BY t.node_id
        """)
        return [dict(row) for row in cur.fetchall()]

    def get_flight_trail(self, node_id, limit=100):
        cur = self._conn.execute("""
            SELECT timestamp_ms, gps_lat_deg, gps_lon_deg, altitude_est_m,
                   gps_speed_mps, gps_fix_status
            FROM Telemetry
            WHERE node_id = ? AND gps_lat_deg IS NOT NULL AND gps_lon_deg IS NOT NULL
            ORDER BY id DESC LIMIT ?
        """, [node_id, limit])
        rows = [dict(row) for row in cur.fetchall()]
        rows.reverse()
        return rows

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
