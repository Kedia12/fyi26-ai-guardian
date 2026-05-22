import threading

try:
    import serial as _serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False

from guardian.ingestion.udp_listener import parse_json_packet


class SerialListener:
    """Receive newline-delimited telemetry from a serial port.

    Requires ``pyserial`` to be installed. Raises ``RuntimeError`` at
    instantiation time if the package is missing.

    Parameters
    ----------
    port : str
        Serial device path, e.g. ``"/dev/ttyUSB0"`` or ``"COM3"``.
    baud : int
        Baud rate (default 57600).
    parser : callable, optional
        Function ``(bytes) -> dict | None`` to parse each line.
        Defaults to :func:`parse_json_packet`.
    """

    def __init__(self, port, baud=57600, parser=None):
        if not _SERIAL_AVAILABLE:
            raise RuntimeError(
                "pyserial is not installed. Run: pip install pyserial>=3.5"
            )
        self.port = port
        self.baud = baud
        self.parser = parser or parse_json_packet
        self._serial = None
        self._thread = None
        self._running = False

    def start(self, callback):
        """Open the serial port and start the receiver thread."""
        self._serial = _serial.Serial(self.port, self.baud, timeout=1.0)
        self._running = True
        self._thread = threading.Thread(
            target=self._receive_loop,
            args=(callback,),
            daemon=True,
            name="serial-listener",
        )
        self._thread.start()

    def _receive_loop(self, callback):
        while self._running:
            try:
                line = self._serial.readline()
                if not line:
                    continue
                row = self.parser(line)
                if row is not None:
                    callback(row)
            except Exception:
                break

    def stop(self):
        """Signal the receiver thread to stop and close the serial port."""
        self._running = False
        if self._serial is not None:
            self._serial.close()
            self._serial = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
