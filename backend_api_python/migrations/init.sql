-- ZhiYiQuant V1 desktop SQLite schema

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS zhiyiquant_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT DEFAULT '',
    nickname TEXT DEFAULT '',
    avatar TEXT DEFAULT '/avatar2.jpg',
    notification_settings TEXT DEFAULT '{}',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS zhiyiquant_strategies_trading (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT DEFAULT 'IndicatorStrategy',
    market_category TEXT DEFAULT 'Crypto',
    execution_mode TEXT DEFAULT 'signal',
    notification_config TEXT DEFAULT '{}',
    status TEXT DEFAULT 'stopped',
    symbol TEXT DEFAULT '',
    timeframe TEXT DEFAULT '1D',
    initial_capital REAL DEFAULT 1000,
    leverage INTEGER DEFAULT 1,
    market_type TEXT DEFAULT 'swap',
    exchange_config TEXT DEFAULT '{}',
    indicator_config TEXT DEFAULT '{}',
    trading_config TEXT DEFAULT '{}',
    ai_model_config TEXT DEFAULT '{}',
    decide_interval INTEGER DEFAULT 300,
    strategy_group_id TEXT DEFAULT '',
    group_base_name TEXT DEFAULT '',
    last_rebalance_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategies_user_id ON zhiyiquant_strategies_trading(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategies_status ON zhiyiquant_strategies_trading(status);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategies_group ON zhiyiquant_strategies_trading(strategy_group_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_strategy_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES zhiyiquant_strategies_trading(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT DEFAULT 'long',
    size REAL DEFAULT 0,
    entry_price REAL DEFAULT 0,
    current_price REAL DEFAULT 0,
    highest_price REAL DEFAULT 0,
    lowest_price REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    pnl_percent REAL DEFAULT 0,
    equity REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(strategy_id, symbol, side)
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_positions_user_id ON zhiyiquant_strategy_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_positions_strategy_id ON zhiyiquant_strategy_positions(strategy_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_strategy_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES zhiyiquant_strategies_trading(id) ON DELETE CASCADE,
    symbol TEXT DEFAULT '',
    type TEXT DEFAULT '',
    price REAL DEFAULT 0,
    amount REAL DEFAULT 0,
    value REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    commission_ccy TEXT DEFAULT '',
    profit REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_trades_user_id ON zhiyiquant_strategy_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_trades_strategy_id ON zhiyiquant_strategy_trades(strategy_id);

CREATE TABLE IF NOT EXISTS pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES zhiyiquant_strategies_trading(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_ts INTEGER,
    market_type TEXT DEFAULT 'swap',
    order_type TEXT DEFAULT 'market',
    amount REAL DEFAULT 0,
    price REAL DEFAULT 0,
    execution_mode TEXT DEFAULT 'signal',
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 10,
    last_error TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    dispatch_note TEXT DEFAULT '',
    exchange_id TEXT DEFAULT '',
    exchange_order_id TEXT DEFAULT '',
    exchange_response_json TEXT DEFAULT '{}',
    filled REAL DEFAULT 0,
    avg_price REAL DEFAULT 0,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pending_orders_user_id ON pending_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_orders_status ON pending_orders(status);
CREATE INDEX IF NOT EXISTS idx_pending_orders_strategy_id ON pending_orders(strategy_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_strategy_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    strategy_id INTEGER REFERENCES zhiyiquant_strategies_trading(id) ON DELETE CASCADE,
    symbol TEXT DEFAULT '',
    signal_type TEXT DEFAULT '',
    channels TEXT DEFAULT '',
    title TEXT DEFAULT '',
    message TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_notifications_user_id ON zhiyiquant_strategy_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_strategy_notifications_strategy_id ON zhiyiquant_strategy_notifications(strategy_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_indicator_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    code TEXT DEFAULT '',
    description TEXT DEFAULT '',
    createtime INTEGER,
    updatetime INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_indicator_codes_user_id ON zhiyiquant_indicator_codes(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, market, symbol)
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_watchlist_user_id ON zhiyiquant_watchlist(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_analysis_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence INTEGER DEFAULT 50,
    price_at_analysis REAL DEFAULT 0,
    entry_price REAL DEFAULT 0,
    stop_loss REAL DEFAULT 0,
    take_profit REAL DEFAULT 0,
    summary TEXT DEFAULT '',
    reasons TEXT DEFAULT '[]',
    risks TEXT DEFAULT '[]',
    scores TEXT DEFAULT '{}',
    indicators_snapshot TEXT DEFAULT '{}',
    raw_result TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    actual_outcome TEXT DEFAULT '',
    actual_return_pct REAL DEFAULT 0,
    was_correct INTEGER,
    user_feedback TEXT DEFAULT '',
    feedback_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_analysis_memory_symbol ON zhiyiquant_analysis_memory(market, symbol);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_analysis_memory_user ON zhiyiquant_analysis_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_analysis_memory_created ON zhiyiquant_analysis_memory(created_at DESC);

CREATE TABLE IF NOT EXISTS zhiyiquant_backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    indicator_id INTEGER,
    market TEXT NOT NULL DEFAULT '',
    symbol TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    start_date TEXT NOT NULL DEFAULT '',
    end_date TEXT NOT NULL DEFAULT '',
    initial_capital REAL DEFAULT 10000,
    commission REAL DEFAULT 0.001,
    slippage REAL DEFAULT 0,
    leverage INTEGER DEFAULT 1,
    trade_direction TEXT DEFAULT 'long',
    strategy_config TEXT DEFAULT '{}',
    status TEXT DEFAULT 'success',
    error_message TEXT DEFAULT '',
    result_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_backtest_runs_user_id ON zhiyiquant_backtest_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_zhiyiquant_backtest_runs_indicator_id ON zhiyiquant_backtest_runs(indicator_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_exchange_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    name TEXT DEFAULT '',
    exchange_id TEXT NOT NULL,
    api_key_hint TEXT DEFAULT '',
    encrypted_config TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_exchange_credentials_user_id ON zhiyiquant_exchange_credentials(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_manual_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT DEFAULT '',
    side TEXT DEFAULT 'long',
    quantity REAL NOT NULL DEFAULT 0,
    entry_price REAL NOT NULL DEFAULT 0,
    entry_time INTEGER,
    notes TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    group_name TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, market, symbol, side, group_name)
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_manual_positions_user_id ON zhiyiquant_manual_positions(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_manual_positions_closed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_position_id INTEGER,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT DEFAULT '',
    side TEXT DEFAULT 'long',
    quantity REAL NOT NULL DEFAULT 0,
    entry_price REAL NOT NULL DEFAULT 0,
    entry_time INTEGER,
    close_price REAL NOT NULL DEFAULT 0,
    close_time INTEGER,
    realized_pnl REAL DEFAULT 0,
    realized_pnl_percent REAL DEFAULT 0,
    hold_seconds INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    close_note TEXT DEFAULT '',
    group_name TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_manual_positions_closed_user_id ON zhiyiquant_manual_positions_closed(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_position_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    position_id INTEGER,
    market TEXT DEFAULT '',
    symbol TEXT DEFAULT '',
    alert_type TEXT NOT NULL,
    threshold REAL NOT NULL DEFAULT 0,
    notification_config TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    is_triggered INTEGER DEFAULT 0,
    repeat_interval INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_position_alerts_user_id ON zhiyiquant_position_alerts(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_position_monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES zhiyiquant_users(id) ON DELETE CASCADE,
    name TEXT DEFAULT '',
    position_ids TEXT DEFAULT '[]',
    monitor_type TEXT DEFAULT 'ai',
    config TEXT DEFAULT '{}',
    notification_config TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1,
    next_run_at TIMESTAMP,
    last_run_at TIMESTAMP,
    last_result TEXT DEFAULT '{}',
    run_count INTEGER DEFAULT 0,
    last_error TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_position_monitors_user_id ON zhiyiquant_position_monitors(user_id);

CREATE TABLE IF NOT EXISTS zhiyiquant_market_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    exchange TEXT DEFAULT '',
    currency TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    is_hot INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(market, symbol)
);

CREATE INDEX IF NOT EXISTS idx_zhiyiquant_market_symbols_market ON zhiyiquant_market_symbols(market);

INSERT OR IGNORE INTO zhiyiquant_market_symbols (market, symbol, name, exchange, currency, is_active, is_hot, sort_order) VALUES
('Crypto', 'BTC/USDT', 'Bitcoin', 'BINANCE', 'USDT', 1, 1, 100),
('Crypto', 'ETH/USDT', 'Ethereum', 'BINANCE', 'USDT', 1, 1, 99),
('Crypto', 'SOL/USDT', 'Solana', 'BINANCE', 'USDT', 1, 1, 98),
('USStock', 'AAPL', 'Apple', 'NASDAQ', 'USD', 1, 1, 100),
('USStock', 'NVDA', 'NVIDIA', 'NASDAQ', 'USD', 1, 1, 99),
('USStock', 'TSLA', 'Tesla', 'NASDAQ', 'USD', 1, 1, 98),
('AShare', '600519', '贵州茅台', 'SSE', 'CNY', 1, 1, 100),
('AShare', '300750', '宁德时代', 'SZSE', 'CNY', 1, 1, 99),
('HShare', '00700', '腾讯控股', 'HKEX', 'HKD', 1, 1, 100),
('HShare', '09988', '阿里巴巴', 'HKEX', 'HKD', 1, 1, 99),
('Forex', 'EURUSD', 'Euro / US Dollar', 'FX', 'USD', 1, 1, 100),
('Forex', 'USDJPY', 'US Dollar / Japanese Yen', 'FX', 'JPY', 1, 1, 99),
('Futures', 'GC', 'Gold Futures', 'COMEX', 'USD', 1, 1, 100),
('Futures', 'CL', 'Crude Oil Futures', 'NYMEX', 'USD', 1, 1, 99);
