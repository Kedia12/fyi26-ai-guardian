from guardian.engine import GuardianEngine


def make_row(**overrides):
    row = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "aircraft_01",
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 1.00,
        "gyro_x_dps": 0.5,
        "gyro_y_dps": 0.4,
        "gyro_z_dps": 0.3,
        "temperature_c": 25.0,
        "pressure_hpa": 1013.2,
        "altitude_est_m": 120.0,
        "battery_voltage_v": 11.1,
        "low_power_flag": 0,
        "gps_lat_deg": -1.9500,
        "gps_lon_deg": 30.0600,
        "gps_alt_m": 121.0,
        "gps_speed_mps": 10.0,
        "gps_fix_status": 1,
        "satellite_count": 8,
        "link_status": "connected",
        "mode_state": "normal",
    }
    row.update(overrides)
    return row


def test_engine_process_row_returns_alerts_and_score():
    engine = GuardianEngine()

    row = make_row()
    alerts, anomaly_score = engine.process_row(row)

    assert isinstance(alerts, list)
    assert "ml_anomaly_score" in row or anomaly_score is None


def test_engine_detects_packet_loss_on_second_row():
    engine = GuardianEngine()

    first_row = make_row(packet_id=1, timestamp_ms=1000)
    second_row = make_row(packet_id=3, timestamp_ms=1100)

    engine.process_row(first_row)
    alerts, _ = engine.process_row(second_row)

    assert any(alert["reason_code"] == "PACKET_LOSS" for alert in alerts)


def test_engine_updates_prev_row():
    engine = GuardianEngine()

    row = make_row(packet_id=5)
    engine.process_row(row)

    assert engine.prev_row == row
    