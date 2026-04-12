"""
Owner account service for the desktop application.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any, Optional

from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import bcrypt

    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


class UserService:
    def hash_password(self, password: str) -> str:
        if HAS_BCRYPT:
            return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

        salt = os.urandom(16).hex()
        digest = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return f"sha256${salt}${digest}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        if password_hash.startswith("$2"):
            if not HAS_BCRYPT:
                return False
            try:
                return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
            except Exception:
                return False
        if password_hash.startswith("sha256$"):
            _, salt, digest = password_hash.split("$", 2)
            computed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
            return computed == digest
        return False

    def ensure_owner_exists(self) -> None:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("SELECT id FROM zhiyiquant_users ORDER BY id ASC LIMIT 1")
            row = cur.fetchone()
            if row:
                cur.close()
                return

            username = (os.getenv("ZHIYIQUANT_OWNER_USERNAME") or "owner").strip()
            password = (os.getenv("ZHIYIQUANT_OWNER_PASSWORD") or "zhiyiquant").strip()
            nickname = (os.getenv("ZHIYIQUANT_OWNER_NICKNAME") or "智弈量化").strip()
            email = (os.getenv("ZHIYIQUANT_OWNER_EMAIL") or "").strip()
            cur.execute(
                """
                INSERT INTO zhiyiquant_users (
                    username, password_hash, email, nickname, avatar,
                    notification_settings, last_login_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    username,
                    self.hash_password(password),
                    email,
                    nickname,
                    "/avatar2.jpg",
                    "{}",
                ),
            )
            db.commit()
            cur.close()

    def get_owner(self) -> Optional[dict[str, Any]]:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, username, password_hash, email, nickname, avatar,
                       notification_settings, last_login_at, created_at, updated_at
                FROM zhiyiquant_users
                ORDER BY id ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            cur.close()
            return row

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        user = self.get_owner()
        if not user:
            return None
        if username.strip() != (user.get("username") or ""):
            return None
        if not self.verify_password(password, user.get("password_hash") or ""):
            return None

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "UPDATE zhiyiquant_users SET last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user["id"],),
            )
            db.commit()
            cur.close()

        user.pop("password_hash", None)
        return user

    def get_profile(self, user_id: int) -> Optional[dict[str, Any]]:
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, username, email, nickname, avatar, notification_settings,
                       last_login_at, created_at, updated_at
                FROM zhiyiquant_users
                WHERE id = ?
                """,
                (user_id,),
            )
            row = cur.fetchone()
            cur.close()
            return row

    def update_profile(self, user_id: int, data: dict[str, Any]) -> bool:
        nickname = (data.get("nickname") or "").strip()
        email = (data.get("email") or "").strip()
        avatar = (data.get("avatar") or "/avatar2.jpg").strip() or "/avatar2.jpg"

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                UPDATE zhiyiquant_users
                SET nickname = ?, email = ?, avatar = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (nickname, email, avatar, user_id),
            )
            db.commit()
            changed = cur.rowcount > 0
            cur.close()
            return changed

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        user = self.get_owner()
        if not user or int(user.get("id") or 0) != int(user_id):
            return False, "User not found"
        if not self.verify_password(old_password, user.get("password_hash") or ""):
            return False, "Current password is incorrect"
        if len(new_password or "") < 8:
            return False, "New password must be at least 8 characters"

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "UPDATE zhiyiquant_users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.hash_password(new_password), user_id),
            )
            db.commit()
            cur.close()
        return True, "Password updated"

    def get_notification_settings(self, user_id: int) -> dict[str, Any]:
        user = self.get_profile(user_id)
        if not user:
            return {}
        value = user.get("notification_settings")
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            import json

            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def update_notification_settings(self, user_id: int, settings: dict[str, Any]) -> bool:
        import json

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "UPDATE zhiyiquant_users SET notification_settings = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(settings or {}, ensure_ascii=False), user_id),
            )
            db.commit()
            changed = cur.rowcount > 0
            cur.close()
            return changed


_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
