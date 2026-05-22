from pathlib import Path
import sys

from guardian.replay import replay_csv
from guardian.engine import GuardianEngine
from guardian.utils import print_banner, format_alert, print_replay_summary
from guardian.config import get_config


def _cli():
    """Entry point used by the ``guardian`` console script."""
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if "--live" in sys.argv:
        from guardian.ingest_runner import run_live
        positional = [a for a in sys.argv[1:] if not a.startswith("-")]
        run_live(mode=positional[0] if positional else None)
    else:
        positional = [a for a in sys.argv[1:] if not a.startswith("-")]
        if positional:
            csv_path = Path(positional[0])
            if not csv_path.is_absolute():
                csv_path = project_root / csv_path
        else:
            csv_path = project_root / "data" / "scenarios" / "low_battery.csv"
        run(csv_path)


def run(path):
    from guardian.db import GuardianDB

    project_root = Path(__file__).resolve().parent.parent
    cfg = get_config()
    db_cfg = cfg.get("database", {})
    db = None
    if db_cfg.get("enabled", False):
        raw = db_cfg.get("path", "results/guardian.db")
        db_path = Path(raw) if Path(raw).is_absolute() else project_root / raw
        db = GuardianDB(path=db_path)

    engine = GuardianEngine(db=db)
    total_rows = 0
    total_alerts = 0

    print_banner()

    for row in replay_csv(path):
        alerts, anomaly_score = engine.process_row(row)
        total_rows += 1
        total_alerts += len(alerts)

        if anomaly_score is None:
            print(f"packet={row['packet_id']} ml_anomaly_score=None")
        else:
            print(f"packet={row['packet_id']} ml_anomaly_score={anomaly_score:.4f}")

        for alert in alerts:
            print(format_alert(alert))

    print_replay_summary(total_rows, total_alerts)

    logging_cfg = cfg.get("logging", {})
    if logging_cfg.get("json_export_enabled", False):
        export_path = logging_cfg.get("json_export_path", "results/logs/alerts.jsonl")
        print(f"\nAlerts exported to: {export_path}")

    if db is not None:
        db.close()


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    if "--live" in sys.argv:
        from guardian.ingest_runner import run_live
        positional = [a for a in sys.argv[1:] if not a.startswith("-")]
        run_live(mode=positional[0] if positional else None)
    else:
        positional = [a for a in sys.argv[1:] if not a.startswith("-")]
        if positional:
            csv_path = Path(positional[0])
            if not csv_path.is_absolute():
                csv_path = project_root / csv_path
        else:
            csv_path = project_root / "data" / "scenarios" / "low_battery.csv"
        run(csv_path)
    