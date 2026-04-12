"""
数据库和缓存配置
"""
import os
import sys

class MetaRedisConfig(type):
    """Redis 配置"""
    
    @property
    def HOST(cls):
        return os.getenv('REDIS_HOST', 'localhost')
    
    @property
    def PORT(cls):
        return int(os.getenv('REDIS_PORT', 6379))
    
    @property
    def PASSWORD(cls):
        return os.getenv('REDIS_PASSWORD', None)
    
    @property
    def DB(cls):
        return int(os.getenv('REDIS_DB', 0))
    
    @property
    def CONNECT_TIMEOUT(cls):
        return int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
    
    @property
    def SOCKET_TIMEOUT(cls):
        return int(os.getenv('REDIS_SOCKET_TIMEOUT', 5))
    
    @property
    def MAX_CONNECTIONS(cls):
        return int(os.getenv('REDIS_MAX_CONNECTIONS', 10))


class RedisConfig(metaclass=MetaRedisConfig):
    """Redis 缓存配置"""
    
    @classmethod
    def get_url(cls) -> str:
        """获取 Redis 连接 URL"""
        if cls.PASSWORD:
            return f"redis://:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DB}"
        return f"redis://{cls.HOST}:{cls.PORT}/{cls.DB}"


class MetaSQLiteConfig(type):
    """SQLite 配置"""
    
    @property
    def DATABASE_FILE(cls):
        override = os.getenv('SQLITE_DATABASE_FILE')
        if override and str(override).strip():
            return override

        app_dir_name = (os.getenv('ZHIYIQUANT_APP_DIR_NAME') or 'zhiyiquant').strip() or 'zhiyiquant'

        if sys.platform == 'win32':
            base_dir = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~')
            data_dir = os.path.join(base_dir, app_dir_name)
        elif sys.platform == 'darwin':
            data_dir = os.path.join(os.path.expanduser('~/Library/Application Support'), app_dir_name)
        else:
            base_dir = os.getenv('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
            data_dir = os.path.join(base_dir, app_dir_name)

        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            pass

        return os.path.join(data_dir, 'zhiyiquant.db')


class SQLiteConfig(metaclass=MetaSQLiteConfig):
    """SQLite 数据库配置"""
    
    @classmethod
    def get_path(cls) -> str:
        """获取数据库文件路径"""
        return cls.DATABASE_FILE


class MetaCacheConfig(type):
    """缓存业务配置"""
    
    @property
    def ENABLED(cls):
        # 强制默认关闭，除非环境变量显式开启
        return os.getenv('CACHE_ENABLED', 'False').lower() == 'true'

    @property
    def DEFAULT_EXPIRE(cls):
        return int(os.getenv('CACHE_EXPIRE', 300))

    @property
    def KLINE_CACHE_TTL(cls):
        return {
            '1m': 5,       # 1分钟K线缓存5秒
            '3m': 30,      # 3分钟K线缓存30秒
            '5m': 60,      # 5分钟K线缓存1分钟
            '15m': 300,    # 15分钟K线缓存5分钟
            '30m': 300,    # 30分钟K线缓存5分钟
            '1H': 300,     # 1小时K线缓存5分钟
            '4H': 300,     # 4小时K线缓存5分钟
            '1D': 300,     # 日K线缓存5分钟
            # 兼容小写
            '1h': 300,
            '4h': 300,
            '1d': 300,
        }

    @property
    def ANALYSIS_CACHE_TTL(cls):
        return 3600

    @property
    def PRICE_CACHE_TTL(cls):
        return 10


class CacheConfig(metaclass=MetaCacheConfig):
    """缓存配置"""
    pass
