from guardian.schemas import (
    REQUIRED_FIELDS,
    REQUIRED_ALERT_FIELDS,
    get_missing_fields,
    validate_telemetry_row,
    validate_alert,
)


def make_row():
    return {
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
        "gps_lat_deg": -1.95,
        "gps_lon_deg": 30.06,
        "gps_alt_m": 121.0,
        "gps_speed_mps": 10.0,
        "gps_fix_status": 1,
        "satellite_count": 8,
        "link_status": "connected",
        "mode_state": "normal",
    }


def make_alert():
    return {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "aircraft_01",
        "severity": "WARNING",
        "confidence": 0.85,
        "reason_code": "PACKET_LOSS",
        "reason_text": "Missing packet sequence detected.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    }


def test_validate_telemetry_row_accepts_complete_row():
    row = make_row()
    assert validate_telemetry_row(row) is True


def test_validate_telemetry_row_rejects_missing_field():
    row = make_row()
    del row["gps_lat_deg"]

    assert validate_telemetry_row(row) is False


def test_validate_alert_accepts_complete_alert():
    alert = make_alert()
    assert validate_alert(alert) is True


def test_validate_alert_rejects_missing_field():
    alert = make_alert()
    del alert["reason_code"]

    assert validate_alert(alert) is False


def test_get_missing_fields_returns_expected_fields():
    row = {"timestamp_ms": 1000, "packet_id": 1}
    missing = get_missing_fields(row, REQUIRED_FIELDS)

    assert "node_id" in missing
    assert "accel_x_g" in missing
    assert "mode_state" in missing
    