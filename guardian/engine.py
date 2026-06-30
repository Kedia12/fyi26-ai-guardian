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
    check_geofence_breach,
)
from guardian.ml_model import GuardianML
from guardian.export import AlertExporter
from guardian.config import get_config, get_ml_param
from guardian.alerts import build_alert
from guardian.predictor import TelemetryBuffer, predict_battery_depletion, predict_imu_drift


class GuardianEngine:
    def __init__(self, db=None):
        self.prev_row = None
        self.db = db
        self.ml = GuardianML()
        self.ml_ready = False

        project_root = Path(__file__).resolve().parent.parent
        normal_csv = project_root / "data" / "scenarios" / "normal_flight.csv"

        if normal_csv.exists():
            self.ml.train_from_csv(normal_csv)
            self.ml_ready = True

        # Instantiate the alert exporter based on config settings.
        cfg = get_config()
        pred_cfg = cfg.get("prediction", {})
        window_size = int(pred_cfg.get("window_size", 20))
        self.telemetry_buffer = TelemetryBuffer(window_size=window_size)
        logging_cfg = cfg.get("logging", {})
        export_enabled = logging_cfg.get("json_export_enabled", False)
        export_path = logging_cfg.get("json_export_path", "results/logs/alerts.jsonl")
        if export_enabled and not Path(export_path).is_absolute():
            export_path = project_root / export_path
        self.exporter = AlertExporter(path=export_path, enabled=export_enabled)

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
        alerts.extend(check_geofence_breach(row))

        self.telemetry_buffer.push(row)
        alerts.extend(predict_battery_depletion(self.telemetry_buffer, row))
        alerts.extend(predict_imu_drift(self.telemetry_buffer, row))

        anomaly_score = None
        if self.ml_ready:
            anomaly_score = self.ml.score_row(row)
            if anomaly_score is not None:
                row["ml_anomaly_score"] = anomaly_score
                if anomaly_score > get_ml_param("alert_threshold", 0.1):
                    ml_alert = build_alert(
                        row=row,
                        severity=get_ml_param("alert_severity", "WARNING"),
                        confidence=min(anomaly_score / (anomaly_score + 1.0), 0.99),
                        reason_code="ML_ANOMALY",
                        reason_text=f"ML anomaly score {anomaly_score:.4f} exceeded threshold.",
                        recommended_action="VERIFY_OPERATOR",
                    )
                    alerts.append(ml_alert)

        self.prev_row = row

        if self.db is not None:
            self.db.insert_telemetry(row)
            for alert in alerts:
                self.db.insert_alert(
                    alert,
                    ml_source=(alert.get("reason_code") == "ML_ANOMALY"),
                )

        # Export all alerts to the .jsonl log file
        if alerts:
            self.exporter.write_batch(alerts, row)

        return alerts, anomaly_score
        