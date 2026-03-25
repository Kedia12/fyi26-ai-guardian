from guardian.rules import (
    check_packet_loss,
    check_out_of_order_packet,
    check_duplicate_packet,
    check_imu_dropout,
    check_frozen_imu,
    check_low_battery,
    check_gps_fix_loss,
    check_gps_jump,
    check_gps_imu_inconsistency,
)


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


def test_check_packet_loss_detects_missing_packet():
    prev_row = make_row(packet_id=1, timestamp_ms=1000)
    row = make_row(packet_id=3, timestamp_ms=1100)

    alerts = check_packet_loss(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "PACKET_LOSS"


def test_check_packet_loss_detects_large_time_gap():
    prev_row = make_row(packet_id=1, timestamp_ms=1000)
    row = make_row(packet_id=2, timestamp_ms=1405)

    alerts = check_packet_loss(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "PACKET_LOSS"


def test_check_packet_loss_no_alert_on_normal_sequence():
    prev_row = make_row(packet_id=1, timestamp_ms=1000)
    row = make_row(packet_id=2, timestamp_ms=1100)

    alerts = check_packet_loss(prev_row, row)

    assert alerts == []


def test_check_out_of_order_packet_detects_alert():
    prev_row = make_row(packet_id=5)
    row = make_row(packet_id=4)

    alerts = check_out_of_order_packet(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "OUT_OF_ORDER_PACKET"


def test_check_duplicate_packet_detects_alert():
    prev_row = make_row(packet_id=7)
    row = make_row(packet_id=7)

    alerts = check_duplicate_packet(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "DUPLICATE_PACKET"


def test_check_imu_dropout_detects_all_zero_values():
    row = make_row(
        accel_x_g=0.0,
        accel_y_g=0.0,
        accel_z_g=0.0,
        gyro_x_dps=0.0,
        gyro_y_dps=0.0,
        gyro_z_dps=0.0,
    )

    alerts = check_imu_dropout(row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "IMU_DROPOUT"


def test_check_imu_dropout_no_alert_for_normal_values():
    row = make_row()

    alerts = check_imu_dropout(row)

    assert alerts == []


def test_check_frozen_imu_detects_repeated_values():
    prev_row = make_row(
        accel_x_g=0.10,
        accel_y_g=0.20,
        accel_z_g=0.98,
        gyro_x_dps=1.0,
        gyro_y_dps=1.5,
        gyro_z_dps=0.8,
    )
    row = make_row(
        accel_x_g=0.10,
        accel_y_g=0.20,
        accel_z_g=0.98,
        gyro_x_dps=1.0,
        gyro_y_dps=1.5,
        gyro_z_dps=0.8,
    )

    alerts = check_frozen_imu(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "IMU_FROZEN"


def test_check_low_battery_warning():
    row = make_row(battery_voltage_v=10.4, low_power_flag=0)

    alerts = check_low_battery(row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "LOW_BATTERY"
    assert alerts[0]["severity"] == "WARNING"


def test_check_low_battery_critical():
    row = make_row(battery_voltage_v=10.1, low_power_flag=1)

    alerts = check_low_battery(row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "LOW_BATTERY"
    assert alerts[0]["severity"] == "CRITICAL"


def test_check_gps_fix_loss_detects_alert():
    row = make_row(gps_fix_status=0, satellite_count=2)

    alerts = check_gps_fix_loss(row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "GPS_FIX_LOSS"


def test_check_gps_jump_detects_large_position_change():
    prev_row = make_row(gps_lat_deg=-1.9500, gps_lon_deg=30.0600, gps_speed_mps=10.0)
    row = make_row(gps_lat_deg=-1.9400, gps_lon_deg=30.0700, gps_speed_mps=11.0)

    alerts = check_gps_jump(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "GPS_JUMP"


def test_check_gps_jump_detects_large_speed_change():
    prev_row = make_row(gps_speed_mps=10.0)
    row = make_row(gps_speed_mps=30.5)

    alerts = check_gps_jump(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "GPS_JUMP"


def test_check_gps_imu_inconsistency_detects_alert():
    prev_row = make_row(
        gps_lat_deg=-1.9500,
        gps_lon_deg=30.0600,
    )
    row = make_row(
        gps_lat_deg=-1.9400,
        gps_lon_deg=30.0700,
        accel_x_g=0.01,
        accel_y_g=0.01,
        accel_z_g=1.00,
        gyro_x_dps=0.2,
        gyro_y_dps=0.2,
        gyro_z_dps=0.2,
    )

    alerts = check_gps_imu_inconsistency(prev_row, row)

    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "GPS_IMU_INCONSISTENCY"


def test_first_row_returns_no_prev_based_alerts():
    row = make_row()

    assert check_packet_loss(None, row) == []
    assert check_out_of_order_packet(None, row) == []
    assert check_duplicate_packet(None, row) == []
    assert check_frozen_imu(None, row) == []
    assert check_gps_jump(None, row) == []
    assert check_gps_imu_inconsistency(None, row) == []


def test_missing_values_do_not_crash_rules():
    prev_row = make_row()
    row = make_row(gps_lat_deg="", gps_lon_deg="", accel_x_g="", battery_voltage_v="")

    assert check_gps_jump(prev_row, row) == []
    assert check_gps_imu_inconsistency(prev_row, row) == []
    assert check_low_battery(row) == []
    