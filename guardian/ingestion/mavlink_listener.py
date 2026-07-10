"""
MAVLink telemetry listener.

Connects to an ArduPilot / PX4 flight controller (real hardware or SITL)
via pymavlink, extracts fields from five message types, and feeds them
through MAVLinkAssembler to produce complete Guardian telemetry rows.

MAVLink → Guardian field mapping
---------------------------------
SCALED_IMU   xacc/yacc/zacc   mG  → accel_x/y/z_g      (÷ 1000)
SCALED_IMU   xgyro/ygyro/zgyro mdps→ gyro_x/y/z_dps     (÷ 1000)
GPS_RAW_INT  lat / lon         1e7 → gps_lat/lon_deg    (÷ 1e7)
GPS_RAW_INT  satellites_visible    → satellite_count
GPS_RAW_INT  fix_type          ≥3  → gps_fix_status=1
GPS_RAW_INT  alt               mm  → gps_alt_m           (÷ 1000, stored in row)
VFR_HUD      alt                m  → altitude_est_m
VFR_HUD      groundspeed        m/s→ gps_speed_mps
VFR_HUD      heading            deg→ heading_deg
SYS_STATUS   voltage_battery   mV  → battery_voltage_v   (÷ 1000)
SCALED_PRESSURE temperature    cdeg→ temperature_c       (÷ 100)
SCALED_PRESSURE press_abs      hPa → pressure_hpa
HEARTBEAT    base_mode              → armed (persists across rows)
"""

import threading
import time

try:
    from pymavlink import mavutil as _mavutil
    _MAVLINK_AVAILABLE = True
except ImportError:
    _MAVLINK_AVAILABLE = False

from guardian.ingestion.mavlink_assembler import MAVLinkAssembler
from guardian.ingestion.mavlink_heartbeat import HeartbeatMonitor


class MAVLinkListener:
    """Receive Guardian telemetry rows from a MAVLink-speaking flight controller.

    Requires ``pymavlink`` to be installed.  Raises ``RuntimeError`` at
    instantiation time if the package is missing.

    Parameters
    ----------
    connection_string : str
        pymavlink connection string, e.g. ``"udp:0.0.0.0:14550"`` for
        UDP input or ``"serial:/dev/ttyUSB0:57600"`` for serial.
    system_id : int
        MAVLink system ID to request messages from (default 1).
    heartbeat_timeout_s : float
        Seconds without a HEARTBEAT before a warning is printed.
    """

    def __init__(self, connection_string="udp:0.0.0.0:14550",
                 system_id=1, heartbeat_timeout_s=3.0):
        if not _MAVLINK_AVAILABLE:
            raise RuntimeError(
                "pymavlink is not installed. Run: pip install pymavlink>=2.4"
            )
        self.connection_string = connection_string
        self.system_id = system_id
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self._conn = None
        self._thread = None
        self._running = False
        self._heartbeat_monitor = None

    def start(self, callback):
        """Open the MAVLink connection and start the receiver thread.

        Parameters
        ----------
        callback : callable
            Invoked with a complete Guardian telemetry row dict for each
            fully assembled set of MAVLink messages.
        """
        self._conn = _mavutil.mavlink_connection(self.connection_string,
                                                  source_system=self.system_id)
        # Identify ourselves as a GCS with an outbound heartbeat. For a
        # udpout: connection this is also what performs the socket's first
        # send — required on Windows before recvfrom() will succeed, and
        # what registers our address with the remote endpoint so it starts
        # relaying traffic back to us.
        self._send_heartbeat()
        self._request_data_streams()
        node_id = f"mavlink_{self.system_id}"
        assembler = MAVLinkAssembler(node_id=node_id)

        def _on_heartbeat_timeout():
            print(f"[Guardian] WARNING: no MAVLink heartbeat for "
                  f"{self.heartbeat_timeout_s:.0f}s — link may be lost.")

        self._heartbeat_monitor = HeartbeatMonitor(
            timeout_s=self.heartbeat_timeout_s,
            on_timeout=_on_heartbeat_timeout,
        )
        self._heartbeat_monitor.start()

        self._running = True
        self._thread = threading.Thread(
            target=self._receive_loop,
            args=(assembler, callback),
            daemon=True,
            name="mavlink-listener",
        )
        self._thread.start()

    def _send_heartbeat(self):
        try:
            self._conn.mav.heartbeat_send(
                _mavutil.mavlink.MAV_TYPE_GCS,
                _mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0, 0, 0,
            )
        except Exception:
            pass

    def _request_data_streams(self):
        # ArduPilot only auto-streams HEARTBEAT/TIMESYNC on a fresh
        # connection — SCALED_IMU/GPS_RAW_INT/VFR_HUD/SYS_STATUS/
        # SCALED_PRESSURE require an explicit stream-rate request from the
        # connecting GCS, same as any real ground station would send.
        try:
            self._conn.mav.request_data_stream_send(
                self._conn.target_system or self.system_id,
                self._conn.target_component or 1,
                _mavutil.mavlink.MAV_DATA_STREAM_ALL,
                10,  # Hz
                1,   # start
            )
        except Exception:
            pass

    def _receive_loop(self, assembler, callback):
        _HANDLED = {
            "SCALED_IMU", "SCALED_IMU2", "GPS_RAW_INT", "VFR_HUD",
            "SYS_STATUS", "SCALED_PRESSURE", "HEARTBEAT",
        }
        last_heartbeat_sent = time.monotonic()

        while self._running:
            try:
                now = time.monotonic()
                if now - last_heartbeat_sent >= 1.0:
                    self._send_heartbeat()
                    last_heartbeat_sent = now

                msg = self._conn.recv_match(type=list(_HANDLED), blocking=True,
                                            timeout=1.0)
                if msg is None:
                    continue

                msg_type = msg.get_type()

                if msg_type == "HEARTBEAT":
                    self._heartbeat_monitor.heartbeat_received()
                    armed = bool(msg.base_mode & _mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                    assembler.set_armed(armed)
                    continue

                fields = self._extract_fields(msg_type, msg)
                if fields:
                    # Not every handled message type carries time_boot_ms
                    # (VFR_HUD, SYS_STATUS, GPS_RAW_INT do not) — fall back
                    # to wall-clock time so timestamps still advance instead
                    # of collapsing to a constant 0.
                    fields["timestamp_ms"] = getattr(
                        msg, "time_boot_ms", None) or int(time.time() * 1000)
                    row = assembler.update(fields)
                    if row is not None:
                        callback(row)

            except Exception:
                if self._running:
                    raise

    @staticmethod
    def _extract_fields(msg_type, msg):
        if msg_type in ("SCALED_IMU", "SCALED_IMU2"):
            return {
                "accel_x_g": msg.xacc / 1000.0,
                "accel_y_g": msg.yacc / 1000.0,
                "accel_z_g": msg.zacc / 1000.0,
                "gyro_x_dps": msg.xgyro / 1000.0,
                "gyro_y_dps": msg.ygyro / 1000.0,
                "gyro_z_dps": msg.zgyro / 1000.0,
            }
        if msg_type == "GPS_RAW_INT":
            return {
                "gps_lat_deg": msg.lat / 1e7,
                "gps_lon_deg": msg.lon / 1e7,
                "satellite_count": msg.satellites_visible,
                "gps_fix_status": 1 if msg.fix_type >= 3 else 0,
            }
        if msg_type == "VFR_HUD":
            return {
                "altitude_est_m": msg.alt,
                "gps_speed_mps": msg.groundspeed,
                "heading_deg": msg.heading,
            }
        if msg_type == "SYS_STATUS":
            return {
                "battery_voltage_v": msg.voltage_battery / 1000.0,
            }
        if msg_type == "SCALED_PRESSURE":
            return {
                "temperature_c": msg.temperature / 100.0,
                "pressure_hpa": msg.press_abs,
            }
        return {}

    def stop(self):
        """Stop the receiver thread and close the MAVLink connection."""
        self._running = False
        if self._heartbeat_monitor is not None:
            self._heartbeat_monitor.stop()
            self._heartbeat_monitor = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None
