"""
Desktop runtime configuration.
"""
import os


class MetaConfig(type):
    @property
    def HOST(cls):
        return os.getenv('PYTHON_API_HOST', '127.0.0.1')

    @property
    def PORT(cls):
        return int(os.getenv('PYTHON_API_PORT', 5051))

    @property
    def DEBUG(cls):
        return os.getenv('PYTHON_API_DEBUG', 'false').lower() == 'true'

    @property
    def APP_NAME(cls):
        return 'ZhiyiQuant Desktop Engine'

    @property
    def VERSION(cls):
        return '1.0.4'

    @property
    def SECRET_KEY(cls):
        return os.getenv('SECRET_KEY', 'zhiyiquant-secret-key-change-me')

    @property
    def LOG_LEVEL(cls):
        return os.getenv('LOG_LEVEL', 'INFO')

    @property
    def LOG_DIR(cls):
        return os.getenv('LOG_DIR', 'logs')

    @property
    def LOG_FILE(cls):
        return os.getenv('LOG_FILE', 'app.log')

    @property
    def LOG_MAX_BYTES(cls):
        return int(os.getenv('LOG_MAX_BYTES', 10 * 1024 * 1024))

    @property
    def LOG_BACKUP_COUNT(cls):
        return int(os.getenv('LOG_BACKUP_COUNT', 5))

    @property
    def CORS_ORIGINS(cls):
        from app.utils.config_loader import load_addon_config
        value = load_addon_config().get('app', {}).get('cors_origins')
        return value if value else os.getenv('CORS_ORIGINS', '*')

    @property
    def RATE_LIMIT(cls):
        from app.utils.config_loader import load_addon_config
        value = load_addon_config().get('app', {}).get('rate_limit')
        return int(value) if value is not None else int(os.getenv('RATE_LIMIT', 100))

    @property
    def ENABLE_CACHE(cls):
        from app.utils.config_loader import load_addon_config
        value = load_addon_config().get('app', {}).get('enable_cache')
        if value is not None:
            return bool(value)
        return os.getenv('ENABLE_CACHE', 'false').lower() == 'true'

    @property
    def ENABLE_REQUEST_LOG(cls):
        from app.utils.config_loader import load_addon_config
        value = load_addon_config().get('app', {}).get('enable_request_log')
        if value is not None:
            return bool(value)
        return os.getenv('ENABLE_REQUEST_LOG', 'true').lower() == 'true'

    @property
    def ENABLE_AI_ANALYSIS(cls):
        from app.utils.config_loader import load_addon_config
        value = load_addon_config().get('app', {}).get('enable_ai_analysis')
        if value is not None:
            return bool(value)
        return os.getenv('ENABLE_AI_ANALYSIS', 'true').lower() == 'true'


class Config(metaclass=MetaConfig):
    @classmethod
    def get_log_path(cls) -> str:
        return os.path.join(cls.LOG_DIR, cls.LOG_FILE)
