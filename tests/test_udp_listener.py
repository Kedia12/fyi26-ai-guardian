import json
import socket
import time
import threading
import pytest

from guardian.ingestion.udp_listener import (
    UDPListener,
    parse_json_packet,
    parse_csv_packet,
    _CSV_FIELDS,
)
from guardian.ingestion.listener_factory import create_listener


# ── helpers ──────────────────────────────────────────────────────────────────

def _free_port():
    """Return an available local UDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _send_udp(data, port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(data, (host, port))


def _make_csv_payload(**overrides):
    defaults = {f: "0" for f in _CSV_FIELDS}
    defaults.update({"node_id": "node_01", "link_status": "OK", "mode_state": "NORMAL"})
    defaults.update({k: str(v) for k, v in overrides.items()})
    return ",".join(defaults[f] for f in _CSV_FIELDS).encode()


# ── parse_json_packet ─────────────────────────────────────────────────────────

def test_parse_json_valid():
    payload = json.dumps({"packet_id": 1, "timestamp_ms": 1000}).encode()
    result = parse_json_packet(payload)
    assert result["packet_id"] == 1
    assert result["timestamp_ms"] == 1000


def test_parse_json_invalid_returns_none():
    result = parse_json_packet(b"not json at all")
    assert result is None


def test_parse_json_empty_bytes_returns_none():
    result = parse_json_packet(b"")
    assert result is None


def test_parse_json_partial_json_returns_none():
    result = parse_json_packet(b'{"packet_id": 1')
    assert result is None


# ── parse_csv_packet ──────────────────────────────────────────────────────────

def test_parse_csv_valid_returns_dict():
    payload = _make_csv_payload(packet_id=42, timestamp_ms=5000)
    result = parse_csv_packet(payload)
    assert result is not None
    assert result["packet_id"] == "42"
    assert result["timestamp_ms"] == "5000"


def test_parse_csv_has_all_fields():
    payload = _make_csv_payload()
    result = parse_csv_packet(payload)
    for field in _CSV_FIELDS:
        assert field in result


def test_parse_csv_too_few_fields_returns_none():
    result = parse_csv_packet(b"1,2,node_01")
    assert result is None


def test_parse_csv_too_many_fields_returns_none():
    payload = _make_csv_payload() + b",extra_field"
    result = parse_csv_packet(payload)
    assert result is None


def test_parse_csv_empty_returns_none():
    result = parse_csv_packet(b"")
    assert result is None


# ── UDPListener loopback ──────────────────────────────────────────────────────

def test_udp_listener_receives_json_packet():
    received = []
    port = _free_port()
    listener = UDPListener(host="127.0.0.1", port=port)
    listener.start(lambda row: received.append(row))
    time.sleep(0.1)

    _send_udp(json.dumps({"packet_id": 7, "timestamp_ms": 9000}).encode(), port)
    time.sleep(0.2)
    listener.stop()

    assert len(received) == 1
    assert received[0]["packet_id"] == 7


def test_udp_listener_discards_invalid_packets():
    received = []
    port = _free_port()
    listener = UDPListener(host="127.0.0.1", port=port)
    listener.start(lambda row: received.append(row))
    time.sleep(0.1)

    _send_udp(b"garbage data ~~~", port)
    time.sleep(0.2)
    listener.stop()

    assert len(received) == 0


def test_udp_listener_receives_multiple_packets():
    received = []
    port = _free_port()
    listener = UDPListener(host="127.0.0.1", port=port)
    listener.start(lambda row: received.append(row))
    time.sleep(0.1)

    for i in range(5):
        _send_udp(json.dumps({"packet_id": i, "timestamp_ms": i * 100}).encode(), port)
    time.sleep(0.3)
    listener.stop()

    assert len(received) == 5


def test_udp_listener_uses_custom_parser():
    received = []
    port = _free_port()
    listener = UDPListener(host="127.0.0.1", port=port, parser=parse_csv_packet)
    listener.start(lambda row: received.append(row))
    time.sleep(0.1)

    _send_udp(_make_csv_payload(packet_id=99), port)
    time.sleep(0.2)
    listener.stop()

    assert len(received) == 1
    assert received[0]["packet_id"] == "99"


def test_udp_listener_stop_is_idempotent():
    port = _free_port()
    listener = UDPListener(host="127.0.0.1", port=port)
    listener.start(lambda row: None)
    time.sleep(0.05)
    listener.stop()
    listener.stop()  # second stop must not raise


# ── listener_factory ──────────────────────────────────────────────────────────

def test_factory_returns_udp_listener_for_udp_mode():
    cfg = {"ingestion": {"mode": "udp", "udp_host": "127.0.0.1", "udp_port": 19999}}
    listener = create_listener(cfg)
    assert isinstance(listener, UDPListener)


def test_factory_raises_for_unknown_mode():
    cfg = {"ingestion": {"mode": "foobar"}}
    with pytest.raises(ValueError, match="Unknown ingestion mode"):
        create_listener(cfg)


def test_factory_udp_uses_configured_port():
    cfg = {"ingestion": {"mode": "udp", "udp_host": "127.0.0.1", "udp_port": 12345}}
    listener = create_listener(cfg)
    assert listener.port == 12345
