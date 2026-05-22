import json
import socket
import threading


_CSV_FIELDS = [
    "timestamp_ms", "packet_id", "node_id",
    "accel_x_g", "accel_y_g", "accel_z_g",
    "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
    "temperature_c", "pressure_hpa", "altitude_est_m",
    "battery_voltage_v", "low_power_flag",
    "gps_lat_deg", "gps_lon_deg", "gps_alt_m", "gps_speed_mps",
    "gps_fix_status", "satellite_count",
    "link_status", "mode_state",
]


def parse_json_packet(data):
    """Parse a UDP payload as JSON. Returns a dict or None on failure."""
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def parse_csv_packet(data):
    """Parse a UDP payload as a comma-separated telemetry line.

    Expects exactly 22 fields in canonical schema order.
    Returns a dict or None if field count does not match.
    """
    try:
        parts = data.decode("utf-8").strip().split(",")
        if len(parts) != len(_CSV_FIELDS):
            return None
        return dict(zip(_CSV_FIELDS, parts))
    except Exception:
        return None


class UDPListener:
    """Receive telemetry rows over a UDP socket and invoke a callback for each.

    Parameters
    ----------
    host : str
        Interface to bind on (``"0.0.0.0"`` for all interfaces).
    port : int
        UDP port to listen on.
    parser : callable, optional
        Function ``(bytes) -> dict | None`` to parse each datagram.
        Defaults to :func:`parse_json_packet`.
    """

    def __init__(self, host="0.0.0.0", port=14550, parser=None):
        self.host = host
        self.port = port
        self.parser = parser or parse_json_packet
        self._socket = None
        self._thread = None
        self._running = False

    def start(self, callback):
        """Bind the socket and start the receiver thread.

        Parameters
        ----------
        callback : callable
            Invoked with ``(row: dict)`` for each successfully parsed datagram.
        """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.settimeout(1.0)
        self._socket.bind((self.host, self.port))
        self._running = True
        self._thread = threading.Thread(
            target=self._receive_loop,
            args=(callback,),
            daemon=True,
            name="udp-listener",
        )
        self._thread.start()

    def _receive_loop(self, callback):
        while self._running:
            try:
                data, _ = self._socket.recvfrom(65535)
                row = self.parser(data)
                if row is not None:
                    callback(row)
            except socket.timeout:
                continue
            except OSError:
                break

    def stop(self):
        """Signal the receiver thread to stop and wait for it to finish."""
        self._running = False
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
