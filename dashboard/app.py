from pathlib import Path

from flask import Flask

from guardian.config import get_config
from guardian.db import GuardianDB
from dashboard.routes import build_blueprint


def create_app(db_path=None, config_path=None):
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "guardian-dashboard-secret"

    if db_path is None:
        from guardian.config import load_config
        cfg = load_config(config_path) if config_path else get_config()
        db_cfg = cfg.get("database", {})
        project_root = Path(__file__).resolve().parent.parent
        raw_path = db_cfg.get("path", "results/guardian.db")
        db_path = (project_root / raw_path
                   if not Path(raw_path).is_absolute()
                   else Path(raw_path))

    db = GuardianDB(path=db_path)
    app.register_blueprint(build_blueprint(db))
    return app


def run_dashboard(host="0.0.0.0", port=5000):
    app = create_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_dashboard()
