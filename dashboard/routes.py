from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for, send_from_directory

from dashboard.auth import login_required, role_required

# How long since the last telemetry packet before we consider the link dead.
_LIVE_THRESHOLD_SECONDS = 10

_REACT_INDEX = Path(__file__).parent / "ui" / "dist" / "index.html"


def build_blueprint(db):
    bp = Blueprint("guardian", __name__)

    @bp.route("/")
    def index():
        if _REACT_INDEX.exists():
            return send_from_directory(str(_REACT_INDEX.parent), "index.html")
        alerts = db.get_recent_alerts(limit=50)
        telemetry = db.get_recent_telemetry(limit=1)
        latest = telemetry[0] if telemetry else None
        active = [a for a in alerts if a.get("alert_status") == "active"]
        history = [a for a in alerts if a.get("alert_status") != "active"]
        return render_template(
            "index.html",
            latest=latest,
            active_alerts=active,
            alert_history=history,
        )

    @bp.route("/api/alerts")
    @login_required
    def api_alerts():
        limit = request.args.get("limit", 50, type=int)
        return jsonify(db.get_recent_alerts(limit=limit))

    @bp.route("/api/connection-status")
    @login_required
    def api_connection_status():
        last_seen = db.get_last_telemetry_time()
        live = False
        if last_seen:
            try:
                last_dt = datetime.fromisoformat(last_seen)
                live = (datetime.now(timezone.utc) - last_dt).total_seconds() <= _LIVE_THRESHOLD_SECONDS
            except ValueError:
                live = False
        return jsonify({"live": live, "last_seen": last_seen})

    @bp.route("/api/telemetry")
    @login_required
    def api_telemetry():
        rows = db.get_recent_telemetry(limit=1)
        return jsonify(rows[0] if rows else None)

    @bp.route("/api/aircraft-positions")
    @login_required
    def api_aircraft_positions():
        return jsonify(db.get_aircraft_positions())

    @bp.route("/api/flight-trail")
    @login_required
    def api_flight_trail():
        node_id = request.args.get("node_id", "")
        limit = request.args.get("limit", 100, type=int)
        if not node_id:
            return jsonify([])
        return jsonify(db.get_flight_trail(node_id, limit=limit))

    @bp.route("/api/report", methods=["POST"])
    @role_required("admin")
    def api_report():
        from guardian.report_generator import generate_report, DEFAULT_REPORT_PATH
        try:
            report_md = generate_report()
            return jsonify({"report": report_md, "saved_to": str(DEFAULT_REPORT_PATH)})
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except Exception as exc:
            return jsonify({"error": f"Report generation failed: {exc}"}), 500

    @bp.route("/api/geofence")
    @login_required
    def api_geofence():
        from guardian.config import get_config
        cfg = get_config().get("geofence", {})
        return jsonify({
            "enabled": cfg.get("enabled", False),
            "polygon": cfg.get("polygon", []),
        })

    @bp.route("/api/alerts/<int:alert_id>")
    @login_required
    def api_alert_by_id(alert_id):
        record = db.get_alert_by_id(alert_id)
        if record is None:
            abort(404)
        return jsonify(record)

    @bp.route("/api/alerts/<int:alert_id>/confirm", methods=["POST"])
    @role_required("admin")
    def api_alert_confirm(alert_id):
        record = db.get_alert_by_id(alert_id)
        if record is None:
            abort(404)
        new_confirmed = not bool(record.get("confirmed", 0))
        db.update_alert_confirmed(alert_id, new_confirmed)
        db.insert_operator_action({
            "alert_id": alert_id,
            "action_type": "confirm" if new_confirmed else "unconfirm",
            "operator_note": "",
        })
        return jsonify({"status": "ok", "alert_id": alert_id, "confirmed": new_confirmed})

    @bp.route("/api/alerts/<int:alert_id>/action", methods=["POST"])
    @role_required("admin")
    def api_alert_action(alert_id):
        record = db.get_alert_by_id(alert_id)
        if record is None:
            abort(404)

        # Accept both JSON body (API clients) and form data (HTML buttons)
        if request.is_json:
            body = request.get_json(silent=True) or {}
        else:
            body = request.form

        action_type = body.get("action_type", "").strip()
        if action_type not in ("acknowledge", "escalate", "resolve"):
            return jsonify({"error": "action_type must be acknowledge, escalate, or resolve"}), 400

        operator_note = body.get("operator_note", "")
        db.insert_operator_action({
            "alert_id": alert_id,
            "action_type": action_type,
            "operator_note": operator_note,
        })

        status_map = {
            "acknowledge": "acknowledged",
            "escalate": "escalated",
            "resolve": "resolved",
        }
        db.update_alert_status(alert_id, status_map[action_type])

        if request.is_json:
            return jsonify({"status": "ok", "alert_id": alert_id,
                            "new_status": status_map[action_type]})
        return redirect(url_for("guardian.index"))

    return bp
