import os
import re
import secrets
from functools import wraps

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

VALID_ROLES = ("admin", "user")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def bootstrap_admin(db):
    """Create the first admin account on first run, if none exists yet."""
    if db.count_users() > 0:
        return

    username = os.environ.get("GUARDIAN_ADMIN_USERNAME", "admin")
    password = os.environ.get("GUARDIAN_ADMIN_PASSWORD")
    generated = password is None
    if generated:
        password = secrets.token_urlsafe(12)

    db.insert_user(username, generate_password_hash(password), role="admin")

    if generated:
        print(
            f"[guardian] Created default admin account -> username: {username!r}  "
            f"password: {password!r} (change this ASAP; shown only once)"
        )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Login required"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _current_user_payload():
    return {
        "id": session["user_id"],
        "username": session["username"],
        "role": session["role"],
    }


def build_auth_blueprint(db):
    bp = Blueprint("auth", __name__)

    @bp.route("/api/login", methods=["POST"])
    def login():
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""

        user = db.get_user_by_username(username)
        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401
        if user.get("disabled"):
            return jsonify({"error": "Account disabled"}), 403

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify(_current_user_payload())

    @bp.route("/api/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"status": "ok"})

    @bp.route("/api/me")
    def me():
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return jsonify(_current_user_payload())

    @bp.route("/api/me/password", methods=["POST"])
    @login_required
    def change_password():
        body = request.get_json(silent=True) or {}
        current_password = body.get("current_password") or ""
        new_password = body.get("new_password") or ""

        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters"}), 400

        user = db.get_user_by_id(session["user_id"])
        if user is None or not check_password_hash(user["password_hash"], current_password):
            return jsonify({"error": "Current password is incorrect"}), 401

        db.update_user_password(user["id"], generate_password_hash(new_password))
        return jsonify({"status": "ok"})

    @bp.route("/api/users", methods=["GET"])
    @role_required("admin")
    def list_users():
        return jsonify(db.list_users())

    @bp.route("/api/users", methods=["POST"])
    @role_required("admin")
    def create_user():
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        role = body.get("role", "user")
        email = (body.get("email") or "").strip()

        if not username or len(password) < 8:
            return jsonify(
                {"error": "username is required and password must be at least 8 characters"}
            ), 400
        if role not in VALID_ROLES:
            return jsonify({"error": f"role must be one of {VALID_ROLES}"}), 400
        if email and not _EMAIL_RE.match(email):
            return jsonify({"error": "email is not valid"}), 400
        if db.get_user_by_username(username) is not None:
            return jsonify({"error": "Username already exists"}), 409

        user_id = db.insert_user(
            username, generate_password_hash(password), role=role, email=email or None
        )
        return jsonify({"id": user_id, "username": username, "role": role, "email": email}), 201

    @bp.route("/api/users/<int:user_id>", methods=["PATCH"])
    @role_required("admin")
    def modify_user(user_id):
        user = db.get_user_by_id(user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        body = request.get_json(silent=True) or {}
        kwargs = {}

        if "username" in body:
            username = (body.get("username") or "").strip()
            if not username:
                return jsonify({"error": "username cannot be empty"}), 400
            existing = db.get_user_by_username(username)
            if existing is not None and existing["id"] != user_id:
                return jsonify({"error": "Username already exists"}), 409
            kwargs["username"] = username

        if "email" in body:
            email = (body.get("email") or "").strip()
            if email and not _EMAIL_RE.match(email):
                return jsonify({"error": "email is not valid"}), 400
            kwargs["email"] = email

        if "role" in body:
            role = body.get("role")
            if role not in VALID_ROLES:
                return jsonify({"error": f"role must be one of {VALID_ROLES}"}), 400
            if (
                user_id == session["user_id"]
                and user["role"] == "admin"
                and role != "admin"
                and db.count_enabled_admins() <= 1
            ):
                return jsonify({"error": "Cannot demote the last remaining admin"}), 400
            kwargs["role"] = role

        if not kwargs:
            return jsonify({"error": "Nothing to update"}), 400

        db.update_user(user_id, **kwargs)
        updated = db.get_user_by_id(user_id)
        return jsonify({
            "id": updated["id"],
            "username": updated["username"],
            "role": updated["role"],
            "email": updated.get("email") or "",
        })

    @bp.route("/api/users/<int:user_id>/password", methods=["POST"])
    @role_required("admin")
    def admin_reset_password(user_id):
        user = db.get_user_by_id(user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        body = request.get_json(silent=True) or {}
        new_password = body.get("new_password") or ""
        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters"}), 400

        db.update_user_password(user_id, generate_password_hash(new_password))
        return jsonify({"status": "ok"})

    @bp.route("/api/users/<int:user_id>/disabled", methods=["POST"])
    @role_required("admin")
    def set_user_disabled(user_id):
        user = db.get_user_by_id(user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        body = request.get_json(silent=True) or {}
        disabled = bool(body.get("disabled"))

        if user_id == session["user_id"] and disabled:
            return jsonify({"error": "You cannot disable your own account"}), 400
        if user["role"] == "admin" and disabled and db.count_enabled_admins() <= 1:
            return jsonify({"error": "Cannot disable the last remaining admin"}), 400

        db.set_user_disabled(user_id, disabled)
        return jsonify({"id": user_id, "disabled": disabled})

    @bp.route("/api/users/<int:user_id>", methods=["DELETE"])
    @role_required("admin")
    def remove_user(user_id):
        user = db.get_user_by_id(user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        if user_id == session["user_id"]:
            return jsonify({"error": "You cannot delete your own account"}), 400
        if user["role"] == "admin" and db.count_enabled_admins() <= 1 and not user["disabled"]:
            return jsonify({"error": "Cannot delete the last remaining admin"}), 400

        db.delete_user(user_id)
        return jsonify({"status": "ok"})

    return bp
