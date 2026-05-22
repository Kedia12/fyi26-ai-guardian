from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for


def build_blueprint(db):
    bp = Blueprint("guardian", __name__)

    @bp.route("/")
    def index():
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
    def api_alerts():
        limit = request.args.get("limit", 50, type=int)
        return jsonify(db.get_recent_alerts(limit=limit))

    @bp.route("/api/telemetry")
    def api_telemetry():
        rows = db.get_recent_telemetry(limit=1)
        return jsonify(rows[0] if rows else None)

    @bp.route("/api/aircraft-positions")
    def api_aircraft_positions():
        return jsonify(db.get_aircraft_positions())

    @bp.route("/api/flight-trail")
    def api_flight_trail():
        node_id = request.args.get("node_id", "")
        limit = request.args.get("limit", 100, type=int)
        if not node_id:
            return jsonify([])
        return jsonify(db.get_flight_trail(node_id, limit=limit))

    @bp.route("/api/live-traffic")
    def api_live_traffic():
        import urllib.request, json as _json
        url = ("https://opensky-network.org/api/states/all"
               "?lamin=35&lomin=-10&lamax=72&lomax=40")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AI-Guardian-Dashboard/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            aircraft = []
            for s in (data.get("states") or []):
                lon, lat = s[5], s[6]
                if lon is None or lat is None or s[8]:
                    continue
                aircraft.append({
                    "icao24":         s[0],
                    "callsign":       (s[1] or "").strip() or s[0],
                    "origin_country": s[2],
                    "latitude":       lat,
                    "longitude":      lon,
                    "altitude_m":     s[7],
                    "velocity_mps":   s[9],
                    "heading_deg":    s[10],
                    "vertical_rate":  s[11],
                })
                if len(aircraft) >= 300:
                    break
            return jsonify(aircraft)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 503

    @bp.route("/api/alerts/<int:alert_id>")
    def api_alert_by_id(alert_id):
        record = db.get_alert_by_id(alert_id)
        if record is None:
            abort(404)
        return jsonify(record)

    @bp.route("/api/alerts/<int:alert_id>/confirm", methods=["POST"])
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
