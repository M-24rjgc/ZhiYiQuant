"""
Desktop settings API backed by local JSON configuration.
"""
from __future__ import annotations

import requests
from flask import Blueprint, jsonify, request

from app.config.api_keys import APIKeys
from app.utils.auth import login_required
from app.utils.config_loader import clear_config_cache, get_settings_file_path, load_addon_config, write_addon_config
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings_bp = Blueprint("settings", __name__)

CONFIG_SCHEMA = {
    "ai": {
        "title": "AI Settings",
        "icon": "robot",
        "order": 1,
        "items": [
            {"key": "LLM_PROVIDER", "label": "LLM Provider", "type": "select", "default": "openrouter", "options": [
                {"value": "openrouter", "label": "OpenRouter"},
                {"value": "openai", "label": "OpenAI"},
                {"value": "google", "label": "Google Gemini"},
                {"value": "deepseek", "label": "DeepSeek"},
                {"value": "grok", "label": "Grok"},
            ]},
            {"key": "OPENROUTER_API_KEY", "label": "OpenRouter API Key", "type": "password", "default": ""},
            {"key": "OPENROUTER_MODEL", "label": "OpenRouter Model", "type": "text", "default": "openai/gpt-4o"},
            {"key": "OPENAI_API_KEY", "label": "OpenAI API Key", "type": "password", "default": ""},
            {"key": "OPENAI_MODEL", "label": "OpenAI Model", "type": "text", "default": "gpt-4o"},
            {"key": "GOOGLE_API_KEY", "label": "Google API Key", "type": "password", "default": ""},
            {"key": "GOOGLE_MODEL", "label": "Google Model", "type": "text", "default": "gemini-1.5-flash"},
            {"key": "DEEPSEEK_API_KEY", "label": "DeepSeek API Key", "type": "password", "default": ""},
            {"key": "DEEPSEEK_MODEL", "label": "DeepSeek Model", "type": "text", "default": "deepseek-chat"},
            {"key": "GROK_API_KEY", "label": "Grok API Key", "type": "password", "default": ""},
            {"key": "GROK_MODEL", "label": "Grok Model", "type": "text", "default": "grok-beta"},
            {"key": "OPENROUTER_TEMPERATURE", "label": "Temperature", "type": "number", "default": 0.7},
            {"key": "OPENROUTER_TIMEOUT", "label": "Request Timeout (sec)", "type": "number", "default": 300},
        ],
    },
    "data": {
        "title": "Data Sources",
        "icon": "database",
        "order": 2,
        "items": [
            {"key": "FINNHUB_API_KEY", "label": "Finnhub API Key", "type": "password", "default": ""},
            {"key": "TIINGO_API_KEY", "label": "Tiingo API Key", "type": "password", "default": ""},
            {"key": "SEARCH_PROVIDER", "label": "Search Provider", "type": "select", "default": "google", "options": [
                {"value": "google", "label": "Google CSE"},
                {"value": "bing", "label": "Bing"},
                {"value": "tavily", "label": "Tavily"},
                {"value": "serpapi", "label": "SerpAPI"},
            ]},
            {"key": "SEARCH_GOOGLE_API_KEY", "label": "Google Search API Key", "type": "password", "default": ""},
            {"key": "SEARCH_GOOGLE_CX", "label": "Google Search CX", "type": "text", "default": ""},
            {"key": "SEARCH_BING_API_KEY", "label": "Bing Search API Key", "type": "password", "default": ""},
            {"key": "TAVILY_API_KEYS", "label": "Tavily API Keys", "type": "password", "default": ""},
            {"key": "SERPAPI_KEYS", "label": "SerpAPI Keys", "type": "password", "default": ""},
            {"key": "BOCHA_API_KEYS", "label": "Bocha API Keys", "type": "password", "default": ""},
        ],
    },
    "trading": {
        "title": "Trading Runtime",
        "icon": "stock",
        "order": 3,
        "items": [
            {"key": "ENABLE_PENDING_ORDER_WORKER", "label": "Enable Pending Order Worker", "type": "boolean", "default": True},
            {"key": "ENABLE_PORTFOLIO_MONITOR", "label": "Enable Portfolio Monitor", "type": "boolean", "default": True},
            {"key": "DISABLE_RESTORE_RUNNING_STRATEGIES", "label": "Disable Strategy Restore", "type": "boolean", "default": False},
            {"key": "PRICE_CACHE_TTL_SEC", "label": "Price Cache TTL", "type": "number", "default": 10},
            {"key": "STRATEGY_MAX_THREADS", "label": "Strategy Max Threads", "type": "number", "default": 64},
        ],
    },
    "notifications": {
        "title": "Notification Services",
        "icon": "bell",
        "order": 4,
        "items": [
            {"key": "SMTP_HOST", "label": "SMTP Host", "type": "text", "default": ""},
            {"key": "SMTP_PORT", "label": "SMTP Port", "type": "number", "default": 587},
            {"key": "SMTP_USER", "label": "SMTP User", "type": "text", "default": ""},
            {"key": "SMTP_PASSWORD", "label": "SMTP Password", "type": "password", "default": ""},
            {"key": "SMTP_FROM", "label": "SMTP From", "type": "text", "default": ""},
            {"key": "SMTP_USE_TLS", "label": "Use TLS", "type": "boolean", "default": True},
            {"key": "SMTP_USE_SSL", "label": "Use SSL", "type": "boolean", "default": False},
            {"key": "TWILIO_ACCOUNT_SID", "label": "Twilio Account SID", "type": "password", "default": ""},
            {"key": "TWILIO_AUTH_TOKEN", "label": "Twilio Auth Token", "type": "password", "default": ""},
            {"key": "TWILIO_FROM_NUMBER", "label": "Twilio From Number", "type": "text", "default": ""},
            {"key": "TELEGRAM_BOT_TOKEN", "label": "Telegram Bot Token", "type": "password", "default": ""},
        ],
    },
    "app": {
        "title": "Desktop Runtime",
        "icon": "desktop",
        "order": 5,
        "items": [
            {"key": "ZHIYIQUANT_APP_DIR_NAME", "label": "Data Directory Name", "type": "text", "default": "zhiyiquant"},
            {"key": "LOG_LEVEL", "label": "Log Level", "type": "select", "default": "INFO", "options": [
                {"value": "DEBUG", "label": "DEBUG"},
                {"value": "INFO", "label": "INFO"},
                {"value": "WARNING", "label": "WARNING"},
                {"value": "ERROR", "label": "ERROR"},
            ]},
            {"key": "CACHE_ENABLED", "label": "Enable Cache", "type": "boolean", "default": False},
            {"key": "ENABLE_AI_ANALYSIS", "label": "Enable AI Analysis", "type": "boolean", "default": True},
        ],
    },
}


def _flatten_config(config: dict) -> dict:
    flat = {}
    mappings = {
        "llm.provider": "LLM_PROVIDER",
        "openrouter.api_key": "OPENROUTER_API_KEY",
        "openrouter.model": "OPENROUTER_MODEL",
        "openrouter.temperature": "OPENROUTER_TEMPERATURE",
        "openrouter.timeout": "OPENROUTER_TIMEOUT",
        "openai.api_key": "OPENAI_API_KEY",
        "openai.model": "OPENAI_MODEL",
        "google.api_key": "GOOGLE_API_KEY",
        "google.model": "GOOGLE_MODEL",
        "deepseek.api_key": "DEEPSEEK_API_KEY",
        "deepseek.model": "DEEPSEEK_MODEL",
        "grok.api_key": "GROK_API_KEY",
        "grok.model": "GROK_MODEL",
        "finnhub.api_key": "FINNHUB_API_KEY",
        "tiingo.api_key": "TIINGO_API_KEY",
        "search.provider": "SEARCH_PROVIDER",
        "search.google.api_key": "SEARCH_GOOGLE_API_KEY",
        "search.google.cx": "SEARCH_GOOGLE_CX",
        "search.bing.api_key": "SEARCH_BING_API_KEY",
        "tavily.api_keys": "TAVILY_API_KEYS",
        "serpapi.api_keys": "SERPAPI_KEYS",
        "bocha.api_keys": "BOCHA_API_KEYS",
        "runtime.enable_pending_order_worker": "ENABLE_PENDING_ORDER_WORKER",
        "runtime.enable_portfolio_monitor": "ENABLE_PORTFOLIO_MONITOR",
        "runtime.disable_restore_running_strategies": "DISABLE_RESTORE_RUNNING_STRATEGIES",
        "runtime.price_cache_ttl_sec": "PRICE_CACHE_TTL_SEC",
        "runtime.strategy_max_threads": "STRATEGY_MAX_THREADS",
        "notifications.smtp_host": "SMTP_HOST",
        "notifications.smtp_port": "SMTP_PORT",
        "notifications.smtp_user": "SMTP_USER",
        "notifications.smtp_password": "SMTP_PASSWORD",
        "notifications.smtp_from": "SMTP_FROM",
        "notifications.smtp_use_tls": "SMTP_USE_TLS",
        "notifications.smtp_use_ssl": "SMTP_USE_SSL",
        "notifications.twilio_account_sid": "TWILIO_ACCOUNT_SID",
        "notifications.twilio_auth_token": "TWILIO_AUTH_TOKEN",
        "notifications.twilio_from_number": "TWILIO_FROM_NUMBER",
        "notifications.telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "app.data_dir_name": "ZHIYIQUANT_APP_DIR_NAME",
        "app.log_level": "LOG_LEVEL",
        "app.enable_cache": "CACHE_ENABLED",
        "app.enable_ai_analysis": "ENABLE_AI_ANALYSIS",
    }

    def get_nested(src: dict, dotted: str):
        ref = src
        for part in dotted.split("."):
            if not isinstance(ref, dict) or part not in ref:
                return None
            ref = ref[part]
        return ref

    for dotted, env_key in mappings.items():
        value = get_nested(config, dotted)
        if value is not None:
            flat[env_key] = value
    return flat


def _values_payload() -> dict:
    config = load_addon_config()
    flat = _flatten_config(config)
    result = {}
    for group_key, group in CONFIG_SCHEMA.items():
        result[group_key] = {}
        for item in group["items"]:
            result[group_key][item["key"]] = flat.get(item["key"], item.get("default"))
            if item["type"] == "password":
                result[group_key][f"{item['key']}_configured"] = bool(flat.get(item["key"]))
    return result


def _persist_settings(payload: dict) -> list[str]:
    current = load_addon_config()
    updates = {}
    for group_values in payload.values():
        if isinstance(group_values, dict):
            updates.update(group_values)

    new_config = dict(current)

    def ensure_branch(root: dict, *parts: str) -> dict:
        ref = root
        for part in parts:
            node = ref.get(part)
            if not isinstance(node, dict):
                node = {}
                ref[part] = node
            ref = node
        return ref

    for key, value in updates.items():
        if key == "LLM_PROVIDER":
            ensure_branch(new_config, "llm")["provider"] = value
        elif key.startswith("OPENROUTER_"):
            branch = ensure_branch(new_config, "openrouter")
            branch["api_key" if key.endswith("API_KEY") else "model" if key.endswith("MODEL") else "temperature" if key.endswith("TEMPERATURE") else "timeout"] = value
        elif key.startswith("OPENAI_"):
            branch = ensure_branch(new_config, "openai")
            branch["api_key" if key.endswith("API_KEY") else "model"] = value
        elif key.startswith("GOOGLE_"):
            branch = ensure_branch(new_config, "google")
            branch["api_key" if key.endswith("API_KEY") else "model"] = value
        elif key.startswith("DEEPSEEK_"):
            branch = ensure_branch(new_config, "deepseek")
            branch["api_key" if key.endswith("API_KEY") else "model"] = value
        elif key.startswith("GROK_"):
            branch = ensure_branch(new_config, "grok")
            branch["api_key" if key.endswith("API_KEY") else "model"] = value
        elif key == "FINNHUB_API_KEY":
            ensure_branch(new_config, "finnhub")["api_key"] = value
        elif key == "TIINGO_API_KEY":
            ensure_branch(new_config, "tiingo")["api_key"] = value
        elif key == "SEARCH_PROVIDER":
            ensure_branch(new_config, "search")["provider"] = value
        elif key == "SEARCH_GOOGLE_API_KEY":
            ensure_branch(new_config, "search", "google")["api_key"] = value
        elif key == "SEARCH_GOOGLE_CX":
            ensure_branch(new_config, "search", "google")["cx"] = value
        elif key == "SEARCH_BING_API_KEY":
            ensure_branch(new_config, "search", "bing")["api_key"] = value
        elif key == "TAVILY_API_KEYS":
            ensure_branch(new_config, "tavily")["api_keys"] = value
        elif key == "SERPAPI_KEYS":
            ensure_branch(new_config, "serpapi")["api_keys"] = value
        elif key == "BOCHA_API_KEYS":
            ensure_branch(new_config, "bocha")["api_keys"] = value
        elif key in {"ENABLE_PENDING_ORDER_WORKER", "ENABLE_PORTFOLIO_MONITOR", "DISABLE_RESTORE_RUNNING_STRATEGIES", "PRICE_CACHE_TTL_SEC", "STRATEGY_MAX_THREADS"}:
            branch = ensure_branch(new_config, "runtime")
            runtime_key = {
                "ENABLE_PENDING_ORDER_WORKER": "enable_pending_order_worker",
                "ENABLE_PORTFOLIO_MONITOR": "enable_portfolio_monitor",
                "DISABLE_RESTORE_RUNNING_STRATEGIES": "disable_restore_running_strategies",
                "PRICE_CACHE_TTL_SEC": "price_cache_ttl_sec",
                "STRATEGY_MAX_THREADS": "strategy_max_threads",
            }[key]
            branch[runtime_key] = value
        elif key.startswith("SMTP_") or key.startswith("TWILIO_") or key == "TELEGRAM_BOT_TOKEN":
            branch = ensure_branch(new_config, "notifications")
            notif_key = {
                "SMTP_HOST": "smtp_host",
                "SMTP_PORT": "smtp_port",
                "SMTP_USER": "smtp_user",
                "SMTP_PASSWORD": "smtp_password",
                "SMTP_FROM": "smtp_from",
                "SMTP_USE_TLS": "smtp_use_tls",
                "SMTP_USE_SSL": "smtp_use_ssl",
                "TWILIO_ACCOUNT_SID": "twilio_account_sid",
                "TWILIO_AUTH_TOKEN": "twilio_auth_token",
                "TWILIO_FROM_NUMBER": "twilio_from_number",
                "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
            }[key]
            branch[notif_key] = value
        elif key in {"ZHIYIQUANT_APP_DIR_NAME", "LOG_LEVEL", "CACHE_ENABLED", "ENABLE_AI_ANALYSIS"}:
            branch = ensure_branch(new_config, "app")
            app_key = {
                "ZHIYIQUANT_APP_DIR_NAME": "data_dir_name",
                "LOG_LEVEL": "log_level",
                "CACHE_ENABLED": "enable_cache",
                "ENABLE_AI_ANALYSIS": "enable_ai_analysis",
            }[key]
            branch[app_key] = value

    write_addon_config(new_config)
    clear_config_cache()
    return sorted(updates.keys())


@settings_bp.route("/schema", methods=["GET"])
@login_required
def get_settings_schema():
    return jsonify({"code": 1, "msg": "success", "data": CONFIG_SCHEMA})


@settings_bp.route("/values", methods=["GET"])
@login_required
def get_settings_values():
    return jsonify({"code": 1, "msg": "success", "data": _values_payload()})


@settings_bp.route("/save", methods=["POST"])
@login_required
def save_settings():
    try:
        payload = request.get_json() or {}
        updated_keys = _persist_settings(payload)
        return jsonify({"code": 1, "msg": "success", "data": {"updated_keys": updated_keys, "settings_file": str(get_settings_file_path())}})
    except Exception as exc:
        logger.error(f"save_settings failed: {exc}")
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@settings_bp.route("/openrouter-balance", methods=["GET"])
@login_required
def get_openrouter_balance():
    api_key = APIKeys.OPENROUTER_API_KEY
    if not api_key:
        return jsonify({"code": 0, "msg": "OpenRouter API key is not configured", "data": None}), 400

    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        return jsonify(
            {
                "code": 1,
                "msg": "success",
                "data": {
                    "label": payload.get("label", ""),
                    "usage": payload.get("usage", 0),
                    "limit": payload.get("limit"),
                    "limit_remaining": payload.get("limit_remaining"),
                    "is_free_tier": payload.get("is_free_tier", False),
                },
            }
        )
    except Exception as exc:
        logger.error(f"get_openrouter_balance failed: {exc}")
        return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


@settings_bp.route("/test-connection", methods=["POST"])
@login_required
def test_connection():
    data = request.get_json() or {}
    service = (data.get("service") or "").strip().lower()
    if service == "openrouter":
        return get_openrouter_balance()
    return jsonify({"code": 0, "msg": f"Unsupported test target: {service}", "data": None}), 400
