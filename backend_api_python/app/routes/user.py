"""
Desktop account profile and notification routes.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from app.services.signal_notifier import SignalNotifier
from app.services.user_service import get_user_service
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)
user_bp = Blueprint("desktop_user", __name__)


@user_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    user_id = int(g.user_id)
    profile = get_user_service().get_profile(user_id)
    if not profile:
        return jsonify({"code": 0, "msg": "User not found", "data": None}), 404

    profile["notification_settings"] = get_user_service().get_notification_settings(user_id)
    return jsonify({"code": 1, "msg": "success", "data": profile})


@user_bp.route("/profile/update", methods=["PUT"])
@login_required
def update_profile():
    payload = request.get_json() or {}
    data = {
        "nickname": payload.get("nickname") or "",
        "email": payload.get("email") or "",
        "avatar": payload.get("avatar") or "/avatar2.jpg",
    }
    success = get_user_service().update_profile(int(g.user_id), data)
    status = 200 if success else 400
    return jsonify({"code": 1 if success else 0, "msg": "success" if success else "Profile update failed", "data": None}), status


@user_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    payload = request.get_json() or {}
    old_password = payload.get("old_password") or ""
    new_password = payload.get("new_password") or ""
    confirm_password = payload.get("confirm_password") or new_password

    if new_password != confirm_password:
        return jsonify({"code": 0, "msg": "Password confirmation does not match", "data": None}), 400

    success, message = get_user_service().change_password(int(g.user_id), old_password, new_password)
    status = 200 if success else 400
    return jsonify({"code": 1 if success else 0, "msg": message, "data": None}), status


@user_bp.route("/notification-settings", methods=["GET"])
@login_required
def get_notification_settings():
    settings = get_user_service().get_notification_settings(int(g.user_id))
    if "default_channels" not in settings:
        settings["default_channels"] = ["browser"]
    return jsonify({"code": 1, "msg": "success", "data": settings})


@user_bp.route("/notification-settings", methods=["PUT"])
@login_required
def update_notification_settings():
    payload = request.get_json() or {}
    allowed = {
        "default_channels": payload.get("default_channels") or ["browser"],
        "telegram_bot_token": payload.get("telegram_bot_token") or "",
        "telegram_chat_id": payload.get("telegram_chat_id") or "",
        "email": payload.get("email") or "",
        "discord_webhook": payload.get("discord_webhook") or "",
        "webhook_url": payload.get("webhook_url") or "",
        "webhook_token": payload.get("webhook_token") or "",
        "phone": payload.get("phone") or "",
    }
    success = get_user_service().update_notification_settings(int(g.user_id), allowed)
    status = 200 if success else 400
    return jsonify({"code": 1 if success else 0, "msg": "success" if success else "Notification settings update failed", "data": None}), status


@user_bp.route("/test-notification", methods=["POST"])
@login_required
def test_notification():
    user_id = int(g.user_id)
    settings = get_user_service().get_notification_settings(user_id)
    notifier = SignalNotifier()
    result = notifier.notify_signal(
        strategy_id=0,
        strategy_name="Desktop Notification Test",
        symbol="LOCAL",
        signal_type="open_long",
        price=0.0,
        stake_amount=0.0,
        direction="long",
        notification_config={
            "channels": settings.get("default_channels") or ["browser"],
            "targets": {
                "telegram": settings.get("telegram_chat_id") or "",
                "telegram_bot_token": settings.get("telegram_bot_token") or "",
                "email": settings.get("email") or "",
                "discord": settings.get("discord_webhook") or "",
                "webhook": settings.get("webhook_url") or "",
                "webhook_token": settings.get("webhook_token") or "",
                "phone": settings.get("phone") or "",
            },
        },
    )
    return jsonify({"code": 1, "msg": "success", "data": result})
