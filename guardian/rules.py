from alerts import build_alert


def check_packet_loss(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    expected_packet = int(prev_row["packet_id"]) + 1
    current_packet = int(row["packet_id"])
    time_gap = int(row["timestamp_ms"]) - int(prev_row["timestamp_ms"])

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


def check_imu_dropout(row):
    alerts = []

    accel_zero = (
        float(row["accel_x_g"]) == 0.0
        and float(row["accel_y_g"]) == 0.0
        and float(row["accel_z_g"]) == 0.0
    )

    gyro_zero = (
        float(row["gyro_x_dps"]) == 0.0
        and float(row["gyro_y_dps"]) == 0.0
        and float(row["gyro_z_dps"]) == 0.0
    )

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


def check_low_battery(row):
    alerts = []

    voltage = float(row["battery_voltage_v"])
    low_flag = int(row["low_power_flag"])

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


def check_gps_jump(prev_row, row):
    alerts = []

    if prev_row is None:
        return alerts

    prev_lat = float(prev_row["gps_lat_deg"])
    prev_lon = float(prev_row["gps_lon_deg"])
    prev_speed = float(prev_row["gps_speed_mps"])

    curr_lat = float(row["gps_lat_deg"])
    curr_lon = float(row["gps_lon_deg"])
    curr_speed = float(row["gps_speed_mps"])

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