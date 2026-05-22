"""
Integration tests for MAVLinkListener.

These tests require a running ArduPilot SITL instance and are skipped
unless the environment variable MAVLINK_SIM=1 is set.

Run against SITL:
    MAVLINK_SIM=1 pytest tests/test_mavlink_listener.py -v
"""

import os
import time
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("MAVLINK_SIM") != "1",
    reason="Set MAVLINK_SIM=1 to run MAVLink integration tests against SITL",
)


@pytest.fixture
def listener():
    from guardian.ingestion.mavlink_listener import MAVLinkListener
    l = MAVLinkListener(connection_string="udp:127.0.0.1:14550", system_id=1)
    yield l
    l.stop()


def test_listener_receives_rows_from_sitl(listener):
    received = []
    listener.start(lambda row: received.append(row))
    time.sleep(5)
    assert len(received) > 0, "No rows received from SITL within 5 seconds"


def test_listener_rows_have_required_fields(listener):
    from guardian.ingestion.mavlink_assembler import _REQUIRED_FIELDS
    received = []
    listener.start(lambda row: received.append(row))
    time.sleep(5)
    assert received, "No rows received"
    row = received[0]
    for field in _REQUIRED_FIELDS:
        assert field in row, f"Missing field: {field}"


def test_listener_packet_ids_increment(listener):
    received = []
    listener.start(lambda row: received.append(row))
    time.sleep(5)
    assert len(received) >= 2
    ids = [r["packet_id"] for r in received]
    assert ids == sorted(ids)
    assert ids[0] < ids[-1]


def test_listener_battery_voltage_in_reasonable_range(listener):
    received = []
    listener.start(lambda row: received.append(row))
    time.sleep(5)
    assert received
    for row in received:
        v = float(row["battery_voltage_v"])
        assert 0 < v < 60, f"Unreasonable voltage: {v}"


def test_listener_gps_coordinates_nonzero(listener):
    received = []
    listener.start(lambda row: received.append(row))
    time.sleep(5)
    assert received
    row = received[-1]
    assert row["gps_lat_deg"] != 0 or row["gps_lon_deg"] != 0


def test_listener_stop_cleans_up(listener):
    listener.start(lambda row: None)
    time.sleep(1)
    listener.stop()
    assert listener._thread is None
    assert listener._conn is None
