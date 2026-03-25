from alerts import build_alert

"""
Deterministic rule-based anomaly checks for the Guardian.

These rules are designed to provide auditable safety checks and
complement ML-based anomaly detection.
"""


def _safe_float(row, key, default=None):
    value = row.get(key, None)
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(row, key, default=None):
    value = row.get(key, None)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def check_packet_loss(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_packet = _safe_int(prev_row, "packet_id")
    current_packet = _safe_int(row, "packet_id")
    prev_time = _safe_int(prev_row, "timestamp_ms")
    current_time = _safe_int(row, "timestamp_ms")

    if None in (prev_packet, current_packet, prev_time, current_time):
        return alerts

    expected_packet = prev_packet + 1
    time_gap = current_time - prev_time

    if current_packet != expected_packet or time_gap > 200:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.85,
                reason_code="PACKET_LOSS",
                reason_text="Missing packet sequence or abnormal timestamp gap detected.",
                recommended_action="CHECK_LINK",
            )
        )

    return alerts


def check_out_of_order_packet(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_packet = _safe_int(prev_row, "packet_id")
    current_packet = _safe_int(row, "packet_id")

    if None in (prev_packet, current_packet):
        return alerts

    if current_packet < prev_packet:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.90,
                reason_code="OUT_OF_ORDER_PACKET",
                reason_text="Telemetry packet arrived out of order.",
                recommended_action="CHECK_LINK",
            )
        )

    return alerts


def check_duplicate_packet(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_packet = _safe_int(prev_row, "packet_id")
    current_packet = _safe_int(row, "packet_id")

    if None in (prev_packet, current_packet):
        return alerts

    if current_packet == prev_packet:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.88,
                reason_code="DUPLICATE_PACKET",
                reason_text="Duplicate telemetry packet detected.",
                recommended_action="CHECK_LINK",
            )
        )

    return alerts


def check_imu_dropout(row):
    alerts = []

    accel_x = _safe_float(row, "accel_x_g")
    accel_y = _safe_float(row, "accel_y_g")
    accel_z = _safe_float(row, "accel_z_g")
    gyro_x = _safe_float(row, "gyro_x_dps")
    gyro_y = _safe_float(row, "gyro_y_dps")
    gyro_z = _safe_float(row, "gyro_z_dps")

    if None in (accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        return alerts

    accel_zero = accel_x == 0.0 and accel_y == 0.0 and accel_z == 0.0
    gyro_zero = gyro_x == 0.0 and gyro_y == 0.0 and gyro_z == 0.0

    if accel_zero and gyro_zero:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.92,
                reason_code="IMU_DROPOUT",
                reason_text="IMU values dropped to zero.",
                recommended_action="CHECK_SENSOR",
            )
        )

    return alerts


def check_frozen_imu(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    keys = [
        "accel_x_g",
        "accel_y_g",
        "accel_z_g",
        "gyro_x_dps",
        "gyro_y_dps",
        "gyro_z_dps",
    ]

    prev_values = [_safe_float(prev_row, key) for key in keys]
    curr_values = [_safe_float(row, key) for key in keys]

    if any(value is None for value in prev_values + curr_values):
        return alerts

    if prev_values == curr_values:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.80,
                reason_code="IMU_FROZEN",
                reason_text="IMU readings repeated exactly across consecutive packets.",
                recommended_action="CHECK_SENSOR",
            )
        )

    return alerts


def check_low_battery(row):
    alerts = []

    voltage = _safe_float(row, "battery_voltage_v")
    low_flag = _safe_int(row, "low_power_flag")

    if voltage is None or low_flag is None:
        return alerts

    if low_flag == 1 or voltage < 10.5:
        alerts.append(
            build_alert(
                row=row,
                severity="CRITICAL" if voltage < 10.2 else "WARNING",
                confidence=0.97,
                reason_code="LOW_BATTERY",
                reason_text="Battery voltage below safety threshold.",
                recommended_action="ENTER_SAFE_MODE",
            )
        )

    return alerts


def check_gps_fix_loss(row):
    alerts = []

    gps_fix = _safe_int(row, "gps_fix_status")
    satellites = _safe_int(row, "satellite_count")

    if gps_fix is None or satellites is None:
        return alerts

    if gps_fix == 0 or satellites < 4:
        alerts.append(
            build_alert(
                row=row,
                severity="WARNING",
                confidence=0.90,
                reason_code="GPS_FIX_LOSS",
                reason_text="GPS fix unavailable or satellite count too low for reliable navigation data.",
                recommended_action="REQUEST_VERIFICATION",
            )
        )

    return alerts


def check_gps_jump(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_lat = _safe_float(prev_row, "gps_lat_deg")
    prev_lon = _safe_float(prev_row, "gps_lon_deg")
    prev_speed = _safe_float(prev_row, "gps_speed_mps")

    curr_lat = _safe_float(row, "gps_lat_deg")
    curr_lon = _safe_float(row, "gps_lon_deg")
    curr_speed = _safe_float(row, "gps_speed_mps")

    if None in (prev_lat, prev_lon, prev_speed, curr_lat, curr_lon, curr_speed):
        return alerts

    lat_jump = abs(curr_lat - prev_lat)
    lon_jump = abs(curr_lon - prev_lon)
    speed_jump = abs(curr_speed - prev_speed)

    if lat_jump > 0.001 or lon_jump > 0.001 or speed_jump > 15:
        alerts.append(
            build_alert(
                row=row,
                severity="CRITICAL",
                confidence=0.95,
                reason_code="GPS_JUMP",
                reason_text="GPS position or speed changed abruptly beyond expected limits.",
                recommended_action="VERIFY_OPERATOR",
            )
        )

    return alerts


def check_gps_imu_inconsistency(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_lat = _safe_float(prev_row, "gps_lat_deg")
    prev_lon = _safe_float(prev_row, "gps_lon_deg")
    curr_lat = _safe_float(row, "gps_lat_deg")
    curr_lon = _safe_float(row, "gps_lon_deg")

    accel_x = _safe_float(row, "accel_x_g")
    accel_y = _safe_float(row, "accel_y_g")
    accel_z = _safe_float(row, "accel_z_g")
    gyro_x = _safe_float(row, "gyro_x_dps")
    gyro_y = _safe_float(row, "gyro_y_dps")
    gyro_z = _safe_float(row, "gyro_z_dps")

    if None in (prev_lat, prev_lon, curr_lat, curr_lon, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        return alerts

    lat_jump = abs(curr_lat - prev_lat)
    lon_jump = abs(curr_lon - prev_lon)

    accel_mag = abs(accel_x) + abs(accel_y) + abs(accel_z - 1.0)
    gyro_mag = abs(gyro_x) + abs(gyro_y) + abs(gyro_z)

    gps_big_change = lat_jump > 0.001 or lon_jump > 0.001
    imu_low_motion = accel_mag < 0.2 and gyro_mag < 3.0

    if gps_big_change and imu_low_motion:
        alerts.append(
            build_alert(
                row=row,
                severity="CRITICAL",
                confidence=0.96,
                reason_code="GPS_IMU_INCONSISTENCY",
                reason_text="GPS changed significantly without matching IMU motion.",
                recommended_action="VERIFY_OPERATOR_AND_ENTER_DEGRADED_MODE",
            )
        )

    return alerts
    