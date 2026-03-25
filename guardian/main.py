from pathlib import Path
import sys

from guardian.replay import replay_csv
from guardian.engine import GuardianEngine


def run(path):
    engine = GuardianEngine()
    total_rows = 0
    total_alerts = 0

    for row in replay_csv(path):
        alerts, anomaly_score = engine.process_row(row)
        total_rows += 1
        total_alerts += len(alerts)

        if anomaly_score is None:
            print(f"packet={row['packet_id']} ml_anomaly_score=None")
        else:
            print(f"packet={row['packet_id']} ml_anomaly_score={anomaly_score:.4f}")

        for alert in alerts:
            print(alert)

    print("\nReplay complete.")
    print(f"Rows processed: {total_rows}")
    print(f"Alerts generated: {total_alerts}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        if not csv_path.is_absolute():
            csv_path = project_root / csv_path
    else:
        csv_path = project_root / "data" / "scenarios" / "low_battery.csv"

    run(csv_path)
    