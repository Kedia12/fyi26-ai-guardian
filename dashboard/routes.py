from pathlib import Path
import threading
import time
import urllib.request
import urllib.error
import json as _json

from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for, send_from_directory

_REACT_INDEX = Path(__file__).parent / "ui" / "dist" / "index.html"

_ADSBX_URL = "https://api.adsb.lol/v2/lat/48.85/lon/2.35/dist/500"

# Bounding box filter applied after fetch (lat/lon degrees).
# Covers the Paris/Western Europe region (approx. 500 nm around Paris).
_ADSBX_LAT_MIN, _ADSBX_LAT_MAX = 40.0, 58.0
_ADSBX_LON_MIN, _ADSBX_LON_MAX = -10.0, 20.0

_live_cache: dict = {"data": [], "error": None, "ts": 0.0}
_bg_started = False


def _fetch_adsbexchange() -> None:
    try:
        req = urllib.request.Request(
            _ADSBX_URL, headers={"User-Agent": "AI-Guardian-Dashboard/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
        aircraft = []
        for ac in data.get("ac") or []:
            lat = ac.get("lat")
            lon = ac.get("lon")
            if lat is None or lon is None:
                continue
            if not (_ADSBX_LAT_MIN <= lat <= _ADSBX_LAT_MAX and
                    _ADSBX_LON_MIN <= lon <= _ADSBX_LON_MAX):
                continue
            alt_ft = ac.get("alt_baro") or ac.get("alt_geom")
            alt_m = float(alt_ft) * 0.3048 if isinstance(alt_ft, (int, float)) else None
            gs_kt = ac.get("gs")
            vel_mps = float(gs_kt) * 0.514444 if isinstance(gs_kt, (int, float)) else None
            baro_rate = ac.get("baro_rate")
            vert_mps = float(baro_rate) * 0.00508 if isinstance(baro_rate, (int, float)) else None
            callsign = (ac.get("flight") or "").strip() or ac.get("hex", "")
            aircraft.append({
                "icao24":         ac.get("hex", ""),
                "callsign":       callsign,
                "origin_country": "",
                "latitude":       lat,
                "longitude":      lon,
                "altitude_m":     alt_m,
                "velocity_mps":   vel_mps,
                "heading_deg":    ac.get("track"),
                "vertical_rate":  vert_mps,
            })
            if len(aircraft) >= 1500:
                break
        _live_cache.update({"data": aircraft, "error": None, "ts": time.monotonic()})
    except urllib.error.HTTPError as exc:
        _live_cache["error"] = f"ADS-B Exchange HTTP {exc.code}"
    except urllib.error.URLError as exc:
        _live_cache["error"] = f"ADS-B Exchange unreachable: {exc.reason}"
    except Exception as exc:
        _live_cache["error"] = str(exc)


def _start_traffic_background(interval: int = 30) -> None:
    global _bg_started
    if _bg_started:
        return
    _bg_started = True

    def _loop():
        while True:
            _fetch_adsbexchange()
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True, name="live-traffic-refresh")
    t.start()


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

    @bp.route("/api/report", methods=["POST"])
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
    def api_geofence():
        from guardian.config import get_config
        cfg = get_config().get("geofence", {})
        return jsonify({
            "enabled": cfg.get("enabled", False),
            "polygon": cfg.get("polygon", []),
        })

    _start_traffic_background(interval=30)

    @bp.route("/api/live-traffic")
    def api_live_traffic():
        if _live_cache["error"] and not _live_cache["data"]:
            return jsonify({"error": _live_cache["error"]}), 503
        return jsonify(_live_cache["data"])

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
