"""
Settings API - 读取和保存 .env 配置

Admin-only endpoints for system configuration management.
"""
import os
import re
from flask import Blueprint, request, jsonify
from app.utils.logger import get_logger
from app.utils.config_loader import clear_config_cache
from app.utils.auth import login_required, admin_required

logger = get_logger(__name__)

settings_bp = Blueprint('settings', __name__)

# .env 文件路径
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')

# 配置项定义（分组）- 按功能模块划分，每个配置项包含描述
CONFIG_SCHEMA = {
    # ==================== 1. 服务配置 ====================
    'server': {
        'title': 'Server Configuration',
        'icon': 'cloud-server',
        'order': 1,
        'items': [
            {
                'key': 'PYTHON_API_HOST',
                'label': 'Listen Address',
                'type': 'text',
                'default': '0.0.0.0',
                'description': 'Server listen address. 0.0.0.0 allows external access, 127.0.0.1 for local only'
            },
            {
                'key': 'PYTHON_API_PORT',
                'label': 'Port',
                'type': 'number',
                'default': '5000',
                'description': 'Server listen port, default 5000'
            },
            {
                'key': 'PYTHON_API_DEBUG',
                'label': 'Debug Mode',
                'type': 'boolean',
                'default': 'False',
                'description': 'Enable debug mode for development. Disable in production'
            },
        ]
    },

    # ==================== 2. 安全认证 ====================
    'auth': {
        'title': 'Security & Authentication',
        'icon': 'lock',
        'order': 2,
        'items': [
            {
                'key': 'SECRET_KEY',
                'label': 'Secret Key',
                'type': 'password',
                'default': 'zhiyiquant-secret-key-change-me',
                'description': 'JWT signing secret key. MUST change in production for security'
            },
            {
                'key': 'ADMIN_USER',
                'label': 'Admin Username',
                'type': 'text',
                'default': 'zhiyiquant',
                'description': 'Administrator login username'
            },
            {
                'key': 'ADMIN_PASSWORD',
                'label': 'Admin Password',
                'type': 'password',
                'default': '123456',
                'description': 'Administrator login password. MUST change in production'
            },
            {
                'key': 'ADMIN_EMAIL',
                'label': 'Admin Email',
                'type': 'text',
                'default': 'admin@example.com',
                'description': 'Administrator email for password reset and notifications'
            },
        ]
    },

    # ==================== 3. AI/LLM 配置 ====================
    'ai': {
        'title': 'AI / LLM Configuration',
        'icon': 'robot',
        'order': 3,
        'items': [
            {
                'key': 'LLM_PROVIDER',
                'label': 'LLM Provider',
                'type': 'select',
                'default': 'openrouter',
                'options': [
                    {'value': 'openrouter', 'label': 'OpenRouter (Multi-model gateway)'},
                    {'value': 'openai', 'label': 'OpenAI Direct'},
                    {'value': 'google', 'label': 'Google Gemini'},
                    {'value': 'deepseek', 'label': 'DeepSeek'},
                    {'value': 'grok', 'label': 'xAI Grok'},
                ],
                'description': 'Select your preferred LLM provider'
            },
            # OpenRouter
            {
                'key': 'OPENROUTER_API_KEY',
                'label': 'OpenRouter API Key',
                'type': 'password',
                'required': False,
                'link': 'https://openrouter.ai/keys',
                'link_text': 'settings.link.getApiKey',
                'description': 'OpenRouter API key. Supports 100+ models via single API',
                'group': 'openrouter'
            },
            {
                'key': 'OPENROUTER_MODEL',
                'label': 'OpenRouter Model',
                'type': 'text',
                'default': 'openai/gpt-4o',
                'link': 'https://openrouter.ai/models',
                'link_text': 'settings.link.viewModels',
                'description': 'Model ID, e.g. openai/gpt-4o, anthropic/claude-3.5-sonnet',
                'group': 'openrouter'
            },
            # OpenAI Direct
            {
                'key': 'OPENAI_API_KEY',
                'label': 'OpenAI API Key',
                'type': 'password',
                'required': False,
                'link': 'https://platform.openai.com/api-keys',
                'link_text': 'settings.link.getApiKey',
                'description': 'OpenAI official API key',
                'group': 'openai'
            },
            {
                'key': 'OPENAI_MODEL',
                'label': 'OpenAI Model',
                'type': 'text',
                'default': 'gpt-4o',
                'description': 'Model name: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.',
                'group': 'openai'
            },
            {
                'key': 'OPENAI_BASE_URL',
                'label': 'OpenAI Base URL',
                'type': 'text',
                'default': 'https://api.openai.com/v1',
                'description': 'Custom API endpoint (for proxies or Azure)',
                'group': 'openai'
            },
            # Google Gemini
            {
                'key': 'GOOGLE_API_KEY',
                'label': 'Google API Key',
                'type': 'password',
                'required': False,
                'link': 'https://aistudio.google.com/apikey',
                'link_text': 'settings.link.getApiKey',
                'description': 'Google AI Studio API key for Gemini',
                'group': 'google'
            },
            {
                'key': 'GOOGLE_MODEL',
                'label': 'Gemini Model',
                'type': 'text',
                'default': 'gemini-1.5-flash',
                'description': 'Model: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp',
                'group': 'google'
            },
            # DeepSeek
            {
                'key': 'DEEPSEEK_API_KEY',
                'label': 'DeepSeek API Key',
                'type': 'password',
                'required': False,
                'link': 'https://platform.deepseek.com/api_keys',
                'link_text': 'settings.link.getApiKey',
                'description': 'DeepSeek API key',
                'group': 'deepseek'
            },
            {
                'key': 'DEEPSEEK_MODEL',
                'label': 'DeepSeek Model',
                'type': 'text',
                'default': 'deepseek-chat',
                'description': 'Model: deepseek-chat, deepseek-coder',
                'group': 'deepseek'
            },
            {
                'key': 'DEEPSEEK_BASE_URL',
                'label': 'DeepSeek Base URL',
                'type': 'text',
                'default': 'https://api.deepseek.com/v1',
                'description': 'DeepSeek API endpoint',
                'group': 'deepseek'
            },
            # xAI Grok
            {
                'key': 'GROK_API_KEY',
                'label': 'Grok API Key',
                'type': 'password',
                'required': False,
                'link': 'https://console.x.ai/',
                'link_text': 'settings.link.getApiKey',
                'description': 'xAI Grok API key',
                'group': 'grok'
            },
            {
                'key': 'GROK_MODEL',
                'label': 'Grok Model',
                'type': 'text',
                'default': 'grok-beta',
                'description': 'Model: grok-beta, grok-2',
                'group': 'grok'
            },
            {
                'key': 'GROK_BASE_URL',
                'label': 'Grok Base URL',
                'type': 'text',
                'default': 'https://api.x.ai/v1',
                'description': 'xAI Grok API endpoint',
                'group': 'grok'
            },
            # Common settings
            {
                'key': 'OPENROUTER_TEMPERATURE',
                'label': 'Temperature',
                'type': 'number',
                'default': '0.7',
                'description': 'Model creativity (0-1). Lower = more deterministic'
            },
            {
                'key': 'OPENROUTER_TIMEOUT',
                'label': 'Request Timeout (sec)',
                'type': 'number',
                'default': '300',
                'description': 'API request timeout in seconds'
            },
            {
                'key': 'AI_MODELS_JSON',
                'label': 'Custom Models (JSON)',
                'type': 'text',
                'default': '{}',
                'required': False,
                'description': 'Custom model list in JSON format for model selector'
            },
        ]
    },

    # ==================== 4. 实盘交易 ====================
    'trading': {
        'title': 'Live Trading',
        'icon': 'stock',
        'order': 4,
        'items': [
            {
                'key': 'ENABLE_PENDING_ORDER_WORKER',
                'label': 'Enable Order Worker',
                'type': 'boolean',
                'default': 'True',
                'description': 'Enable background order processing worker for live trading'
            },
            {
                'key': 'PENDING_ORDER_STALE_SEC',
                'label': 'Order Stale Timeout (sec)',
                'type': 'number',
                'default': '90',
                'description': 'Mark pending order as stale after this many seconds'
            },
            {
                'key': 'ORDER_MODE',
                'label': 'Order Execution Mode',
                'type': 'select',
                'options': ['maker', 'market'],
                'default': 'maker',
                'description': 'maker: Limit order first (lower fees), market: Market order (instant fill)'
            },
            {
                'key': 'MAKER_WAIT_SEC',
                'label': 'Limit Order Wait (sec)',
                'type': 'number',
                'default': '10',
                'description': 'Wait time for limit order fill before switching to market order'
            },
            {
                'key': 'MAKER_OFFSET_BPS',
                'label': 'Limit Order Offset (bps)',
                'type': 'number',
                'default': '2',
                'description': 'Price offset in basis points (1bps=0.01%). Buy: price*(1-offset), Sell: price*(1+offset)'
            },
        ]
    },

    # ==================== 5. 策略执行 ====================
    'strategy': {
        'title': 'Strategy Execution',
        'icon': 'fund',
        'order': 5,
        'items': [
            {
                'key': 'DISABLE_RESTORE_RUNNING_STRATEGIES',
                'label': 'Disable Auto Restore',
                'type': 'boolean',
                'default': 'False',
                'description': 'Disable automatic restore of running strategies on server restart'
            },
            {
                'key': 'STRATEGY_TICK_INTERVAL_SEC',
                'label': 'Tick Interval (sec)',
                'type': 'number',
                'default': '10',
                'description': 'Strategy main loop tick interval in seconds'
            },
            {
                'key': 'PRICE_CACHE_TTL_SEC',
                'label': 'Price Cache TTL (sec)',
                'type': 'number',
                'default': '10',
                'description': 'Time-to-live for cached price data in seconds'
            },
        ]
    },

    # ==================== 6. 数据源配置 ====================
    'data_source': {
        'title': 'Data Sources',
        'icon': 'database',
        'order': 6,
        'items': [
            {
                'key': 'DATA_SOURCE_TIMEOUT',
                'label': 'Default Timeout (sec)',
                'type': 'number',
                'default': '30',
                'description': 'Default timeout for all data source requests'
            },
            {
                'key': 'DATA_SOURCE_RETRY',
                'label': 'Retry Count',
                'type': 'number',
                'default': '3',
                'description': 'Number of retry attempts on data source failure'
            },
            {
                'key': 'DATA_SOURCE_RETRY_BACKOFF',
                'label': 'Retry Backoff (sec)',
                'type': 'number',
                'default': '0.5',
                'description': 'Backoff time between retry attempts'
            },
            {
                'key': 'CCXT_DEFAULT_EXCHANGE',
                'label': 'CCXT Default Exchange',
                'type': 'text',
                'default': 'coinbase',
                'link': 'https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets',
                'link_text': 'settings.link.supportedExchanges',
                'description': 'Default exchange for CCXT crypto data (binance, coinbase, okx, etc.)'
            },
            {
                'key': 'CCXT_TIMEOUT',
                'label': 'CCXT Timeout (ms)',
                'type': 'number',
                'default': '10000',
                'description': 'CCXT request timeout in milliseconds'
            },
            {
                'key': 'CCXT_PROXY',
                'label': 'CCXT Proxy',
                'type': 'text',
                'required': False,
                'description': 'Proxy URL for CCXT requests (e.g. socks5h://127.0.0.1:1080)'
            },
            {
                'key': 'FINNHUB_API_KEY',
                'label': 'Finnhub API Key',
                'type': 'password',
                'required': False,
                'link': 'https://finnhub.io/register',
                'link_text': 'settings.link.freeRegister',
                'description': 'Finnhub API key for US stock data (free tier available)'
            },
            {
                'key': 'FINNHUB_TIMEOUT',
                'label': 'Finnhub Timeout (sec)',
                'type': 'number',
                'default': '10',
                'description': 'Finnhub API request timeout'
            },
            {
                'key': 'FINNHUB_RATE_LIMIT',
                'label': 'Finnhub Rate Limit',
                'type': 'number',
                'default': '60',
                'description': 'Finnhub API rate limit (requests per minute)'
            },
            {
                'key': 'TIINGO_API_KEY',
                'label': 'Tiingo API Key',
                'type': 'password',
                'required': False,
                'link': 'https://www.tiingo.com/account/api/token',
                'link_text': 'settings.link.getToken',
                'description': 'Tiingo API key for Forex/Metals data (free tier does not support 1-minute data)'
            },
            {
                'key': 'TIINGO_TIMEOUT',
                'label': 'Tiingo Timeout (sec)',
                'type': 'number',
                'default': '10',
                'description': 'Tiingo API request timeout'
            },
            {
                'key': 'AKSHARE_TIMEOUT',
                'label': 'Akshare Timeout (sec)',
                'type': 'number',
                'default': '30',
                'description': 'Akshare API timeout for China A-share data'
            },
            {
                'key': 'YFINANCE_TIMEOUT',
                'label': 'YFinance Timeout (sec)',
                'type': 'number',
                'default': '30',
                'description': 'Yahoo Finance API timeout'
            },
        ]
    },

    # ==================== 7. 邮件配置 (公共 SMTP) ====================
    'email': {
        'title': 'Email (SMTP)',
        'icon': 'mail',
        'order': 7,
        'items': [
            {
                'key': 'SMTP_HOST',
                'label': 'SMTP Server',
                'type': 'text',
                'required': False,
                'description': 'SMTP server hostname (e.g. smtp.gmail.com)'
            },
            {
                'key': 'SMTP_PORT',
                'label': 'SMTP Port',
                'type': 'number',
                'default': '587',
                'description': 'SMTP port (587 for TLS, 465 for SSL, 25 for plain)'
            },
            {
                'key': 'SMTP_USER',
                'label': 'SMTP Username',
                'type': 'text',
                'required': False,
                'description': 'SMTP authentication username (usually email address)'
            },
            {
                'key': 'SMTP_PASSWORD',
                'label': 'SMTP Password',
                'type': 'password',
                'required': False,
                'description': 'SMTP authentication password or app-specific password'
            },
            {
                'key': 'SMTP_FROM',
                'label': 'Sender Address',
                'type': 'text',
                'required': False,
                'description': 'Email sender address (From header)'
            },
            {
                'key': 'SMTP_USE_TLS',
                'label': 'Use TLS',
                'type': 'boolean',
                'default': 'True',
                'description': 'Enable STARTTLS encryption (recommended for port 587)'
            },
            {
                'key': 'SMTP_USE_SSL',
                'label': 'Use SSL',
                'type': 'boolean',
                'default': 'False',
                'description': 'Enable SSL encryption (for port 465)'
            },
        ]
    },

    # ==================== 9. 短信配置 ====================
    'sms': {
        'title': 'SMS (Twilio)',
        'icon': 'phone',
        'order': 8,
        'items': [
            {
                'key': 'TWILIO_ACCOUNT_SID',
                'label': 'Account SID',
                'type': 'password',
                'required': False,
                'link': 'https://console.twilio.com/',
                'link_text': 'settings.link.getApi',
                'description': 'Twilio Account SID from console dashboard'
            },
            {
                'key': 'TWILIO_AUTH_TOKEN',
                'label': 'Auth Token',
                'type': 'password',
                'required': False,
                'description': 'Twilio Auth Token from console dashboard'
            },
            {
                'key': 'TWILIO_FROM_NUMBER',
                'label': 'Sender Number',
                'type': 'text',
                'required': False,
                'description': 'Twilio phone number for sending SMS (e.g. +1234567890)'
            },
        ]
    },

    # ==================== 9. AI Agent 配置 ====================
    'agent': {
        'title': 'AI Agent',
        'icon': 'experiment',
        'order': 9,
        'items': [
            {
                'key': 'ENABLE_AGENT_MEMORY',
                'label': 'Enable Agent Memory',
                'type': 'boolean',
                'default': 'True',
                'description': 'Enable AI agent memory for learning from past trades'
            },
            {
                'key': 'AGENT_MEMORY_ENABLE_VECTOR',
                'label': 'Enable Vector Search',
                'type': 'boolean',
                'default': 'True',
                'description': 'Enable local vector similarity search for memory retrieval'
            },
            {
                'key': 'AGENT_MEMORY_EMBEDDING_DIM',
                'label': 'Embedding Dimension',
                'type': 'number',
                'default': '256',
                'description': 'Vector embedding dimension for memory storage'
            },
            {
                'key': 'AGENT_MEMORY_TOP_K',
                'label': 'Retrieval Top-K',
                'type': 'number',
                'default': '5',
                'description': 'Number of similar memories to retrieve'
            },
            {
                'key': 'AGENT_MEMORY_CANDIDATE_LIMIT',
                'label': 'Candidate Limit',
                'type': 'number',
                'default': '500',
                'description': 'Maximum candidates for similarity search'
            },
            {
                'key': 'AGENT_MEMORY_HALF_LIFE_DAYS',
                'label': 'Recency Half-life (days)',
                'type': 'number',
                'default': '30',
                'description': 'Time decay half-life for memory recency scoring'
            },
            {
                'key': 'AGENT_MEMORY_W_SIM',
                'label': 'Similarity Weight',
                'type': 'number',
                'default': '0.75',
                'description': 'Weight for similarity score in memory ranking (0-1)'
            },
            {
                'key': 'AGENT_MEMORY_W_RECENCY',
                'label': 'Recency Weight',
                'type': 'number',
                'default': '0.20',
                'description': 'Weight for recency score in memory ranking (0-1)'
            },
            {
                'key': 'AGENT_MEMORY_W_RETURNS',
                'label': 'Returns Weight',
                'type': 'number',
                'default': '0.05',
                'description': 'Weight for returns score in memory ranking (0-1)'
            },
            {
                'key': 'ENABLE_REFLECTION_WORKER',
                'label': 'Enable Auto Reflection',
                'type': 'boolean',
                'default': 'False',
                'description': 'Enable background worker for automatic trade reflection'
            },
            {
                'key': 'REFLECTION_WORKER_INTERVAL_SEC',
                'label': 'Reflection Interval (sec)',
                'type': 'number',
                'default': '86400',
                'description': 'Interval between automatic reflection runs (default: 24h)'
            },
        ]
    },

    # ==================== 10. 网络代理 ====================
    'network': {
        'title': 'Network & Proxy',
        'icon': 'global',
        'order': 10,
        'items': [
            {
                'key': 'PROXY_HOST',
                'label': 'Proxy Host',
                'type': 'text',
                'default': '127.0.0.1',
                'description': 'Proxy server hostname or IP'
            },
            {
                'key': 'PROXY_PORT',
                'label': 'Proxy Port',
                'type': 'text',
                'required': False,
                'description': 'Proxy server port (leave empty to disable proxy)'
            },
            {
                'key': 'PROXY_SCHEME',
                'label': 'Proxy Protocol',
                'type': 'select',
                'options': ['socks5h', 'socks5', 'http', 'https'],
                'default': 'socks5h',
                'description': 'Proxy protocol type. socks5h: SOCKS5 with DNS resolution'
            },
            {
                'key': 'PROXY_URL',
                'label': 'Full Proxy URL',
                'type': 'text',
                'required': False,
                'description': 'Complete proxy URL (overrides above settings if set)'
            },
        ]
    },

    # ==================== 11. 搜索配置 ====================
    'search': {
        'title': 'Web Search',
        'icon': 'search',
        'order': 11,
        'items': [
            {
                'key': 'SEARCH_PROVIDER',
                'label': 'Search Provider',
                'type': 'select',
                'options': ['bocha', 'tavily', 'google', 'bing', 'none'],
                'default': 'bocha',
                'description': 'Web search provider for AI research features. Bocha recommended for A-share news'
            },
            {
                'key': 'SEARCH_MAX_RESULTS',
                'label': 'Max Results',
                'type': 'number',
                'default': '10',
                'description': 'Maximum search results to return'
            },
            # Tavily Search API
            {
                'key': 'TAVILY_API_KEYS',
                'label': 'Tavily API Keys',
                'type': 'password',
                'required': False,
                'link': 'https://tavily.com/',
                'link_text': 'settings.link.getApiKey',
                'description': 'Tavily Search API keys, comma-separated for rotation. Free 1000 requests/month'
            },
            # Bocha Search API
            {
                'key': 'BOCHA_API_KEYS',
                'label': 'Bocha API Keys',
                'type': 'password',
                'required': False,
                'link': 'https://bochaai.com/',
                'link_text': 'settings.link.getApiKey',
                'description': 'Bocha Search API keys, comma-separated for rotation. Best for A-share news'
            },
            # SerpAPI
            {
                'key': 'SERPAPI_KEYS',
                'label': 'SerpAPI Keys',
                'type': 'password',
                'required': False,
                'link': 'https://serpapi.com/',
                'link_text': 'settings.link.getApiKey',
                'description': 'SerpAPI keys for Google/Bing search, comma-separated for rotation'
            },
            {
                'key': 'SEARCH_GOOGLE_API_KEY',
                'label': 'Google API Key',
                'type': 'password',
                'required': False,
                'link': 'https://developers.google.com/custom-search/v1/introduction',
                'link_text': 'settings.link.applyApi',
                'description': 'Google Custom Search JSON API key'
            },
            {
                'key': 'SEARCH_GOOGLE_CX',
                'label': 'Google Search Engine ID',
                'type': 'text',
                'required': False,
                'link': 'https://programmablesearchengine.google.com/controlpanel/all',
                'link_text': 'settings.link.createSearchEngine',
                'description': 'Google Programmable Search Engine ID (CX)'
            },
            {
                'key': 'SEARCH_BING_API_KEY',
                'label': 'Bing API Key',
                'type': 'password',
                'required': False,
                'link': 'https://www.microsoft.com/en-us/bing/apis/bing-web-search-api',
                'link_text': 'settings.link.applyApi',
                'description': 'Microsoft Bing Web Search API key'
            },
            {
                'key': 'INTERNAL_API_KEY',
                'label': 'Internal API Key',
                'type': 'password',
                'required': False,
                'description': 'Internal API authentication key for service-to-service calls'
            },
        ]
    },

    # ==================== 12. 注册与安全 ====================
    'security': {
        'title': 'Registration & Security',
        'icon': 'safety',
        'order': 12,
        'items': [
            {
                'key': 'ENABLE_REGISTRATION',
                'label': 'Enable Registration',
                'type': 'boolean',
                'default': 'True',
                'description': 'Allow new users to register accounts'
            },
            {
                'key': 'TURNSTILE_SITE_KEY',
                'label': 'Turnstile Site Key',
                'type': 'text',
                'required': False,
                'link': 'https://dash.cloudflare.com/?to=/:account/turnstile',
                'link_text': 'settings.link.getTurnstileKey',
                'description': 'Cloudflare Turnstile site key for CAPTCHA verification'
            },
            {
                'key': 'TURNSTILE_SECRET_KEY',
                'label': 'Turnstile Secret Key',
                'type': 'password',
                'required': False,
                'description': 'Cloudflare Turnstile secret key'
            },
            {
                'key': 'FRONTEND_URL',
                'label': 'Frontend URL',
                'type': 'text',
                'default': 'http://localhost:8080',
                'description': 'Frontend URL for OAuth redirects'
            },
            {
                'key': 'GOOGLE_CLIENT_ID',
                'label': 'Google Client ID',
                'type': 'text',
                'required': False,
                'link': 'https://console.cloud.google.com/apis/credentials',
                'link_text': 'settings.link.getGoogleCredentials',
                'description': 'Google OAuth Client ID'
            },
            {
                'key': 'GOOGLE_CLIENT_SECRET',
                'label': 'Google Client Secret',
                'type': 'password',
                'required': False,
                'description': 'Google OAuth Client Secret'
            },
            {
                'key': 'GOOGLE_REDIRECT_URI',
                'label': 'Google Redirect URI',
                'type': 'text',
                'default': 'http://localhost:5000/api/auth/oauth/google/callback',
                'description': 'Google OAuth callback URL'
            },
            {
                'key': 'GITHUB_CLIENT_ID',
                'label': 'GitHub Client ID',
                'type': 'text',
                'required': False,
                'link': 'https://github.com/settings/developers',
                'link_text': 'settings.link.getGithubCredentials',
                'description': 'GitHub OAuth Client ID'
            },
            {
                'key': 'GITHUB_CLIENT_SECRET',
                'label': 'GitHub Client Secret',
                'type': 'password',
                'required': False,
                'description': 'GitHub OAuth Client Secret'
            },
            {
                'key': 'GITHUB_REDIRECT_URI',
                'label': 'GitHub Redirect URI',
                'type': 'text',
                'default': 'http://localhost:5000/api/auth/oauth/github/callback',
                'description': 'GitHub OAuth callback URL'
            },
            {
                'key': 'SECURITY_IP_MAX_ATTEMPTS',
                'label': 'IP Max Failed Attempts',
                'type': 'number',
                'default': '10',
                'description': 'Block IP after this many failed login attempts'
            },
            {
                'key': 'SECURITY_IP_WINDOW_MINUTES',
                'label': 'IP Window (minutes)',
                'type': 'number',
                'default': '5',
                'description': 'Time window for counting IP failed attempts'
            },
            {
                'key': 'SECURITY_IP_BLOCK_MINUTES',
                'label': 'IP Block Duration (minutes)',
                'type': 'number',
                'default': '15',
                'description': 'How long to block IP after exceeding limit'
            },
            {
                'key': 'SECURITY_ACCOUNT_MAX_ATTEMPTS',
                'label': 'Account Max Failed Attempts',
                'type': 'number',
                'default': '5',
                'description': 'Lock account after this many failed login attempts'
            },
            {
                'key': 'SECURITY_ACCOUNT_WINDOW_MINUTES',
                'label': 'Account Window (minutes)',
                'type': 'number',
                'default': '60',
                'description': 'Time window for counting account failed attempts'
            },
            {
                'key': 'SECURITY_ACCOUNT_BLOCK_MINUTES',
                'label': 'Account Block Duration (minutes)',
                'type': 'number',
                'default': '30',
                'description': 'How long to lock account after exceeding limit'
            },
            {
                'key': 'VERIFICATION_CODE_EXPIRE_MINUTES',
                'label': 'Verification Code Expiry (minutes)',
                'type': 'number',
                'default': '10',
                'description': 'Email verification code validity period'
            },
            {
                'key': 'VERIFICATION_CODE_RATE_LIMIT',
                'label': 'Code Rate Limit (seconds)',
                'type': 'number',
                'default': '60',
                'description': 'Minimum time between verification code requests per email'
            },
            {
                'key': 'VERIFICATION_CODE_IP_HOURLY_LIMIT',
                'label': 'Code Hourly Limit per IP',
                'type': 'number',
                'default': '10',
                'description': 'Maximum verification codes per IP per hour'
            },
            {
                'key': 'VERIFICATION_CODE_MAX_ATTEMPTS',
                'label': 'Code Max Attempts',
                'type': 'number',
                'default': '5',
                'description': 'Maximum attempts to verify a code before lockout'
            },
            {
                'key': 'VERIFICATION_CODE_LOCK_MINUTES',
                'label': 'Code Lock Minutes',
                'type': 'number',
                'default': '30',
                'description': 'Lockout duration after exceeding max attempts'
            },
        ]
    },

    # ==================== 13. 计费配置 ====================
    'billing': {
        'title': 'Billing & Credits',
        'icon': 'dollar',
        'order': 13,
        'items': [
            {
                'key': 'BILLING_ENABLED',
                'label': 'Enable Billing',
                'type': 'boolean',
                'default': 'False',
                'description': 'Enable billing system. When enabled, users need credits to use certain features'
            },
            {
                'key': 'BILLING_VIP_BYPASS',
                'label': 'VIP Free',
                'type': 'boolean',
                'default': 'True',
                'description': 'VIP users can use all paid features for free during VIP period'
            },
            {
                'key': 'BILLING_COST_AI_ANALYSIS',
                'label': 'AI Analysis Cost',
                'type': 'number',
                'default': '10',
                'description': 'Credits consumed per AI analysis request'
            },
            {
                'key': 'BILLING_COST_STRATEGY_RUN',
                'label': 'Strategy Run Cost',
                'type': 'number',
                'default': '5',
                'description': 'Credits consumed when starting a strategy'
            },
            {
                'key': 'BILLING_COST_BACKTEST',
                'label': 'Backtest Cost',
                'type': 'number',
                'default': '3',
                'description': 'Credits consumed per backtest run'
            },
            {
                'key': 'BILLING_COST_PORTFOLIO_MONITOR',
                'label': 'Portfolio Monitor Cost',
                'type': 'number',
                'default': '8',
                'description': 'Credits consumed per portfolio AI monitoring run'
            },
            {
                'key': 'RECHARGE_TELEGRAM_URL',
                'label': 'Recharge Telegram URL',
                'type': 'text',
                'default': 'https://t.me/your_support_bot',
                'description': 'Telegram customer service URL for recharge inquiries'
            },
            {
                'key': 'CREDITS_REGISTER_BONUS',
                'label': 'Register Bonus',
                'type': 'number',
                'default': '100',
                'description': 'Credits awarded to new users on registration'
            },
            {
                'key': 'CREDITS_REFERRAL_BONUS',
                'label': 'Referral Bonus',
                'type': 'number',
                'default': '50',
                'description': 'Credits awarded to referrer when someone signs up with their code'
            },
        ]
    },

    # ==================== 14. 应用配置 ====================
    'app': {
        'title': 'Application',
        'icon': 'appstore',
        'order': 14,
        'items': [
            {
                'key': 'CORS_ORIGINS',
                'label': 'CORS Origins',
                'type': 'text',
                'default': '*',
                'description': 'Allowed CORS origins (* for all, or comma-separated list)'
            },
            {
                'key': 'RATE_LIMIT',
                'label': 'Rate Limit (req/min)',
                'type': 'number',
                'default': '100',
                'description': 'API rate limit per IP per minute'
            },
            {
                'key': 'ENABLE_CACHE',
                'label': 'Enable Cache',
                'type': 'boolean',
                'default': 'False',
                'description': 'Enable response caching for improved performance'
            },
            {
                'key': 'ENABLE_REQUEST_LOG',
                'label': 'Enable Request Log',
                'type': 'boolean',
                'default': 'True',
                'description': 'Log all API requests for debugging'
            },
            {
                'key': 'ENABLE_AI_ANALYSIS',
                'label': 'Enable AI Analysis',
                'type': 'boolean',
                'default': 'True',
                'description': 'Enable AI-powered market analysis features'
            },
        ]
    },
}


def read_env_file():
    """读取 .env 文件"""
    env_values = {}
    
    if not os.path.exists(ENV_FILE_PATH):
        logger.warning(f".env file not found at {ENV_FILE_PATH}")
        return env_values
    
    try:
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    env_values[key] = value
    except Exception as e:
        logger.error(f"Failed to read .env file: {e}")
    
    return env_values


def write_env_file(env_values):
    """写入 .env 文件，保留注释和格式"""
    lines = []
    existing_keys = set()
    
    # 读取原文件保留格式
    if os.path.exists(ENV_FILE_PATH):
        try:
            with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    original_line = line
                    stripped = line.strip()
                    
                    # 保留空行和注释
                    if not stripped or stripped.startswith('#'):
                        lines.append(original_line)
                        continue
                    
                    # 更新已存在的键
                    if '=' in stripped:
                        key = stripped.split('=', 1)[0].strip()
                        if key in env_values:
                            existing_keys.add(key)
                            value = env_values[key]
                            # 如果值包含特殊字符，用引号包裹
                            if ' ' in str(value) or '"' in str(value) or "'" in str(value):
                                lines.append(f'{key}="{value}"\n')
                            else:
                                lines.append(f'{key}={value}\n')
                        else:
                            lines.append(original_line)
                    else:
                        lines.append(original_line)
        except Exception as e:
            logger.error(f"Failed to read .env file for update: {e}")
    
    # 添加新的键
    new_keys = set(env_values.keys()) - existing_keys
    if new_keys:
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')
        lines.append('\n# Added by Settings UI\n')
        for key in sorted(new_keys):
            value = env_values[key]
            if ' ' in str(value) or '"' in str(value) or "'" in str(value):
                lines.append(f'{key}="{value}"\n')
            else:
                lines.append(f'{key}={value}\n')
    
    # 写入文件
    try:
        with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        logger.error(f"Failed to write .env file: {e}")
        return False


@settings_bp.route('/schema', methods=['GET'])
@login_required
@admin_required
def get_settings_schema():
    """获取配置项定义 (admin only)"""
    return jsonify({
        'code': 1,
        'msg': 'success',
        'data': CONFIG_SCHEMA
    })


@settings_bp.route('/values', methods=['GET'])
@login_required
@admin_required
def get_settings_values():
    """获取当前配置值 - 包括敏感信息（真实值）(admin only)"""
    env_values = read_env_file()
    
    # 构建返回数据，返回真实值
    result = {}
    for group_key, group in CONFIG_SCHEMA.items():
        result[group_key] = {}
        for item in group['items']:
            key = item['key']
            value = env_values.get(key, item.get('default', ''))
            result[group_key][key] = value
            # 标记密码类型是否已配置
            if item['type'] == 'password':
                result[group_key][f'{key}_configured'] = bool(value)
    
    return jsonify({
        'code': 1,
        'msg': 'success',
        'data': result
    })


@settings_bp.route('/save', methods=['POST'])
@login_required
@admin_required
def save_settings():
    """保存配置 (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 0, 'msg': 'Invalid request payload'})
        
        # 读取当前配置
        current_env = read_env_file()
        
        # 更新配置
        updates = {}
        for group_key, group_values in data.items():
            if group_key not in CONFIG_SCHEMA:
                continue
            
            for item in CONFIG_SCHEMA[group_key]['items']:
                key = item['key']
                if key in group_values:
                    new_value = group_values[key]
                    
                    # 空值处理
                    if new_value is None or new_value == '':
                        if not item.get('required', True):
                            updates[key] = ''
                    else:
                        updates[key] = str(new_value)
        
        # 合并更新
        current_env.update(updates)
        
        # 写入文件
        if write_env_file(current_env):
            # 清除配置缓存
            clear_config_cache()
            
            # 同步更新 os.environ，使 os.getenv() 立即读到新值（无需重启）
            for k, v in updates.items():
                os.environ[k] = str(v)
            
            return jsonify({
                'code': 1,
                'msg': 'Settings saved successfully',
                'data': {
                    'updated_keys': list(updates.keys()),
                    'requires_restart': False
                }
            })
        else:
            return jsonify({'code': 0, 'msg': 'Failed to save settings'})
    
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return jsonify({'code': 0, 'msg': f'Save failed: {str(e)}'})


@settings_bp.route('/openrouter-balance', methods=['GET'])
@login_required
@admin_required
def get_openrouter_balance():
    """查询 OpenRouter 账户余额 (admin only)"""
    try:
        import requests
        from app.config.api_keys import APIKeys
        
        api_key = APIKeys.OPENROUTER_API_KEY
        if not api_key:
            return jsonify({
                'code': 0, 
                'msg': 'OpenRouter API Key 未配置',
                'data': None
            })
        
        # 调用 OpenRouter API 查询余额
        # https://openrouter.ai/docs#limits
        resp = requests.get(
            'https://openrouter.ai/api/v1/auth/key',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            # OpenRouter 返回格式: {"data": {"label": "...", "usage": 0.0, "limit": null, ...}}
            key_data = data.get('data', {})
            usage = key_data.get('usage', 0)  # 已使用金额
            limit = key_data.get('limit')  # 限额（可能为null表示无限制）
            limit_remaining = key_data.get('limit_remaining')  # 剩余额度
            is_free_tier = key_data.get('is_free_tier', False)
            rate_limit = key_data.get('rate_limit', {})
            
            return jsonify({
                'code': 1,
                'msg': 'success',
                'data': {
                    'usage': round(usage, 4),  # 已使用（美元）
                    'limit': limit,  # 总限额
                    'limit_remaining': round(limit_remaining, 4) if limit_remaining is not None else None,  # 剩余额度
                    'is_free_tier': is_free_tier,
                    'rate_limit': rate_limit,
                    'label': key_data.get('label', '')
                }
            })
        elif resp.status_code == 401:
            return jsonify({
                'code': 0,
                'msg': 'API Key 无效或已过期',
                'data': None
            })
        else:
            return jsonify({
                'code': 0,
                'msg': f'查询失败: HTTP {resp.status_code}',
                'data': None
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'code': 0,
            'msg': '请求超时，请检查网络连接',
            'data': None
        })
    except Exception as e:
        logger.error(f"Get OpenRouter balance failed: {e}")
        return jsonify({
            'code': 0,
            'msg': f'查询失败: {str(e)}',
            'data': None
        })


@settings_bp.route('/test-connection', methods=['POST'])
@login_required
@admin_required
def test_connection():
    """测试API连接 (admin only)"""
    try:
        data = request.get_json()
        service = data.get('service')
        
        if service == 'openrouter':
            # 测试 OpenRouter 连接
            from app.services.llm import LLMService
            llm = LLMService()
            result = llm.test_connection()
            if result:
                return jsonify({'code': 1, 'msg': 'OpenRouter connection successful'})
            else:
                return jsonify({'code': 0, 'msg': 'OpenRouter connection failed'})
        
        elif service == 'finnhub':
            # 测试 Finnhub 连接
            import requests
            api_key = data.get('api_key') or os.getenv('FINNHUB_API_KEY')
            if not api_key:
                return jsonify({'code': 0, 'msg': 'API key is not configured'})
            resp = requests.get(
                f'https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}',
                timeout=10
            )
            if resp.status_code == 200:
                return jsonify({'code': 1, 'msg': 'Finnhub connection successful'})
            else:
                return jsonify({'code': 0, 'msg': f'Finnhub connection failed: {resp.status_code}'})
        
        return jsonify({'code': 0, 'msg': 'Unknown service'})
    
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return jsonify({'code': 0, 'msg': f'Test failed: {str(e)}'})
