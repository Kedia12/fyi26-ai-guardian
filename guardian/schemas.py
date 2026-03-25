REQUIRED_FIELDS = [
    "timestamp_ms",
    "packet_id",
    "node_id",
    "accel_x_g",
    "accel_y_g",
    "accel_z_g",
    "gyro_x_dps",
    "gyro_y_dps",
    "gyro_z_dps",
    "temperature_c",
    "pressure_hpa",
    "altitude_est_m",
    "battery_voltage_v",
    "low_power_flag",
    "gps_lat_deg",
    "gps_lon_deg",
    "gps_alt_m",
    "gps_speed_mps",
    "gps_fix_status",
    "satellite_count",
    "link_status",
    "mode_state",
]

REQUIRED_ALERT_FIELDS = [
    "timestamp_ms",
    "packet_id",
    "node_id",
    "severity",
    "confidence",
    "reason_code",
    "reason_text",
    "recommended_action",
    "alert_status",
]


def get_missing_fields(row, required_fields):
    return [field for field in required_fields if field not in row or row[field] in (None, "")]


def validate_telemetry_row(row):
    return get_missing_fields(row, REQUIRED_FIELDS) == []


def validate_alert(alert):
    return get_missing_fields(alert, REQUIRED_ALERT_FIELDS) == []
    