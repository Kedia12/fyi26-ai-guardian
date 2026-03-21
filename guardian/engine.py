from rules import (
    check_packet_loss,
    check_imu_dropout,
    check_low_battery,
    check_gps_jump,
    check_gps_imu_inconsistency,
)


class GuardianEngine:
    def __init__(self):
        self.prev_row = None

    def process_row(self, row):
        alerts = []

        alerts.extend(check_packet_loss(self.prev_row, row))
        alerts.extend(check_imu_dropout(row))
        alerts.extend(check_low_battery(row))
        alerts.extend(check_gps_jump(self.prev_row, row))
        alerts.extend(check_gps_imu_inconsistency(self.prev_row, row))

        self.prev_row = row
        return alerts