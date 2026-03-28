"""
Authentication helpers for the desktop application.
"""
from __future__ import annotations

import datetime as dt
from functools import wraps

import jwt
from flask import g, jsonify, request

from app.config.settings import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_token(user_id: int, username: str) -> str | None:
    try:
        payload = {
            "exp": dt.datetime.utcnow() + dt.timedelta(days=7),
            "iat": dt.datetime.utcnow(),
            "sub": username,
            "user_id": user_id,
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")
    except Exception as exc:
        logger.error(f"generate_token failed: {exc}")
        return None


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(None, 1)[1].strip()

        if not token:
            return jsonify({"code": 401, "msg": "Token missing", "data": None}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({"code": 401, "msg": "Token invalid or expired", "data": None}), 401

        g.user_id = payload.get("user_id")
        g.username = payload.get("sub")
        return func(*args, **kwargs)

    return decorated


def get_current_user_id() -> int | None:
    return getattr(g, "user_id", None)
