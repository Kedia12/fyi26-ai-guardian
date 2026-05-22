"""
MAVLink message assembler.

MAVLink telemetry arrives as a stream of typed messages (SCALED_IMU,
GPS_RAW_INT, VFR_HUD, SYS_STATUS, SCALED_PRESSURE …).  Each message
contains only a subset of the Guardian 22-field schema.

MAVLinkAssembler accumulates fields from multiple messages and emits a
complete Guardian telemetry row the moment all required fields have been
populated.  After emission the internal buffer resets so the next burst
of messages produces the next row.

Conversion from raw MAVLink units to Guardian units is the responsibility
of the caller (MAVLinkListener).  The assembler works entirely with
already-converted values.
"""

_REQUIRED_FIELDS = frozenset({
    # IMU (from SCALED_IMU)
    "accel_x_g", "accel_y_g", "accel_z_g",
    "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
    # Navigation (from GPS_RAW_INT + VFR_HUD)
    "gps_lat_deg", "gps_lon_deg",
    "gps_speed_mps", "altitude_est_m",
    "satellite_count", "gps_fix_status",
    # Power (from SYS_STATUS)
    "battery_voltage_v",
    # Environment (from SCALED_PRESSURE)
    "temperature_c", "pressure_hpa",
})


class MAVLinkAssembler:
    """Merge partial MAVLink field updates into complete Guardian telemetry rows.

    Parameters
    ----------
    node_id : str
        Node identifier written into every emitted row.
    low_power_threshold_v : float
        Battery voltage below which ``low_power_flag`` is set to ``1``.
    """

    def __init__(self, node_id="mavlink_node", low_power_threshold_v=10.5):
        self.node_id = node_id
        self.low_power_threshold_v = low_power_threshold_v
        self._partial = {}
        self._packet_id = 0

    def update(self, fields):
        """Merge *fields* into the internal buffer.

        Parameters
        ----------
        fields : dict
            Converted Guardian-unit fields extracted from one MAVLink message.

        Returns
        -------
        dict or None
            A complete telemetry row if all required fields are now present,
            otherwise ``None``.
        """
        self._partial.update(fields)
        if _REQUIRED_FIELDS.issubset(self._partial.keys()):
            return self._emit()
        return None

    def _emit(self):
        self._packet_id += 1
        voltage = float(self._partial.get("battery_voltage_v", 99.0))
        row = {
            "timestamp_ms": int(self._partial.get("timestamp_ms", 0)),
            "packet_id": self._packet_id,
            "node_id": self.node_id,
            "low_power_flag": 1 if voltage < self.low_power_threshold_v else 0,
        }
        for field in _REQUIRED_FIELDS:
            row[field] = self._partial[field]
        self._partial = {}
        return row

    @property
    def pending_fields(self):
        """Set of required fields not yet received in the current batch."""
        return _REQUIRED_FIELDS - self._partial.keys()
