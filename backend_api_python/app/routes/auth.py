"""
Local authentication routes for the desktop application.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from app.services.user_service import get_user_service
from app.utils.auth import generate_token, login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)
auth_bp = Blueprint("auth", __name__)


def _userinfo_payload(user: dict) -> dict:
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "nickname": user.get("nickname") or user.get("username") or "Owner",
        "avatar": user.get("avatar") or "/avatar2.jpg",
        "email": user.get("email") or "",
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"code": 0, "msg": "Username and password are required", "data": None}), 400

    user = get_user_service().authenticate(username, password)
    if not user:
        return jsonify({"code": 0, "msg": "Invalid username or password", "data": None}), 401

    token = generate_token(int(user["id"]), user.get("username") or username)
    if not token:
        return jsonify({"code": 0, "msg": "Failed to create session", "data": None}), 500

    return jsonify({
        "code": 1,
        "msg": "success",
        "data": {
            "token": token,
            "userinfo": _userinfo_payload(user),
        },
    })


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"code": 1, "msg": "success", "data": None})


@auth_bp.route("/info", methods=["GET"])
@login_required
def info():
    user = get_user_service().get_profile(int(g.user_id))
    if not user:
        return jsonify({"code": 0, "msg": "User not found", "data": None}), 404
    return jsonify({"code": 1, "msg": "success", "data": _userinfo_payload(user)})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json() or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or new_password

    if not old_password or not new_password:
        return jsonify({"code": 0, "msg": "Current password and new password are required", "data": None}), 400
    if new_password != confirm_password:
        return jsonify({"code": 0, "msg": "Password confirmation does not match", "data": None}), 400

    success, message = get_user_service().change_password(int(g.user_id), old_password, new_password)
    status = 200 if success else 400
    return jsonify({"code": 1 if success else 0, "msg": message, "data": None}), status
