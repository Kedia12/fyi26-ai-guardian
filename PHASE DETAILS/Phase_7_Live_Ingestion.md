# Phase 7 — Live Telemetry Ingestion
**Fixes Gap 1: No live telemetry ingestion — the system only reads pre-recorded CSV files**

---

## What You Are Building

Right now the only way to feed data into the Guardian is through `replay_csv()`, which reads a static CSV file. A real aircraft streams telemetry continuously over a network. This phase adds three listener types:

1. **UDP socket listener** (primary) — listens on a UDP port for JSON or CSV-encoded telemetry packets sent over WiFi or a radio link
2. **Serial/UART listener** — reads from a USB serial port connected to a flight controller or telemetry radio
3. **MQTT listener** (stub) — subscribes to an MQTT broker topic (optional, lower priority)

All three listeners share the same interface: a `start(callback)` method that calls `callback(row)` for each valid telemetry row received. This means the Guardian engine does not care where its data comes from — it just calls `process_row(row)` regardless of the source.

A `queue.Queue` sits between the listener thread and the engine thread to handle concurrency safely.

---

## Prerequisites

- Phase 1 (config) — listener settings come from `ingestion` section of the YAML
- Phase 2 (JSON export) — alerts from live ingestion are exported automatically
- Phase 3 (database) — live alerts are persisted automatically
- Phase 4 (ML alerts) — ML_ANOMALY fires on live data

---

## Files You Will Create

```
guardian/ingestion/__init__.py
guardian/ingestion/udp_listener.py
guardian/ingestion/serial_listener.py
guardian/ingestion/mqtt_listener.py
guardian/ingestion/listener_factory.py
guardian/ingest_runner.py
tests/test_udp_listener.py
```

## Files You Will Modify

```
guardian/main.py                 ← add --live CLI flag
requirements.txt                 ← add pyserial>=3.5
```

---

## Step 1 — Install pyserial

```bash
pip install "pyserial>=3.5"
```

Add to `requirements.txt`:
```
pyserial>=3.5
# optional: paho-mqtt>=1.6
```

---

## Step 2 — Create `guardian/ingestion/__init__.py`

Create this empty file to make `guardian/ingestion/` a Python package:

```python
```
(empty file)

---

## Step 3 — Create `guardian/ingestion/udp_listener.py`

This is the primary listener. It opens a UDP socket and waits for incoming packets. Each packet is expected to be either a JSON object or a comma-separated string with fields in the same order as `REQUIRED_FIELDS`.

Create the file `guardian/ingestion/udp_listener.py`:

```python
import json
import socket
import threading
from guardian.schemas import REQUIRED_FIELDS, validate_telemetry_row


class UDPListener:
    """Listens for telemetry packets on a UDP port and calls a callback for each valid row.

    The listener runs in a background thread. The callback is called from that
    thread, so use a queue.Queue in the caller if you need thread safety.

    Parameters
    ----------
    host : str
        IP address to bind to. Use "0.0.0.0" to accept from all interfaces.
    port : int
        UDP port number to listen on.
    parser : callable
        Function that accepts raw bytes and returns a telemetry dict or None.
        Use parse_json_packet or parse_csv_packet.
    """

    def __init__(self, host="0.0.0.0", port=14550, parser=None):
        self.host = host
        self.port = port
        self.parser = parser or parse_json_packet
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, callback):
        """Start listening in a background thread.

        Parameters
        ----------
        callback : callable
            Called with a telemetry dict for each valid incoming packet.
            Receives one argument: the parsed row dict.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            args=(callback,),
            daemon=True,
            name="UDPListenerThread",
        )
        self._thread.start()
        print(f"UDP listener started on {self.host}:{self.port}")

    def _listen_loop(self, callback):
        """Internal: bind socket and enter receive loop."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)  # 1-second timeout so stop() can interrupt
        sock.bind((self.host, self.port))

        try:
            while not self._stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    # Normal — check the stop event and loop again
                    continue
                except OSError:
                    break

                row = self.parser(data)
                if row is not None:
                    callback(row)
        finally:
            sock.close()

    def stop(self):
        """Signal the listener thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        print("UDP listener stopped.")


# ---------------------------------------------------------------------------
# Parser functions
# ---------------------------------------------------------------------------

def parse_json_packet(data):
    """Parse a UDP packet containing a JSON-encoded telemetry dict.

    Parameters
    ----------
    data : bytes
        Raw UDP payload. Expected to be a UTF-8 encoded JSON object.

    Returns
    -------
    dict or None
        A validated telemetry row dict, or None if parsing or validation fails.
    """
    try:
        text = data.decode("utf-8").strip()
        row = json.loads(text)
        if not isinstance(row, dict):
            return None
        if validate_telemetry_row(row):
            return row
        return None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def parse_csv_packet(data):
    """Parse a UDP packet containing comma-separated telemetry values.

    The values must be in the same order as REQUIRED_FIELDS from schemas.py.

    Parameters
    ----------
    data : bytes
        Raw UDP payload. Expected to be a UTF-8 encoded comma-separated string.

    Returns
    -------
    dict or None
        A validated telemetry row dict, or None on parse/validation failure.
    """
    try:
        text = data.decode("utf-8").strip()
        values = text.split(",")
        if len(values) != len(REQUIRED_FIELDS):
            return None
        row = dict(zip(REQUIRED_FIELDS, values))
        if validate_telemetry_row(row):
            return row
        return None
    except (UnicodeDecodeError, ValueError):
        return None
```

---

## Step 4 — Create `guardian/ingestion/serial_listener.py`

This listener reads telemetry from a serial port (USB or UART). It works with flight controllers, telemetry radios (SiK), or any device that sends JSON or CSV lines over serial.

Create the file `guardian/ingestion/serial_listener.py`:

```python
import threading

from guardian.ingestion.udp_listener import parse_json_packet, parse_csv_packet


class SerialListener:
    """Listens for telemetry on a serial/UART port.

    Each line received from the serial port is parsed as either JSON or CSV.
    Requires pyserial to be installed.

    Parameters
    ----------
    port : str
        Serial port name. Examples: "/dev/ttyUSB0" (Linux), "COM3" (Windows).
    baud : int
        Baud rate. Common values: 57600, 115200.
    parser : callable, optional
        Packet parser function. Defaults to parse_json_packet.
    """

    def __init__(self, port="/dev/ttyUSB0", baud=57600, parser=None):
        self.port = port
        self.baud = baud
        self.parser = parser or parse_json_packet
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, callback):
        """Start reading from the serial port in a background thread.

        Parameters
        ----------
        callback : callable
            Called with a telemetry dict for each valid line received.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._read_loop,
            args=(callback,),
            daemon=True,
            name="SerialListenerThread",
        )
        self._thread.start()
        print(f"Serial listener started on {self.port} at {self.baud} baud")

    def _read_loop(self, callback):
        """Internal: open serial port and read lines."""
        try:
            import serial  # pyserial
        except ImportError:
            raise RuntimeError(
                "pyserial is required for serial ingestion. "
                "Install it with: pip install pyserial>=3.5"
            )

        ser = serial.Serial(self.port, self.baud, timeout=1.0)
        try:
            while not self._stop_event.is_set():
                try:
                    line = ser.readline()
                    if not line:
                        continue
                    row = self.parser(line)
                    if row is not None:
                        callback(row)
                except serial.SerialException as e:
                    print(f"Serial error: {e}")
                    break
        finally:
            ser.close()

    def stop(self):
        """Stop the serial listener thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        print("Serial listener stopped.")
```

---

## Step 5 — Create `guardian/ingestion/mqtt_listener.py`

This is an optional listener for MQTT brokers. It requires `paho-mqtt`. If paho-mqtt is not installed, importing this file still works — the error only surfaces when `start()` is called.

Create the file `guardian/ingestion/mqtt_listener.py`:

```python
import threading

from guardian.ingestion.udp_listener import parse_json_packet


class MQTTListener:
    """Subscribes to an MQTT topic and calls a callback for each valid message.

    Requires paho-mqtt to be installed:
        pip install "paho-mqtt>=1.6"

    Parameters
    ----------
    broker_host : str
        MQTT broker hostname or IP address.
    broker_port : int
        MQTT broker port. Default is 1883.
    topic : str
        MQTT topic to subscribe to. E.g. "aircraft/telemetry".
    parser : callable, optional
        Packet parser function. Defaults to parse_json_packet.
    """

    def __init__(self, broker_host="localhost", broker_port=1883,
                 topic="aircraft/telemetry", parser=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.parser = parser or parse_json_packet
        self._client = None
        self._stop_event = threading.Event()

    def start(self, callback):
        """Connect to the MQTT broker and start receiving messages.

        Parameters
        ----------
        callback : callable
            Called with a telemetry dict for each valid message received.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise RuntimeError(
                "paho-mqtt is required for MQTT ingestion. "
                "Install it with: pip install paho-mqtt>=1.6"
            )

        self._stop_event.clear()

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                client.subscribe(self.topic)
                print(f"MQTT connected: subscribed to '{self.topic}'")
            else:
                print(f"MQTT connection failed with code {rc}")

        def on_message(client, userdata, message):
            row = self.parser(message.payload)
            if row is not None:
                callback(row)

        self._client = mqtt.Client()
        self._client.on_connect = on_connect
        self._client.on_message = on_message
        self._client.connect(self.broker_host, self.broker_port, keepalive=60)
        self._client.loop_start()  # runs in background thread
        print(f"MQTT listener connecting to {self.broker_host}:{self.broker_port}")

    def stop(self):
        """Disconnect from the MQTT broker and stop the loop."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
        print("MQTT listener stopped.")
```

---

## Step 6 — Create `guardian/ingestion/listener_factory.py`

This factory function reads the config and returns the correct listener instance.

Create the file `guardian/ingestion/listener_factory.py`:

```python
def create_listener(config):
    """Create and return the appropriate telemetry listener based on config.

    Parameters
    ----------
    config : dict
        The full guardian config dict. Reads the "ingestion" section.

    Returns
    -------
    A listener object with start(callback) and stop() methods.

    Raises
    ------
    ValueError
        If config["ingestion"]["mode"] is not a known value.
    """
    ingestion_cfg = config.get("ingestion", {})
    mode = ingestion_cfg.get("mode", "replay").lower().strip()

    if mode == "udp":
        from guardian.ingestion.udp_listener import UDPListener, parse_json_packet
        host = ingestion_cfg.get("udp_host", "0.0.0.0")
        port = int(ingestion_cfg.get("udp_port", 14550))
        return UDPListener(host=host, port=port, parser=parse_json_packet)

    elif mode == "serial":
        from guardian.ingestion.serial_listener import SerialListener
        port = ingestion_cfg.get("serial_port", "/dev/ttyUSB0")
        baud = int(ingestion_cfg.get("serial_baud", 57600))
        return SerialListener(port=port, baud=baud)

    elif mode == "mqtt":
        from guardian.ingestion.mqtt_listener import MQTTListener
        broker = ingestion_cfg.get("mqtt_broker", "localhost")
        broker_port = int(ingestion_cfg.get("mqtt_port", 1883))
        topic = ingestion_cfg.get("mqtt_topic", "aircraft/telemetry")
        return MQTTListener(broker_host=broker, broker_port=broker_port, topic=topic)

    elif mode == "mavlink":
        from guardian.ingestion.mavlink_listener import MAVLinkListener
        conn_string = ingestion_cfg.get("mavlink_connection", "udp:0.0.0.0:14550")
        return MAVLinkListener(connection_string=conn_string)

    else:
        raise ValueError(
            f"Unknown ingestion mode '{mode}'. "
            f"Valid options: udp, serial, mqtt, mavlink, replay."
        )
```

---

## Step 7 — Create `guardian/ingest_runner.py`

This is the live ingestion entry point. It wires together the listener, the engine, the database, and the JSON exporter into a complete pipeline.

Create the file `guardian/ingest_runner.py`:

```python
"""Live telemetry ingestion runner.

Usage:
    python -m guardian.ingest_runner

Configure the ingestion mode in config/guardian_config.yaml:
    ingestion:
      mode: udp          # or serial, mqtt, mavlink
      udp_host: 0.0.0.0
      udp_port: 14550
"""
import queue
import signal
import sys

from guardian.config import get_config
from guardian.engine import GuardianEngine
from guardian.utils import format_alert, print_banner


def run_live(mode=None):
    """Start live telemetry ingestion using the configured listener.

    Parameters
    ----------
    mode : str, optional
        Override the ingestion mode from config. If None, uses config value.
    """
    print_banner()
    cfg = get_config()

    # Override mode if provided
    if mode is not None:
        cfg.setdefault("ingestion", {})["mode"] = mode

    ingestion_mode = cfg.get("ingestion", {}).get("mode", "udp")
    print(f"Ingestion mode: {ingestion_mode}")

    # Set up the database (optional)
    db = None
    db_cfg = cfg.get("database", {})
    if db_cfg.get("enabled", False):
        from guardian.db import GuardianDB
        db = GuardianDB(db_cfg.get("path", "results/guardian.db"))
        print(f"Database: {db_cfg.get('path', 'results/guardian.db')}")

    # Set up the engine
    engine = GuardianEngine(db=db)
    print("Guardian engine ready.")

    # Row queue: listener thread puts rows here, main thread consumes them.
    # This decouples the network I/O thread from the processing thread
    # and makes it thread-safe without locks.
    row_queue = queue.Queue(maxsize=1000)

    def on_row(row):
        """Called by the listener thread for each received telemetry row."""
        try:
            row_queue.put_nowait(row)
        except queue.Full:
            # Drop rows if the queue is full (processing is falling behind)
            print("[WARNING] Row queue full — dropping packet.")

    # Create and start the listener
    from guardian.ingestion.listener_factory import create_listener
    listener = create_listener(cfg)
    listener.start(on_row)

    # Counters for the session summary
    total_rows = 0
    total_alerts = 0

    # Graceful shutdown on Ctrl+C
    def signal_handler(sig, frame):
        print("\nShutdown signal received. Stopping listener...")
        listener.stop()
        if db is not None:
            db.close()
        if engine.exporter:
            engine.exporter.close()
        print(f"\nSession summary: {total_rows} rows processed, {total_alerts} alerts generated.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("Listening for telemetry... Press Ctrl+C to stop.\n")

    # Main processing loop: consume rows from the queue
    while True:
        try:
            row = row_queue.get(timeout=1.0)
        except queue.Empty:
            # No data — just loop and check again
            continue

        total_rows += 1
        alerts, anomaly_score = engine.process_row(row)
        total_alerts += len(alerts)

        # Print to console
        packet_id = row.get("packet_id", "?")
        if alerts:
            for alert in alerts:
                print(f"  Packet {packet_id}: {format_alert(alert)}")
        else:
            print(f"  Packet {packet_id}: OK | ML score={anomaly_score:.4f}" if anomaly_score else f"  Packet {packet_id}: OK")


if __name__ == "__main__":
    run_live()
```

---

## Step 8 — Modify `guardian/main.py`

Open `guardian/main.py`. Add a `--live` flag to the CLI argument parser. Find the `if __name__ == "__main__":` block (or wherever the CLI arguments are parsed) and update it:

```python
import sys

def run(path=None):
    """Main entry point for Guardian. Replays a CSV scenario file."""
    # ... existing replay logic unchanged ...

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--live" in args:
        # Live ingestion mode
        from guardian.ingest_runner import run_live
        # Allow passing a mode override: python -m guardian.main --live udp
        mode = None
        idx = args.index("--live")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            mode = args[idx + 1]
        run_live(mode=mode)
    else:
        # CSV replay mode (existing behaviour)
        csv_path = args[0] if args else "data/scenarios/low_battery.csv"
        run(csv_path)
```

---

## Step 9 — Create `tests/test_udp_listener.py`

Create the file `tests/test_udp_listener.py` with the following content.

```python
import json
import socket
import threading
import time
import pytest
from guardian.ingestion.udp_listener import (
    UDPListener,
    parse_json_packet,
    parse_csv_packet,
)
from guardian.schemas import REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# Helper: build a complete valid telemetry row dict
# ---------------------------------------------------------------------------

def make_row(**overrides):
    row = {
        "timestamp_ms": "1000", "packet_id": "1", "node_id": "node_01",
        "accel_x_g": "0.01", "accel_y_g": "0.02", "accel_z_g": "1.0",
        "gyro_x_dps": "0.1", "gyro_y_dps": "0.2", "gyro_z_dps": "0.3",
        "temperature_c": "25.0", "pressure_hpa": "1013.0", "altitude_est_m": "10.0",
        "battery_voltage_v": "11.8", "low_power_flag": "0",
        "gps_lat_deg": "43.5", "gps_lon_deg": "-79.3", "gps_alt_m": "10.0",
        "gps_speed_mps": "5.0", "gps_fix_status": "1", "satellite_count": "8",
        "link_status": "ok", "mode_state": "AUTO",
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# parse_json_packet tests
# ---------------------------------------------------------------------------

def test_parse_json_packet_valid_row_returns_dict():
    """parse_json_packet() with a valid row must return a dict."""
    row = make_row()
    data = json.dumps(row).encode("utf-8")
    result = parse_json_packet(data)
    assert isinstance(result, dict)
    assert result["node_id"] == "node_01"


def test_parse_json_packet_invalid_json_returns_none():
    """parse_json_packet() with garbage bytes must return None."""
    result = parse_json_packet(b"not valid json !!!")
    assert result is None


def test_parse_json_packet_missing_fields_returns_none():
    """parse_json_packet() with a dict missing required fields must return None."""
    incomplete = {"timestamp_ms": 1000, "packet_id": 1}
    data = json.dumps(incomplete).encode("utf-8")
    result = parse_json_packet(data)
    assert result is None


def test_parse_json_packet_empty_bytes_returns_none():
    """parse_json_packet() with empty bytes must return None."""
    result = parse_json_packet(b"")
    assert result is None


# ---------------------------------------------------------------------------
# parse_csv_packet tests
# ---------------------------------------------------------------------------

def test_parse_csv_packet_valid_row_returns_dict():
    """parse_csv_packet() must map comma-separated values to field names."""
    row = make_row()
    # Values in REQUIRED_FIELDS order
    csv_values = ",".join(str(row[f]) for f in REQUIRED_FIELDS)
    data = csv_values.encode("utf-8")
    result = parse_csv_packet(data)
    assert isinstance(result, dict)
    assert result["node_id"] == "node_01"


def test_parse_csv_packet_wrong_column_count_returns_none():
    """parse_csv_packet() with the wrong number of columns must return None."""
    data = b"1,2,3"  # only 3 values, not 22
    result = parse_csv_packet(data)
    assert result is None


def test_parse_csv_packet_empty_bytes_returns_none():
    """parse_csv_packet() with empty bytes must return None."""
    result = parse_csv_packet(b"")
    assert result is None


# ---------------------------------------------------------------------------
# UDPListener integration test
# ---------------------------------------------------------------------------

def test_udp_listener_receives_packet_and_calls_callback():
    """UDPListener must call the callback when a valid JSON packet is received."""
    received = []

    def callback(row):
        received.append(row)

    # Use port 0 to get an OS-assigned free port
    listener = UDPListener(host="127.0.0.1", port=0, parser=parse_json_packet)

    # We need to bind the socket to get the actual port before start()
    # Instead, use a known free port found dynamically:
    import socket as sock_mod
    with sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    listener.port = free_port
    listener.start(callback)
    time.sleep(0.1)  # Give the listener thread time to bind

    # Send one valid JSON packet
    row = make_row(packet_id="99")
    payload = json.dumps(row).encode("utf-8")
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(payload, ("127.0.0.1", free_port))
    send_sock.close()

    time.sleep(0.3)  # Give the listener time to receive and call the callback
    listener.stop()

    assert len(received) == 1, f"Expected 1 callback call but got {len(received)}"
    assert received[0].get("packet_id") in ("99", 99)


def test_udp_listener_ignores_invalid_packets():
    """UDPListener must not call callback for invalid packets."""
    received = []

    def callback(row):
        received.append(row)

    import socket as sock_mod
    with sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    listener = UDPListener(host="127.0.0.1", port=free_port, parser=parse_json_packet)
    listener.start(callback)
    time.sleep(0.1)

    # Send invalid data
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(b"this is not json", ("127.0.0.1", free_port))
    send_sock.close()

    time.sleep(0.3)
    listener.stop()

    assert len(received) == 0, "Callback must not be called for invalid packets."
```

---

## Step 10 — Run Tests

```bash
pytest tests/test_udp_listener.py -v
```

Expected: all tests pass.

```bash
pytest -q
```

Expected: zero failures.

---

## Step 11 — Test Live Ingestion Manually

Open two terminals.

**Terminal 1 — Start the live listener:**
```bash
# In config/guardian_config.yaml, make sure:
# ingestion:
#   mode: udp
#   udp_host: 0.0.0.0
#   udp_port: 14550

python -m guardian.ingest_runner
```

**Terminal 2 — Send test packets:**
```python
# Save this as test_send.py and run it
import socket, json, time, csv

ROWS = []
with open("data/scenarios/low_battery.csv", newline="") as f:
    for row in csv.DictReader(f):
        ROWS.append(row)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for row in ROWS:
    payload = json.dumps(row).encode("utf-8")
    sock.sendto(payload, ("127.0.0.1", 14550))
    print(f"Sent packet_id={row['packet_id']}")
    time.sleep(0.1)

sock.close()
print("Done.")
```

```bash
python test_send.py
```

Terminal 1 should show alerts arriving in real-time as packets are received.

---

## Checklist — Phase 7 Complete When:

- [ ] `guardian/ingestion/__init__.py` exists (empty)
- [ ] `guardian/ingestion/udp_listener.py` exists with `UDPListener`, `parse_json_packet`, `parse_csv_packet`
- [ ] `guardian/ingestion/serial_listener.py` exists with `SerialListener`
- [ ] `guardian/ingestion/mqtt_listener.py` exists with `MQTTListener`
- [ ] `guardian/ingestion/listener_factory.py` exists with `create_listener()`
- [ ] `guardian/ingest_runner.py` exists with `run_live()`
- [ ] `guardian/main.py` has `--live` flag that calls `run_live()`
- [ ] `tests/test_udp_listener.py` exists with all tests passing
- [ ] `requirements.txt` includes `pyserial>=3.5`
- [ ] Manual test: sending UDP packets triggers Guardian alerts in real-time
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
guardian/
├── ingestion/                   ← NEW package
│   ├── __init__.py
│   ├── udp_listener.py
│   ├── serial_listener.py
│   ├── mqtt_listener.py
│   └── listener_factory.py
├── ingest_runner.py             ← NEW — live ingestion entry point
└── main.py                      ← MODIFIED — --live flag added

tests/
└── test_udp_listener.py         ← NEW — 9 UDP and parser tests

requirements.txt                 ← MODIFIED — added pyserial>=3.5
```

---

## Proceed to Phase 8 →

Phase 8 packages the entire system for deployment: a Dockerfile, docker-compose, pyproject.toml for pip installation, and a GitHub Actions CI pipeline. No Python logic changes — pure infrastructure.
