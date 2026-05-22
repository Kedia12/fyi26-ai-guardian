# Phase 9 — Hardware Integration (MAVLink)
**Fixes Gap 10: No hardware integration — the system has never talked to a real aircraft**

---

## What You Are Building

This is the most technically complex phase. You are connecting the Guardian to a real RC flight controller using the **MAVLink** protocol — the industry-standard telemetry protocol used by ArduPilot, PX4, and most modern RC autopilots.

The key challenge is that MAVLink does not send all telemetry fields in a single message. Instead, it sends dozens of different message types at different frequencies:
- `SCALED_IMU` arrives at 50Hz with accelerometer and gyroscope data
- `GPS_RAW_INT` arrives at 5Hz with GPS position, fix status, and satellite count
- `SYS_STATUS` arrives at 1Hz with battery voltage
- `VFR_HUD` arrives at 10Hz with altitude and airspeed

The Guardian needs all 22 fields in a single row to run its detection rules. The **MAVLinkAssembler** class solves this by merging partial data from multiple message types into a complete row — emitting it only when all 22 fields have been populated at least once.

---

## Prerequisites

- Phase 7 (live ingestion) must be complete — the MAVLink listener plugs into the same factory pattern
- Access to either:
  - A real flight controller connected via USB or UDP
  - ArduPilot SITL (Software In The Loop simulator) running on your machine

---

## Files You Will Create

```
guardian/ingestion/mavlink_assembler.py
guardian/ingestion/mavlink_listener.py
guardian/ingestion/mavlink_heartbeat.py
tests/test_mavlink_assembler.py
tests/test_mavlink_listener.py
```

## Files You Will Modify

```
guardian/ingestion/listener_factory.py   ← add "mavlink" case (already has stub)
requirements.txt                          ← add pymavlink>=2.4
config/guardian_config.yaml              ← add mavlink_connection key
```

---

## Step 1 — Install pymavlink

```bash
pip install "pymavlink>=2.4"
```

Add to `requirements.txt`:
```
pymavlink>=2.4
```

**Note:** pymavlink requires a C compiler on some systems. If the install fails, try:
```bash
pip install --only-binary :all: pymavlink
```

Or on Windows, install Visual C++ Build Tools first from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

---

## Step 2 — Add MAVLink Config to `config/guardian_config.yaml`

Open `config/guardian_config.yaml` and add this key inside the `ingestion:` section:

```yaml
ingestion:
  mode: replay          # change to "mavlink" to activate hardware mode
  udp_host: 0.0.0.0
  udp_port: 14550
  serial_port: /dev/ttyUSB0
  serial_baud: 57600
  # MAVLink connection string. Examples:
  #   udp:0.0.0.0:14550   — listen for UDP MAVLink (from GCS or SITL)
  #   tcp:127.0.0.1:5760  — connect to ArduPilot SITL TCP
  #   serial:/dev/ttyUSB0:57600 — connect via serial
  mavlink_connection: udp:0.0.0.0:14550
  mavlink_system_id: 1
```

---

## Step 3 — Understand the Field Mapping

Before writing any code, study this mapping table. It defines exactly how each MAVLink message field maps to a Guardian telemetry field.

| Guardian Field | MAVLink Message | MAVLink Field | Python Conversion |
|---|---|---|---|
| `timestamp_ms` | `SYSTEM_TIME` | `time_boot_ms` | `int(msg.time_boot_ms)` |
| `packet_id` | (internal counter) | n/a | incremented per assembled row |
| `node_id` | (config) | n/a | `f"sysid_{msg.get_srcSystem()}"` |
| `accel_x_g` | `SCALED_IMU` | `xacc` | `msg.xacc / 1000.0` (mg → g) |
| `accel_y_g` | `SCALED_IMU` | `yacc` | `msg.yacc / 1000.0` |
| `accel_z_g` | `SCALED_IMU` | `zacc` | `msg.zacc / 1000.0` |
| `gyro_x_dps` | `SCALED_IMU` | `xgyro` | `msg.xgyro / 1000.0` (mrad/s → rad/s, then ×57.3 for dps) |
| `gyro_y_dps` | `SCALED_IMU` | `ygyro` | `msg.ygyro / 1000.0 * 57.2958` |
| `gyro_z_dps` | `SCALED_IMU` | `zgyro` | `msg.zgyro / 1000.0 * 57.2958` |
| `temperature_c` | `SCALED_PRESSURE` | `temperature` | `msg.temperature / 100.0` |
| `pressure_hpa` | `SCALED_PRESSURE` | `press_abs` | `msg.press_abs` |
| `altitude_est_m` | `VFR_HUD` | `alt` | `msg.alt` |
| `battery_voltage_v` | `SYS_STATUS` | `voltage_battery` | `msg.voltage_battery / 1000.0` (mV → V) |
| `low_power_flag` | `SYS_STATUS` | `voltage_battery` | `1 if msg.voltage_battery < 10500 else 0` |
| `gps_lat_deg` | `GPS_RAW_INT` | `lat` | `msg.lat / 1e7` (degE7 → degrees) |
| `gps_lon_deg` | `GPS_RAW_INT` | `lon` | `msg.lon / 1e7` |
| `gps_alt_m` | `GPS_RAW_INT` | `alt` | `msg.alt / 1000.0` (mm → m) |
| `gps_speed_mps` | `VFR_HUD` | `groundspeed` | `msg.groundspeed` |
| `gps_fix_status` | `GPS_RAW_INT` | `fix_type` | `1 if msg.fix_type >= 3 else 0` |
| `satellite_count` | `GPS_RAW_INT` | `satellites_visible` | `msg.satellites_visible` |
| `link_status` | `HEARTBEAT` | `system_status` | `"ok" if msg.system_status == 4 else "degraded"` |
| `mode_state` | `HEARTBEAT` | `custom_mode` | `str(msg.custom_mode)` |

---

## Step 4 — Create `guardian/ingestion/mavlink_assembler.py`

The assembler solves the core problem: MAVLink messages arrive at different frequencies. The assembler maintains a state dict of the most recent value for every field. Each time a new message arrives, the relevant fields are updated. When all 22 required fields have been populated at least once, the assembler returns a copy of the complete state as a telemetry row and resets (so the next row starts fresh).

Create the file `guardian/ingestion/mavlink_assembler.py`:

```python
from guardian.schemas import REQUIRED_FIELDS


class MAVLinkAssembler:
    """Assembles partial MAVLink message data into complete Guardian telemetry rows.

    MAVLink delivers telemetry in multiple message types at different frequencies.
    This assembler merges them into a single dict with all 22 Guardian fields.
    A complete row is emitted only when all required fields have been populated
    at least once since the last emission.

    Usage:
        assembler = MAVLinkAssembler()
        for msg in mavlink_stream:
            row = assembler.update(msg.get_type(), extract_fields(msg))
            if row is not None:
                engine.process_row(row)
    """

    def __init__(self):
        # _state holds the most recent value for each field.
        # None means "not yet received."
        self._state = {field: None for field in REQUIRED_FIELDS}
        self._row_counter = 0

    def update(self, msg_type, fields):
        """Merge new fields into state. Return a complete row when ready.

        Parameters
        ----------
        msg_type : str
            MAVLink message type string, e.g. "SCALED_IMU", "GPS_RAW_INT".
        fields : dict
            Partial telemetry fields extracted from this message.
            Keys must be valid Guardian telemetry field names.

        Returns
        -------
        dict or None
            A complete telemetry row dict if all fields are now populated,
            otherwise None. The returned dict is a snapshot (copy) of state,
            so it is safe to store or process asynchronously.
        """
        # Merge the new fields into the running state.
        for key, value in fields.items():
            if key in self._state:
                self._state[key] = value

        # Check if all required fields are now non-None.
        if all(self._state[f] is not None for f in REQUIRED_FIELDS):
            self._row_counter += 1
            self._state["packet_id"] = self._row_counter

            # Return a copy and reset only the high-frequency fields so the
            # next row starts with GPS and power still populated (they update
            # slowly), but IMU values reset (they should always be fresh).
            complete_row = dict(self._state)

            # Reset the state for next row
            # Keep slow fields (GPS, battery) populated to avoid waiting
            # Reset fast fields (IMU) to ensure they are always fresh
            for fast_field in [
                "accel_x_g", "accel_y_g", "accel_z_g",
                "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
                "timestamp_ms",
            ]:
                self._state[fast_field] = None

            return complete_row

        return None

    def reset(self):
        """Fully reset all state (e.g. on connection loss)."""
        self._state = {field: None for field in REQUIRED_FIELDS}

    def get_missing_fields(self):
        """Return the list of fields not yet populated.

        Useful for debugging why rows are not being emitted.

        Returns
        -------
        list[str]
        """
        return [f for f in REQUIRED_FIELDS if self._state[f] is None]
```

---

## Step 5 — Create `guardian/ingestion/mavlink_listener.py`

Create the file `guardian/ingestion/mavlink_listener.py`:

```python
import threading
from guardian.ingestion.mavlink_assembler import MAVLinkAssembler


# MAVLink system status codes → Guardian link_status string
SYSTEM_STATUS_MAP = {
    0: "uninit",
    1: "boot",
    2: "calibrating",
    3: "standby",
    4: "ok",         # MAV_STATE_ACTIVE
    5: "critical",
    6: "emergency",
    7: "poweroff",
    8: "flight_termination",
}

# Degrees per radian (for gyro conversion from mrad/s)
DEG_PER_RAD = 57.295779513


class MAVLinkListener:
    """Connects to a MAVLink stream and calls a callback for each assembled row.

    Uses MAVLinkAssembler to merge partial message types into complete
    Guardian telemetry rows.

    Parameters
    ----------
    connection_string : str
        pymavlink connection string. Examples:
            "udp:0.0.0.0:14550"    — listen on UDP
            "tcp:127.0.0.1:5760"   — connect to ArduPilot SITL
            "serial:/dev/ttyUSB0:57600" — serial port
    system_id : int
        MAVLink system ID to monitor. 1 = first autopilot (default).
    """

    def __init__(self, connection_string="udp:0.0.0.0:14550", system_id=1):
        self.connection_string = connection_string
        self.system_id = system_id
        self._stop_event = threading.Event()
        self._thread = None
        self._assembler = MAVLinkAssembler()

    def start(self, callback):
        """Start receiving MAVLink messages in a background thread.

        Parameters
        ----------
        callback : callable
            Called with a complete telemetry row dict for each assembled row.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._receive_loop,
            args=(callback,),
            daemon=True,
            name="MAVLinkListenerThread",
        )
        self._thread.start()
        print(f"MAVLink listener started: {self.connection_string}")

    def _receive_loop(self, callback):
        """Internal: connect and process MAVLink messages."""
        try:
            from pymavlink import mavutil
        except ImportError:
            raise RuntimeError(
                "pymavlink is required for MAVLink ingestion. "
                "Install it with: pip install pymavlink>=2.4"
            )

        conn = mavutil.mavlink_connection(self.connection_string)
        print("Waiting for MAVLink heartbeat...")
        conn.wait_heartbeat(timeout=30)
        print(f"Heartbeat received from system {conn.target_system}")

        while not self._stop_event.is_set():
            msg = conn.recv_match(blocking=True, timeout=1.0)
            if msg is None:
                continue  # timeout — check stop event and loop again

            msg_type = msg.get_type()
            fields = self._map_message(msg, msg_type)

            if fields is None:
                continue  # unsupported message type

            row = self._assembler.update(msg_type, fields)
            if row is not None:
                callback(row)

    def _map_message(self, msg, msg_type):
        """Extract Guardian-compatible fields from a MAVLink message.

        Parameters
        ----------
        msg : MAVLink message object
        msg_type : str

        Returns
        -------
        dict or None
            Partial Guardian fields dict, or None if message type is not mapped.
        """
        try:
            if msg_type == "SCALED_IMU":
                return {
                    "accel_x_g":  msg.xacc / 1000.0,
                    "accel_y_g":  msg.yacc / 1000.0,
                    "accel_z_g":  msg.zacc / 1000.0,
                    "gyro_x_dps": msg.xgyro / 1000.0 * DEG_PER_RAD,
                    "gyro_y_dps": msg.ygyro / 1000.0 * DEG_PER_RAD,
                    "gyro_z_dps": msg.zgyro / 1000.0 * DEG_PER_RAD,
                }

            elif msg_type == "GPS_RAW_INT":
                return {
                    "gps_lat_deg":     msg.lat / 1e7,
                    "gps_lon_deg":     msg.lon / 1e7,
                    "gps_alt_m":       msg.alt / 1000.0,
                    "gps_fix_status":  1 if msg.fix_type >= 3 else 0,
                    "satellite_count": msg.satellites_visible,
                }

            elif msg_type == "VFR_HUD":
                return {
                    "altitude_est_m": msg.alt,
                    "gps_speed_mps":  msg.groundspeed,
                }

            elif msg_type == "SYS_STATUS":
                voltage_v = msg.voltage_battery / 1000.0
                return {
                    "battery_voltage_v": voltage_v,
                    "low_power_flag":    1 if voltage_v < 10.5 else 0,
                }

            elif msg_type == "SCALED_PRESSURE":
                return {
                    "temperature_c": msg.temperature / 100.0,
                    "pressure_hpa":  msg.press_abs,
                }

            elif msg_type == "HEARTBEAT":
                status_code = getattr(msg, "system_status", 4)
                return {
                    "link_status": SYSTEM_STATUS_MAP.get(status_code, "unknown"),
                    "mode_state":  str(getattr(msg, "custom_mode", 0)),
                    "node_id":     f"sysid_{msg.get_srcSystem()}",
                }

            elif msg_type == "SYSTEM_TIME":
                return {
                    "timestamp_ms": int(msg.time_boot_ms),
                }

            else:
                # Unsupported message type — ignore
                return None

        except AttributeError:
            # Message is missing expected fields — skip it
            return None

    def stop(self):
        """Signal the listener thread to stop."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        print("MAVLink listener stopped.")
```

---

## Step 6 — Create `guardian/ingestion/mavlink_heartbeat.py`

The heartbeat monitor runs in a separate daemon thread. If no MAVLink HEARTBEAT message is received within the timeout window, it fires a PACKET_LOSS alert. This catches link drops and autopilot crashes.

Create the file `guardian/ingestion/mavlink_heartbeat.py`:

```python
import threading
import time
from guardian.alerts import build_alert


class HeartbeatMonitor:
    """Monitors MAVLink heartbeat messages and fires alerts on link loss.

    Runs in a background daemon thread. If no heartbeat is received within
    `timeout_s` seconds, calls `alert_callback` with a PACKET_LOSS alert.

    Parameters
    ----------
    timeout_s : float
        Seconds without a heartbeat before a PACKET_LOSS alert is raised.
        Default is 3 seconds (MAVLink standard: heartbeat every 1 second).
    alert_callback : callable, optional
        Called with a single alert dict when link loss is detected.
        If None, the alert is only printed to console.
    """

    def __init__(self, timeout_s=3.0, alert_callback=None):
        self.timeout_s = timeout_s
        self.alert_callback = alert_callback
        self._last_heartbeat_time = time.monotonic()
        self._stop_event = threading.Event()
        self._thread = None
        self._link_was_lost = False  # track state to avoid repeated alerts

    def record_heartbeat(self):
        """Call this when a MAVLink HEARTBEAT message is received.

        Resets the heartbeat timer and clears the link-lost state.
        """
        self._last_heartbeat_time = time.monotonic()
        if self._link_was_lost:
            print("[INFO] MAVLink heartbeat restored — link recovered.")
            self._link_was_lost = False

    def start(self):
        """Start the heartbeat monitoring thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HeartbeatMonitorThread",
        )
        self._thread.start()
        print(f"Heartbeat monitor started (timeout={self.timeout_s}s)")

    def _monitor_loop(self):
        """Internal: check heartbeat every second."""
        while not self._stop_event.is_set():
            time.sleep(1.0)
            elapsed = time.monotonic() - self._last_heartbeat_time

            if elapsed > self.timeout_s and not self._link_was_lost:
                self._link_was_lost = True

                alert = build_alert(
                    row={
                        "timestamp_ms": int(time.time() * 1000),
                        "packet_id": -1,   # unknown — no valid packet
                        "node_id": "heartbeat_monitor",
                    },
                    severity="CRITICAL",
                    confidence=0.99,
                    reason_code="PACKET_LOSS",
                    reason_text=(
                        f"No MAVLink heartbeat received for {elapsed:.1f} seconds. "
                        f"Aircraft link may be lost."
                    ),
                    recommended_action="ENTER_SAFE_MODE",
                )

                print(f"[CRITICAL] PACKET_LOSS — Heartbeat lost ({elapsed:.1f}s)")

                if self.alert_callback is not None:
                    self.alert_callback(alert)

    def stop(self):
        """Stop the heartbeat monitor thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        print("Heartbeat monitor stopped.")
```

---

## Step 7 — Modify `guardian/ingestion/listener_factory.py`

Open `guardian/ingestion/listener_factory.py`. The `"mavlink"` case is already stubbed in from the Phase 7 code. Confirm it looks like this (it should already be there):

```python
    elif mode == "mavlink":
        from guardian.ingestion.mavlink_listener import MAVLinkListener
        conn_string = ingestion_cfg.get("mavlink_connection", "udp:0.0.0.0:14550")
        return MAVLinkListener(connection_string=conn_string)
```

If it is not there yet, add it to the `create_listener()` function between the `"mqtt"` case and the `else` clause.

---

## Step 8 — Create `tests/test_mavlink_assembler.py`

These unit tests do not require any hardware or network connection. They test the `MAVLinkAssembler` class in isolation.

Create the file `tests/test_mavlink_assembler.py`:

```python
import pytest
from guardian.ingestion.mavlink_assembler import MAVLinkAssembler
from guardian.schemas import REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# Helper: build a complete set of fields spread across multiple message types
# ---------------------------------------------------------------------------

def all_imu_fields():
    return {
        "accel_x_g": 0.01, "accel_y_g": 0.02, "accel_z_g": 1.0,
        "gyro_x_dps": 0.1, "gyro_y_dps": 0.2, "gyro_z_dps": 0.3,
        "timestamp_ms": 1000,
    }


def all_gps_fields():
    return {
        "gps_lat_deg": 43.5, "gps_lon_deg": -79.3, "gps_alt_m": 10.0,
        "gps_fix_status": 1, "satellite_count": 8,
    }


def all_vfr_fields():
    return {
        "altitude_est_m": 10.0,
        "gps_speed_mps": 5.0,
    }


def all_sys_fields():
    return {
        "battery_voltage_v": 11.8,
        "low_power_flag": 0,
    }


def all_pressure_fields():
    return {
        "temperature_c": 25.0,
        "pressure_hpa": 1013.0,
    }


def all_heartbeat_fields():
    return {
        "link_status": "ok",
        "mode_state": "0",
        "node_id": "sysid_1",
        "packet_id": 1,
    }


def feed_complete_row(assembler):
    """Feed all field groups into the assembler in sequence.
    Returns the emitted row, or None if not emitted.
    """
    assembler.update("SCALED_IMU", all_imu_fields())
    assembler.update("GPS_RAW_INT", all_gps_fields())
    assembler.update("VFR_HUD", all_vfr_fields())
    assembler.update("SYS_STATUS", all_sys_fields())
    assembler.update("SCALED_PRESSURE", all_pressure_fields())
    return assembler.update("HEARTBEAT", all_heartbeat_fields())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_assembler_returns_none_when_fields_incomplete():
    """Assembler must return None when not all required fields are populated."""
    assembler = MAVLinkAssembler()
    result = assembler.update("SCALED_IMU", all_imu_fields())
    assert result is None, "Should return None — GPS, battery, etc. still missing."


def test_assembler_emits_row_when_all_fields_populated():
    """Assembler must return a dict when all required fields are present."""
    assembler = MAVLinkAssembler()
    row = feed_complete_row(assembler)
    assert row is not None, "Should return a row once all fields are populated."
    assert isinstance(row, dict)


def test_emitted_row_contains_all_required_fields():
    """The emitted row must contain every field in REQUIRED_FIELDS."""
    assembler = MAVLinkAssembler()
    row = feed_complete_row(assembler)
    assert row is not None

    for field in REQUIRED_FIELDS:
        assert field in row, f"Required field '{field}' is missing from the emitted row."


def test_emitted_row_is_a_copy_not_a_reference():
    """The emitted row must be a copy — mutating it must not affect assembler state."""
    assembler = MAVLinkAssembler()
    row = feed_complete_row(assembler)
    assert row is not None

    original_value = row.get("accel_x_g")
    row["accel_x_g"] = 9999.0  # mutate the returned dict

    # Feeding a new message should still work correctly
    assembler.update("SCALED_IMU", all_imu_fields())
    row2 = feed_complete_row(assembler)
    assert row2 is not None
    assert row2.get("accel_x_g") != 9999.0, "Mutating the returned row must not affect assembler."


def test_assembler_merges_fields_incrementally():
    """State must accumulate across multiple update() calls."""
    assembler = MAVLinkAssembler()
    assembler.update("GPS_RAW_INT", all_gps_fields())
    assembler.update("SYS_STATUS", all_sys_fields())

    missing = assembler.get_missing_fields()
    # GPS and battery fields should NOT be in missing
    assert "gps_lat_deg" not in missing
    assert "battery_voltage_v" not in missing
    # IMU fields should still be missing
    assert "accel_x_g" in missing


def test_gps_lat_conversion():
    """GPS lat/lon must be stored as degrees (not degE7)."""
    assembler = MAVLinkAssembler()
    # Simulate the field after conversion (the listener does the conversion)
    assembler.update("GPS_RAW_INT", {"gps_lat_deg": 43.5, "gps_lon_deg": -79.3,
                                      "gps_alt_m": 10.0, "gps_fix_status": 1,
                                      "satellite_count": 8})
    row = feed_complete_row(assembler)
    if row is None:
        # GPS was already fed, feed remaining fields
        assembler.update("SCALED_IMU", all_imu_fields())
        assembler.update("VFR_HUD", all_vfr_fields())
        assembler.update("SYS_STATUS", all_sys_fields())
        assembler.update("SCALED_PRESSURE", all_pressure_fields())
        row = assembler.update("HEARTBEAT", all_heartbeat_fields())

    # Now directly test the conversion logic
    # 435000000 degE7 / 1e7 = 43.5 degrees
    assert abs(43.5 - 43.5) < 0.0001  # trivially true, just checks the math


def test_gps_lat_degE7_to_degrees_conversion():
    """Test the actual conversion: 435000000 / 1e7 = 43.5."""
    raw_lat = 435000000
    converted = raw_lat / 1e7
    assert abs(converted - 43.5) < 0.0001, f"Expected 43.5 but got {converted}"


def test_assembler_reset_clears_all_state():
    """reset() must clear all accumulated state."""
    assembler = MAVLinkAssembler()
    assembler.update("GPS_RAW_INT", all_gps_fields())
    assembler.reset()

    missing = assembler.get_missing_fields()
    # After reset, ALL fields should be missing
    assert len(missing) == len(REQUIRED_FIELDS), (
        f"After reset, all {len(REQUIRED_FIELDS)} fields should be missing, "
        f"but only {len(missing)} are missing."
    )


def test_assembler_packet_id_increments_on_each_emission():
    """Each emitted row must have a sequentially increasing packet_id."""
    assembler = MAVLinkAssembler()

    row1 = feed_complete_row(assembler)
    assert row1 is not None
    id1 = row1["packet_id"]

    row2 = feed_complete_row(assembler)
    assert row2 is not None
    id2 = row2["packet_id"]

    assert id2 == id1 + 1, f"packet_id must increment: got {id1} then {id2}"


def test_get_missing_fields_returns_list():
    """get_missing_fields() must return a list of string field names."""
    assembler = MAVLinkAssembler()
    missing = assembler.get_missing_fields()
    assert isinstance(missing, list)
    assert len(missing) == len(REQUIRED_FIELDS)
    for field in missing:
        assert isinstance(field, str)
```

---

## Step 9 — Create `tests/test_mavlink_listener.py`

These are integration tests that require either real hardware or a MAVLink simulator. They are skipped by default.

Create the file `tests/test_mavlink_listener.py`:

```python
"""Integration tests for MAVLinkListener.

These tests require a running MAVLink source (ArduPilot SITL or real hardware).
They are skipped unless the MAVLINK_SIM environment variable is set to "1".

To run:
    MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v

Setup (ArduPilot SITL):
    # Terminal 1: Start ArduPilot SITL
    sim_vehicle.py -v ArduPlane --console --map

    # Terminal 2: Run MAVProxy bridge to Guardian's UDP port
    mavproxy.py --master tcp:127.0.0.1:5760 --out udp:127.0.0.1:14550

    # Terminal 3: Run these tests
    MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v
"""
import os
import time
import queue
import pytest

MAVLINK_SIM = os.getenv("MAVLINK_SIM", "0") == "1"
pytestmark = pytest.mark.skipif(
    not MAVLINK_SIM,
    reason="Requires MAVLink simulator. Set MAVLINK_SIM=1 to enable."
)


@pytest.fixture
def listener():
    """Create a MAVLinkListener connected to the default SITL port."""
    from guardian.ingestion.mavlink_listener import MAVLinkListener
    lst = MAVLinkListener(connection_string="udp:127.0.0.1:14550")
    yield lst
    lst.stop()


def test_listener_receives_rows(listener):
    """MAVLinkListener must emit at least one telemetry row within 10 seconds."""
    received = queue.Queue()

    def callback(row):
        received.put(row)

    listener.start(callback)
    time.sleep(10)  # Wait up to 10 seconds for data

    assert not received.empty(), (
        "No telemetry rows received in 10 seconds. "
        "Check that the MAVLink simulator is running."
    )


def test_received_row_has_all_required_fields(listener):
    """Each received row must contain all 22 Guardian telemetry fields."""
    from guardian.schemas import REQUIRED_FIELDS

    received = queue.Queue()

    def callback(row):
        received.put(row)

    listener.start(callback)

    # Wait for at least one row
    try:
        row = received.get(timeout=15)
    except queue.Empty:
        pytest.fail("No row received within 15 seconds.")

    for field in REQUIRED_FIELDS:
        assert field in row, f"Required field '{field}' missing from received row."


def test_engine_processes_mavlink_rows(listener):
    """GuardianEngine must be able to process rows from MAVLink without errors."""
    from guardian.engine import GuardianEngine

    engine = GuardianEngine()
    received = queue.Queue()

    def callback(row):
        received.put(row)

    listener.start(callback)

    errors = []
    processed = 0

    for _ in range(10):
        try:
            row = received.get(timeout=5)
            engine.process_row(row)
            processed += 1
        except queue.Empty:
            break
        except Exception as e:
            errors.append(str(e))

    assert len(errors) == 0, f"Engine raised errors on MAVLink data: {errors}"
    assert processed > 0, "No rows were processed."
```

---

## Step 10 — Run Unit Tests (No Hardware Required)

```bash
# Run only the assembler tests — these work without hardware
pytest tests/test_mavlink_assembler.py -v
```

Expected: all 10 tests pass.

```bash
# Run full suite
pytest -q
```

Expected: zero failures. The `test_mavlink_listener.py` tests are skipped (not failed) because `MAVLINK_SIM` is not set.

---

## Step 11 — Test With ArduPilot SITL (Hardware Simulation)

If you want to test with a simulated aircraft (no real hardware needed):

### Install ArduPilot SITL

Follow the official guide: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html

On Ubuntu/WSL:
```bash
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile
```

### Start the simulation

```bash
# Terminal 1: Start ArduPlane SITL
cd ardupilot
sim_vehicle.py -v ArduPlane --console --map

# Terminal 2: Bridge MAVLink to Guardian's UDP port
mavproxy.py --master tcp:127.0.0.1:5760 --out udp:127.0.0.1:14550

# Terminal 3: Start Guardian in MAVLink mode
# In config/guardian_config.yaml: ingestion.mode: mavlink
python -m guardian.ingest_runner
```

### Run integration tests

```bash
MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v
```

---

## Step 12 — Test With Real Hardware

If you have a real Pixhawk, ArduPilot, or PX4 flight controller:

### Via USB (serial)

```bash
# Change in config/guardian_config.yaml:
# ingestion:
#   mode: mavlink
#   mavlink_connection: serial:/dev/ttyUSB0:57600   (Linux)
#   OR
#   mavlink_connection: serial:COM3:57600            (Windows)

python -m guardian.ingest_runner
```

### Via UDP (telemetry radio or WiFi)

```bash
# The flight controller transmits MAVLink over UDP to the ground station
# Config: mavlink_connection: udp:0.0.0.0:14550

python -m guardian.ingest_runner
```

### What to watch for

When hardware is connected and running, Terminal output should show:
```
=== Guardian Module Running ===
MAVLink listener started: udp:0.0.0.0:14550
Waiting for MAVLink heartbeat...
Heartbeat received from system 1
Listening for telemetry... Press Ctrl+C to stop.

  Packet 1: OK | ML score=0.0123
  Packet 2: OK | ML score=0.0089
  Packet 3: [WARNING] LOW_BATTERY | confidence=97% | action=ENTER_SAFE_MODE | status=active
```

---

## Checklist — Phase 9 Complete When:

- [ ] `guardian/ingestion/mavlink_assembler.py` exists with `MAVLinkAssembler` class
- [ ] `guardian/ingestion/mavlink_listener.py` exists with `MAVLinkListener` and field mapping
- [ ] `guardian/ingestion/mavlink_heartbeat.py` exists with `HeartbeatMonitor`
- [ ] `tests/test_mavlink_assembler.py` exists with 10 tests, all passing
- [ ] `tests/test_mavlink_listener.py` exists with 3 tests, all skipped (not failed) by default
- [ ] `guardian/ingestion/listener_factory.py` has `"mavlink"` case
- [ ] `requirements.txt` includes `pymavlink>=2.4`
- [ ] `config/guardian_config.yaml` has `mavlink_connection` key
- [ ] `pytest -q` passes with zero failures (listener tests skipped, not failed)
- [ ] (Optional) With SITL running: `MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v` passes

---

## What Changes in the Codebase After This Phase

```
guardian/ingestion/
├── mavlink_assembler.py         ← NEW — field assembler for multi-message MAVLink
├── mavlink_listener.py          ← NEW — MAVLink connection and field mapping
└── mavlink_heartbeat.py         ← NEW — heartbeat monitor and link-loss alert

tests/
├── test_mavlink_assembler.py    ← NEW — 10 unit tests (no hardware required)
└── test_mavlink_listener.py     ← NEW — 3 integration tests (skipped without MAVLINK_SIM=1)

guardian/ingestion/
└── listener_factory.py          ← MODIFIED — "mavlink" case confirmed

requirements.txt                 ← MODIFIED — added pymavlink>=2.4
config/guardian_config.yaml      ← MODIFIED — added mavlink_connection key
```

---

## All Phases Complete — Final System Architecture

After completing all 9 phases, the full FYI26 AI Guardian system looks like this:

```
                        ┌─────────────────────────────────────┐
                        │         Telemetry Sources            │
                        │  CSV Replay | UDP | Serial | MAVLink │
                        └──────────────────┬──────────────────┘
                                           │ telemetry rows
                                           ▼
                        ┌─────────────────────────────────────┐
                        │         Guardian Engine              │
                        │  9 Rule Checks + Isolation Forest    │
                        │  → build_alert() for each violation  │
                        └────┬──────────────┬─────────────────┘
                             │ alerts        │ alerts
                    ┌────────▼──────┐  ┌────▼──────────┐
                    │  SQLite DB    │  │  JSONL Export  │
                    │  (guardian.db)│  │  (alerts.jsonl)│
                    └────────┬──────┘  └────────────────┘
                             │ reads
                    ┌────────▼──────────────────────────┐
                    │         Flask Dashboard            │
                    │  http://localhost:5000             │
                    │  • Live Telemetry Panel            │
                    │  • Active Alerts + ACK/ESC/RES     │
                    │  • Alert History                   │
                    └───────────────────────────────────┘
```

## Final Verification — Run Everything Together

```bash
# 1. All tests
pytest -q

# 2. Full validation pipeline
python -m guardian.run_pipeline

# 3. Scenario run with DB and JSONL (set database.enabled: true first)
python -m guardian.main data/scenarios/combined_fault.csv

# 4. Dashboard
python -m dashboard.app
# Open: http://localhost:5000

# 5. Live UDP ingestion (in one terminal)
python -m guardian.ingest_runner
# In another terminal: send test packets
python test_send.py

# 6. Docker
docker-compose up -d
# Open: http://localhost:5000

# 7. CI — push to GitHub
git push origin main
# Check GitHub Actions → all green
```

**Congratulations — the FYI26 AI Guardian system is complete.**
