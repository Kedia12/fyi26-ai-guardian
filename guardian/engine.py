from rules import check_packet_loss, check_imu_dropout, check_low_battery


class GuardianEngine:
    def __init__(self):
        self.prev_row = None

    def process_row(self, row):
        alerts = []

        alerts.extend(check_packet_loss(self.prev_row, row))
        alerts.extend(check_imu_dropout(row))
        alerts.extend(check_low_battery(row))

        self.prev_row = row
        return alerts