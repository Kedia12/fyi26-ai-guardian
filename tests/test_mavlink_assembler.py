"""
Unit tests for MAVLinkAssembler — no hardware or pymavlink required.
All values are passed in already-converted Guardian units.
"""

import pytest
from guardian.ingestion.mavlink_assembler import MAVLinkAssembler, _REQUIRED_FIELDS


# ── helpers ──────────────────────────────────────────────────────────────────

def _imu():
    return {
        "accel_x_g": 0.01, "accel_y_g": 0.02, "accel_z_g": 1.00,
        "gyro_x_dps": 0.5,  "gyro_y_dps": 0.4,  "gyro_z_dps": 0.3,
    }

def _gps():
    return {
        "gps_lat_deg": 48.8566, "gps_lon_deg": 2.3522,
        "satellite_count": 8,   "gps_fix_status": 1,
    }

def _nav():
    return {"altitude_est_m": 120.0, "gps_speed_mps": 9.5}

def _battery(v=11.8):
    return {"battery_voltage_v": v}

def _env():
    return {"temperature_c": 25.0, "pressure_hpa": 1013.0}

def _fill(asm, ts=1000, battery_v=11.8):
    """Feed one complete set of messages into the assembler and return the row."""
    row = None
    for fields in [{"timestamp_ms": ts}, _imu(), _gps(), _nav(),
                   _battery(battery_v), _env()]:
        row = asm.update(fields)
    return row


# ── partial updates don't emit ────────────────────────────────────────────────

def test_single_field_update_returns_none():
    asm = MAVLinkAssembler()
    assert asm.update({"accel_x_g": 0.01}) is None


def test_partial_imu_update_returns_none():
    asm = MAVLinkAssembler()
    assert asm.update(_imu()) is None


def test_imu_plus_gps_still_incomplete():
    asm = MAVLinkAssembler()
    asm.update(_imu())
    assert asm.update(_gps()) is None


# ── emission ──────────────────────────────────────────────────────────────────

def test_emits_when_all_required_fields_set():
    asm = MAVLinkAssembler()
    row = _fill(asm)
    assert row is not None


def test_emitted_row_contains_all_required_fields():
    asm = MAVLinkAssembler()
    row = _fill(asm)
    for field in _REQUIRED_FIELDS:
        assert field in row, f"missing: {field}"


def test_emitted_row_contains_metadata_fields():
    asm = MAVLinkAssembler()
    row = _fill(asm, ts=5000)
    assert "packet_id"   in row
    assert "node_id"     in row
    assert "timestamp_ms" in row
    assert "low_power_flag" in row


def test_timestamp_ms_propagated():
    asm = MAVLinkAssembler()
    row = _fill(asm, ts=9999)
    assert row["timestamp_ms"] == 9999


def test_node_id_set_from_constructor():
    asm = MAVLinkAssembler(node_id="test_craft")
    row = _fill(asm)
    assert row["node_id"] == "test_craft"


# ── packet_id ─────────────────────────────────────────────────────────────────

def test_first_row_packet_id_is_one():
    asm = MAVLinkAssembler()
    row = _fill(asm)
    assert row["packet_id"] == 1


def test_packet_id_increments_each_emission():
    asm = MAVLinkAssembler()
    row1 = _fill(asm, ts=1000)
    row2 = _fill(asm, ts=2000)
    assert row2["packet_id"] == row1["packet_id"] + 1


def test_packet_id_increments_across_three_rows():
    asm = MAVLinkAssembler()
    ids = [_fill(asm, ts=i * 1000)["packet_id"] for i in range(1, 4)]
    assert ids == [1, 2, 3]


# ── low_power_flag ────────────────────────────────────────────────────────────

def test_low_power_flag_zero_when_battery_ok():
    asm = MAVLinkAssembler()
    row = _fill(asm, battery_v=11.8)
    assert row["low_power_flag"] == 0


def test_low_power_flag_one_when_battery_low():
    asm = MAVLinkAssembler()
    row = _fill(asm, battery_v=10.0)
    assert row["low_power_flag"] == 1


def test_low_power_flag_threshold_is_configurable():
    asm = MAVLinkAssembler(low_power_threshold_v=12.0)
    row = _fill(asm, battery_v=11.5)
    assert row["low_power_flag"] == 1


def test_low_power_flag_zero_at_threshold_boundary():
    asm = MAVLinkAssembler(low_power_threshold_v=10.5)
    row = _fill(asm, battery_v=10.5)
    assert row["low_power_flag"] == 0  # not strictly less than


# ── field values preserved ────────────────────────────────────────────────────

def test_accel_values_preserved():
    asm = MAVLinkAssembler()
    row = _fill(asm)
    assert row["accel_x_g"]  == pytest.approx(0.01)
    assert row["accel_y_g"]  == pytest.approx(0.02)
    assert row["accel_z_g"]  == pytest.approx(1.00)


def test_gps_coordinates_preserved():
    asm = MAVLinkAssembler()
    row = _fill(asm)
    assert row["gps_lat_deg"] == pytest.approx(48.8566)
    assert row["gps_lon_deg"] == pytest.approx(2.3522)


def test_gps_fix_status_one_when_fix_present():
    asm = MAVLinkAssembler()
    asm.update(_imu())
    asm.update({"gps_lat_deg": 1.0, "gps_lon_deg": 2.0,
                "satellite_count": 8, "gps_fix_status": 1})
    row = asm.update({**_nav(), **_battery(), **_env()})
    assert row["gps_fix_status"] == 1


def test_gps_fix_status_zero_when_no_fix():
    asm = MAVLinkAssembler()
    asm.update(_imu())
    asm.update({"gps_lat_deg": 0.0, "gps_lon_deg": 0.0,
                "satellite_count": 2, "gps_fix_status": 0})
    row = asm.update({**_nav(), **_battery(), **_env()})
    assert row["gps_fix_status"] == 0


# ── buffer reset after emission ───────────────────────────────────────────────

def test_buffer_resets_after_emission():
    asm = MAVLinkAssembler()
    _fill(asm)
    # After emission, a partial update must not immediately re-emit
    assert asm.update(_imu()) is None


def test_pending_fields_empty_after_fill():
    asm = MAVLinkAssembler()
    _fill(asm)
    # Buffer has reset; all required fields are pending again
    assert len(asm.pending_fields) == len(_REQUIRED_FIELDS)


# ── heartbeat monitor (no hardware) ──────────────────────────────────────────

def test_heartbeat_monitor_fires_on_timeout():
    import time
    from guardian.ingestion.mavlink_heartbeat import HeartbeatMonitor

    fired = []
    monitor = HeartbeatMonitor(timeout_s=0.15, on_timeout=lambda: fired.append(1))
    monitor.start()
    time.sleep(0.35)
    monitor.stop()
    assert len(fired) >= 1


def test_heartbeat_monitor_does_not_fire_when_reset():
    import time
    from guardian.ingestion.mavlink_heartbeat import HeartbeatMonitor

    fired = []
    monitor = HeartbeatMonitor(timeout_s=0.2, on_timeout=lambda: fired.append(1))
    monitor.start()
    # Reset timer before it fires
    time.sleep(0.1)
    monitor.heartbeat_received()
    time.sleep(0.1)
    monitor.heartbeat_received()
    time.sleep(0.05)
    monitor.stop()
    assert len(fired) == 0


def test_heartbeat_monitor_stop_is_idempotent():
    from guardian.ingestion.mavlink_heartbeat import HeartbeatMonitor
    monitor = HeartbeatMonitor(timeout_s=1.0)
    monitor.start()
    monitor.stop()
    monitor.stop()  # must not raise
