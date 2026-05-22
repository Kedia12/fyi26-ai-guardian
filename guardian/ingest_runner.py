import time
from pathlib import Path

from guardian.config import get_config
from guardian.db import GuardianDB
from guardian.engine import GuardianEngine
from guardian.utils import format_alert, print_banner
from guardian.ingestion.listener_factory import create_listener


def run_live(mode=None):
    """Start the Guardian engine in live ingestion mode.

    Parameters
    ----------
    mode : str, optional
        Override the ingestion mode from config (``"udp"``, ``"serial"``,
        ``"mqtt"``). When None the value from ``config["ingestion"]["mode"]``
        is used.
    """
    cfg = get_config()
    project_root = Path(__file__).resolve().parent.parent

    # Allow caller to override mode without mutating the cached config dict
    if mode is not None:
        import copy
        cfg = copy.deepcopy(cfg)
        cfg.setdefault("ingestion", {})["mode"] = mode

    ingestion_mode = cfg.get("ingestion", {}).get("mode", "udp")

    # Database (optional)
    db_cfg = cfg.get("database", {})
    db = None
    if db_cfg.get("enabled", False):
        db_path = db_cfg.get("path", "results/guardian.db")
        if not Path(db_path).is_absolute():
            db_path = project_root / db_path
        db = GuardianDB(path=db_path)

    engine = GuardianEngine(db=db)

    print_banner()
    print(f"[Guardian] Live ingestion — mode={ingestion_mode}")
    udp_cfg = cfg.get("ingestion", {})
    if ingestion_mode == "udp":
        print(f"[Guardian] Listening on {udp_cfg.get('udp_host', '0.0.0.0')}:"
              f"{udp_cfg.get('udp_port', 14550)}")
    print("[Guardian] Press Ctrl+C to stop.\n")

    def on_row(row):
        alerts, anomaly_score = engine.process_row(row)
        score_str = f"{anomaly_score:.4f}" if anomaly_score is not None else "None"
        print(f"packet={row.get('packet_id')} ml_score={score_str}")
        for alert in alerts:
            print(format_alert(alert))

    listener = create_listener(cfg)
    listener.start(on_row)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Guardian] Stopping.")
    finally:
        listener.stop()
        if db is not None:
            db.close()


if __name__ == "__main__":
    run_live()
