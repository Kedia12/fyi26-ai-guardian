from pathlib import Path

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
from guardian.ml_model import GuardianML


class GuardianEngine:
    def __init__(self):
        self.prev_row = None
        self.ml = GuardianML()
        self.ml_ready = False

        project_root = Path(__file__).resolve().parent.parent
        normal_csv = project_root / "data" / "scenarios" / "normal_flight.csv"

        if normal_csv.exists():
            self.ml.train_from_csv(normal_csv)
            self.ml_ready = True

    def process_row(self, row):
        alerts = []

        alerts.extend(check_packet_loss(self.prev_row, row))
        alerts.extend(check_out_of_order_packet(self.prev_row, row))
        alerts.extend(check_duplicate_packet(self.prev_row, row))
        alerts.extend(check_imu_dropout(row))
        alerts.extend(check_frozen_imu(self.prev_row, row))
        alerts.extend(check_low_battery(row))
        alerts.extend(check_gps_fix_loss(row))
        alerts.extend(check_gps_jump(self.prev_row, row))
        alerts.extend(check_gps_imu_inconsistency(self.prev_row, row))

        anomaly_score = None
        if self.ml_ready:
            anomaly_score = self.ml.score_row(row)
            if anomaly_score is not None:
                row["ml_anomaly_score"] = anomaly_score

        self.prev_row = row
        return alerts, anomaly_score
        