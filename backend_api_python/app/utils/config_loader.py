"""
Desktop settings loader.

Local JSON configuration is the primary source of truth.
Environment variables can override individual values for development.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from app.config.database import SQLiteConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)
_config_cache: Optional[dict[str, Any]] = None


def get_settings_file_path() -> Path:
    base_dir = Path(SQLiteConfig.get_path()).resolve().parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "settings.json"


def _read_settings_file() -> dict[str, Any]:
    path = get_settings_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning(f"Failed to read settings file: {exc}")
        return {}


def write_addon_config(config: dict[str, Any]) -> None:
    path = get_settings_file_path()
    path.write_text(json.dumps(config or {}, ensure_ascii=False, indent=2), encoding="utf-8")


def load_addon_config() -> dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = _read_settings_file()

    def set_nested(root: dict[str, Any], dotted_key: str, value: Any) -> None:
        ref = root
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            node = ref.get(part)
            if not isinstance(node, dict):
                node = {}
                ref[part] = node
            ref = node
        ref[parts[-1]] = value

    def env_get(name: str) -> Optional[str]:
        value = os.getenv(name)
        if value is None:
            return None
        value = str(value).strip()
        return value if value else None

    mappings = [
        ("INTERNAL_API_KEY", "internal_api.key", "string"),
        ("LLM_PROVIDER", "llm.provider", "string"),
        ("OPENROUTER_API_KEY", "openrouter.api_key", "string"),
        ("OPENROUTER_MODEL", "openrouter.model", "string"),
        ("OPENROUTER_TEMPERATURE", "openrouter.temperature", "float"),
        ("OPENROUTER_TIMEOUT", "openrouter.timeout", "int"),
        ("OPENAI_API_KEY", "openai.api_key", "string"),
        ("OPENAI_MODEL", "openai.model", "string"),
        ("OPENAI_BASE_URL", "openai.base_url", "string"),
        ("GOOGLE_API_KEY", "google.api_key", "string"),
        ("GOOGLE_MODEL", "google.model", "string"),
        ("DEEPSEEK_API_KEY", "deepseek.api_key", "string"),
        ("DEEPSEEK_MODEL", "deepseek.model", "string"),
        ("DEEPSEEK_BASE_URL", "deepseek.base_url", "string"),
        ("GROK_API_KEY", "grok.api_key", "string"),
        ("GROK_MODEL", "grok.model", "string"),
        ("GROK_BASE_URL", "grok.base_url", "string"),
        ("FINNHUB_API_KEY", "finnhub.api_key", "string"),
        ("TIINGO_API_KEY", "tiingo.api_key", "string"),
        ("SEARCH_PROVIDER", "search.provider", "string"),
        ("SEARCH_GOOGLE_API_KEY", "search.google.api_key", "string"),
        ("SEARCH_GOOGLE_CX", "search.google.cx", "string"),
        ("SEARCH_BING_API_KEY", "search.bing.api_key", "string"),
        ("TAVILY_API_KEYS", "tavily.api_keys", "string"),
        ("SERPAPI_KEYS", "serpapi.api_keys", "string"),
        ("BOCHA_API_KEYS", "bocha.api_keys", "string"),
        ("ENABLE_PENDING_ORDER_WORKER", "runtime.enable_pending_order_worker", "bool"),
        ("ENABLE_PORTFOLIO_MONITOR", "runtime.enable_portfolio_monitor", "bool"),
        ("DISABLE_RESTORE_RUNNING_STRATEGIES", "runtime.disable_restore_running_strategies", "bool"),
        ("PRICE_CACHE_TTL_SEC", "runtime.price_cache_ttl_sec", "int"),
        ("STRATEGY_MAX_THREADS", "runtime.strategy_max_threads", "int"),
        ("SMTP_HOST", "notifications.smtp_host", "string"),
        ("SMTP_PORT", "notifications.smtp_port", "int"),
        ("SMTP_USER", "notifications.smtp_user", "string"),
        ("SMTP_PASSWORD", "notifications.smtp_password", "string"),
        ("SMTP_FROM", "notifications.smtp_from", "string"),
        ("SMTP_USE_TLS", "notifications.smtp_use_tls", "bool"),
        ("SMTP_USE_SSL", "notifications.smtp_use_ssl", "bool"),
        ("TWILIO_ACCOUNT_SID", "notifications.twilio_account_sid", "string"),
        ("TWILIO_AUTH_TOKEN", "notifications.twilio_auth_token", "string"),
        ("TWILIO_FROM_NUMBER", "notifications.twilio_from_number", "string"),
        ("TELEGRAM_BOT_TOKEN", "notifications.telegram_bot_token", "string"),
        ("ZHIYIQUANT_APP_DIR_NAME", "app.data_dir_name", "string"),
        ("LOG_LEVEL", "app.log_level", "string"),
        ("CACHE_ENABLED", "app.enable_cache", "bool"),
        ("ENABLE_AI_ANALYSIS", "app.enable_ai_analysis", "bool"),
    ]

    for env_name, dotted_key, value_type in mappings:
        raw = env_get(env_name)
        if raw is None:
            continue
        set_nested(config, dotted_key, _convert_value(raw, value_type))

    _config_cache = config
    return config


def _convert_value(value: str, value_type: str) -> Any:
    if value_type == "int":
        try:
            return int(value)
        except Exception:
            return 0
    if value_type == "float":
        try:
            return float(value)
        except Exception:
            return 0.0
    if value_type == "bool":
        return value.lower() in {"1", "true", "yes", "on"}
    if value_type == "json":
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value


def get_internal_api_key() -> Optional[str]:
    return load_addon_config().get("internal_api", {}).get("key")


def clear_config_cache() -> None:
    global _config_cache
    _config_cache = None
