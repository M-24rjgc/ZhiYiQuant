# ZhiYiQuant Changelog

This document records version updates, new features, bug fixes, and database migration instructions.

---

## V2.1.3 (2026-02-XX)

### 🚀 New Features

#### Cross-Sectional Strategy Support
- **Multi-Symbol Portfolio Management** - Added support for cross-sectional strategies that manage a portfolio of multiple symbols simultaneously
  - Strategy type selection: Single Symbol vs Cross-Sectional
  - Symbol list configuration: Select multiple symbols for portfolio management
  - Portfolio size: Configure the number of symbols to hold simultaneously
  - Long/Short ratio: Set the proportion of long vs short positions (0-1)
  - Rebalance frequency: Daily, Weekly, or Monthly portfolio rebalancing
  - Indicator execution: Indicators receive a `data` dictionary (symbol -> DataFrame) for cross-symbol analysis
  - Signal generation: Automatic buy/sell/close signals based on indicator rankings
  - Parallel execution: Multiple orders executed concurrently for efficiency
- **Backend Implementation**
  - Cross-sectional configurations stored in `trading_config` JSON field
  - New `_run_cross_sectional_strategy_loop` method in TradingExecutor
  - Automatic rebalancing based on configured frequency
  - Support for both long and short positions in the same portfolio
- **Frontend UI**
  - Strategy type selector in strategy creation/editing form
  - Conditional display of single-symbol vs cross-sectional configuration fields
  - Multi-select symbol picker for cross-sectional strategies
  - Full i18n support (Chinese and English)

See `docs/CROSS_SECTIONAL_STRATEGY_GUIDE_CN.md` or `docs/CROSS_SECTIONAL_STRATEGY_GUIDE_EN.md` for detailed usage instructions.

### 🐛 Bug Fixes
- Fixed decimal precision issues in exchange order quantities (Binance Spot LOT_SIZE filter errors)
- Improved `_dec_str` method across all exchange clients for accurate quantity formatting
- Enhanced quantity normalization to respect exchange precision requirements
- Fixed validation logic for cross-sectional strategies (now validates correct symbol list field)
- Fixed success message to show correct strategy count for cross-sectional strategies

### 📋 Database Migration

**Run the following SQL on your PostgreSQL database before deploying V2.1.3:**

```sql
-- ============================================================
-- ZhiYiQuant V2.1.3 Database Migration
-- Cross-Sectional Strategy Support
-- ============================================================

-- Add last_rebalance_at column to track rebalancing time for cross-sectional strategies
-- Note: Cross-sectional strategy configurations (symbol_list, portfolio_size, long_ratio, rebalance_frequency)
-- are stored in the trading_config JSON field, not as separate database columns.
-- This migration only adds the last_rebalance_at timestamp field which is needed for rebalancing logic.

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_strategies_trading' 
        AND column_name = 'last_rebalance_at'
    ) THEN
        ALTER TABLE qd_strategies_trading 
        ADD COLUMN last_rebalance_at TIMESTAMP;
        RAISE NOTICE 'Added last_rebalance_at column to qd_strategies_trading';
    ELSE
        RAISE NOTICE 'Column last_rebalance_at already exists';
    END IF;
END $$;
```

**Migration Notes:**
- This migration is safe to run multiple times (uses IF NOT EXISTS check)
- Cross-sectional strategy configurations are stored in the `trading_config` JSON field, so no additional columns are needed
- The `last_rebalance_at` field is used to track when the last rebalancing occurred for cross-sectional strategies
- If you don't run this migration, cross-sectional strategies will still work, but rebalancing frequency checks may not function correctly

---

## V2.1.2 (2026-02-01)

### 🚀 New Features

#### Indicator Parameter Support
- **External Parameter Passing** - Indicators can now declare parameters using `# @param` syntax that can be configured per-strategy
  - Supported types: `int`, `float`, `bool`, `str`
  - Parameters are displayed in the strategy creation form after selecting an indicator
  - Different strategies using the same indicator can have different parameter values
- **Cross-Indicator Calling** - Indicators can now call other indicators using `call_indicator(id_or_name, df)` function
  - Supports calling by indicator ID (number) or name (string)
  - Maximum call depth of 5 to prevent circular dependencies
  - Only allows calling own indicators or published community indicators

#### Parameter Declaration Syntax
```
# @param <name> <type> <default> <description>
```

| Field | Description | Example |
|-------|-------------|---------|
| name | Parameter name (variable name) | `ma_fast` |
| type | Data type: `int`, `float`, `bool`, `str` | `int` |
| default | Default value | `5` |
| description | Description (shown in UI tooltip) | `Short-term MA period` |

#### Example: Dual Moving Average with Parameters
```python
# @param sma_short int 14 Short-term MA period
# @param sma_long int 28 Long-term MA period

# Get parameters
sma_short_period = params.get('sma_short', 14)
sma_long_period = params.get('sma_long', 28)

my_indicator_name = "Dual MA Strategy"
my_indicator_description = f"SMA{sma_short_period}/{sma_long_period} crossover"

df = df.copy()
sma_short = df["close"].rolling(sma_short_period).mean()
sma_long = df["close"].rolling(sma_long_period).mean()

# Golden cross / Death cross
buy = (sma_short > sma_long) & (sma_short.shift(1) <= sma_long.shift(1))
sell = (sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))

df["buy"] = buy.fillna(False).astype(bool)
df["sell"] = sell.fillna(False).astype(bool)

# Chart markers
buy_marks = [df["low"].iloc[i] * 0.995 if df["buy"].iloc[i] else None for i in range(len(df))]
sell_marks = [df["high"].iloc[i] * 1.005 if df["sell"].iloc[i] else None for i in range(len(df))]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": f"SMA{sma_short_period}", "data": sma_short.tolist(), "color": "#FF9800", "overlay": True},
        {"name": f"SMA{sma_long_period}", "data": sma_long.tolist(), "color": "#3F51B5", "overlay": True}
    ],
    "signals": [
        {"type": "buy", "text": "B", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "S", "data": sell_marks, "color": "#FF5252"}
    ]
}
```

#### Example: Using call_indicator()
```python
# Call another indicator by name or ID
# rsi_df = call_indicator('RSI', df)           # By name
# rsi_df = call_indicator(5, df)               # By ID
# rsi_df = call_indicator('RSI', df, {'period': 14})  # With params

# Note: The called indicator must be created first
# and accessible (own indicator or published community indicator)
```

### 🐛 Bug Fixes

#### Dashboard Fixes
- **Fixed current positions showing records from other users** - Position synchronization now correctly associates positions with the strategy owner's user_id
- **Fixed strategy distribution pie chart always showing "No Data"** - Chart now uses `strategy_stats` data which includes all strategies with trading activity
- **Removed AI strategy count from running strategies card** - Dashboard now only shows indicator strategy count since AI strategies category has been removed

---

## V2.1.1 (2026-01-31)

### 🚀 New Features

#### AI Analysis System Overhaul
- **Fast Analysis Mode**: Replaced the complex multi-agent system with a streamlined single LLM call architecture for faster and more accurate analysis
- **Progressive Loading**: Market data now loads independently - each section (sentiment, indices, heatmap, calendar) displays as soon as it's ready
- **Professional Loading Animation**: New progress bar with step indicators during AI analysis
- **Analysis Memory**: Store analysis results for history review and user feedback
- **Stop Loss/Take Profit Calculation**: Now based on ATR (Average True Range) and Support/Resistance levels with clear methodology hints

#### Global Market Integration
- Integrated Global Market data directly into AI Analysis page
- Real-time scrolling display of major global indices with flags, prices, and percentage changes
- Interactive heatmaps for Crypto, Commodities, Sectors, and Forex
- Economic calendar with bullish/bearish/neutral impact indicators
- Commodities heatmap added (Gold, Silver, Crude Oil, etc.)

#### Indicator Community Enhancements
- **Admin Review System**: Administrators can now review, approve, reject, unpublish, and delete community indicators
- **Purchase & Rating System**: Users can buy indicators, leave ratings and comments
- **Statistics Tracking**: Purchase count, average rating, rating count, view count for each indicator

#### Trading Assistant Improvements
- Improved IBKR/MT5 connection test feedback
- Added local deployment warning for external trading platforms
- Virtual profit/loss calculation for signal-only strategies

### 🐛 Bug Fixes
- Fixed progress bar and timer not animating during AI analysis
- Fixed missing i18n translations for various components
- Fixed Tiingo API rate limit issues with caching
- Fixed A-share and H-share data fetching with multiple fallback sources
- Fixed watchlist price batch fetch timeout handling
- Fixed heatmap multi-language support for commodities and forex
- **Fixed AI analysis history not filtered by user** - All users were seeing the same history records; now each user only sees their own analysis history
- **Fixed "Missing Turnstile token" error when changing password** - Logged-in users no longer need Turnstile verification to request password change verification code

### 🎨 UI/UX Improvements
- Reorganized left menu: Indicator Market moved below Indicator Analysis, Settings moved to bottom
- Skeleton loading animations for progressive data display
- Dark theme support for all new components
- Compact market overview bar design

### 📋 Database Migration

**Run the following SQL on your PostgreSQL database before deploying V2.1.1:**

```sql
-- ============================================================
-- ZhiYiQuant V2.1.1 Database Migration
-- ============================================================

-- 1. AI Analysis Memory Table
CREATE TABLE IF NOT EXISTS qd_analysis_memory (
    id SERIAL PRIMARY KEY,
    market VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    decision VARCHAR(10) NOT NULL,
    confidence INT DEFAULT 50,
    price_at_analysis DECIMAL(24, 8),
    entry_price DECIMAL(24, 8),
    stop_loss DECIMAL(24, 8),
    take_profit DECIMAL(24, 8),
    summary TEXT,
    reasons JSONB,
    risks JSONB,
    scores JSONB,
    indicators_snapshot JSONB,
    raw_result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    actual_outcome VARCHAR(20),
    actual_return_pct DECIMAL(10, 4),
    was_correct BOOLEAN,
    user_feedback VARCHAR(20),
    feedback_at TIMESTAMP
);

-- Add raw_result column if table exists but column doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_analysis_memory' AND column_name = 'raw_result'
    ) THEN
        ALTER TABLE qd_analysis_memory ADD COLUMN raw_result JSONB;
    END IF;
END $$;

-- Add user_id column for user-specific history filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_analysis_memory' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE qd_analysis_memory ADD COLUMN user_id INT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_analysis_memory_symbol ON qd_analysis_memory(market, symbol);
CREATE INDEX IF NOT EXISTS idx_analysis_memory_created ON qd_analysis_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_memory_validated ON qd_analysis_memory(validated_at) WHERE validated_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analysis_memory_user ON qd_analysis_memory(user_id);

-- 2. Indicator Purchase Records
CREATE TABLE IF NOT EXISTS qd_indicator_purchases (
    id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES qd_indicator_codes(id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES qd_users(id),
    price DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(indicator_id, buyer_id)
);

CREATE INDEX IF NOT EXISTS idx_purchases_indicator ON qd_indicator_purchases(indicator_id);
CREATE INDEX IF NOT EXISTS idx_purchases_buyer ON qd_indicator_purchases(buyer_id);
CREATE INDEX IF NOT EXISTS idx_purchases_seller ON qd_indicator_purchases(seller_id);

-- 3. Indicator Comments
CREATE TABLE IF NOT EXISTS qd_indicator_comments (
    id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES qd_indicator_codes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    rating INTEGER DEFAULT 5 CHECK (rating >= 1 AND rating <= 5),
    content TEXT DEFAULT '',
    parent_id INTEGER REFERENCES qd_indicator_comments(id) ON DELETE CASCADE,
    is_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_indicator ON qd_indicator_comments(indicator_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON qd_indicator_comments(user_id);

-- 4. Indicator Codes Extensions
DO $$
BEGIN
    -- Purchase count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'purchase_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN purchase_count INTEGER DEFAULT 0;
    END IF;
    
    -- Average rating
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'avg_rating'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN avg_rating DECIMAL(3,2) DEFAULT 0;
    END IF;
    
    -- Rating count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'rating_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN rating_count INTEGER DEFAULT 0;
    END IF;
    
    -- View count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'view_count'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN view_count INTEGER DEFAULT 0;
    END IF;
    
    -- Review status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'review_status'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN review_status VARCHAR(20) DEFAULT 'approved';
        UPDATE qd_indicator_codes SET review_status = 'approved' WHERE publish_to_community = 1;
    END IF;
    
    -- Review note
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'review_note'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN review_note TEXT DEFAULT '';
    END IF;
    
    -- Reviewed at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'reviewed_at'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN reviewed_at TIMESTAMP;
    END IF;
    
    -- Reviewed by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_indicator_codes' AND column_name = 'reviewed_by'
    ) THEN
        ALTER TABLE qd_indicator_codes ADD COLUMN reviewed_by INTEGER;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_indicator_review_status ON qd_indicator_codes(review_status);

-- 5. User Table Extensions
DO $$
BEGIN
    -- Token version (for single-client login)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_users' AND column_name = 'token_version'
    ) THEN
        ALTER TABLE qd_users ADD COLUMN token_version INTEGER DEFAULT 1;
    END IF;
    
    -- Notification settings
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_users' AND column_name = 'notification_settings'
    ) THEN
        ALTER TABLE qd_users ADD COLUMN notification_settings TEXT DEFAULT '{}';
    END IF;
END $$;

-- Migration Complete
DO $$
BEGIN
    RAISE NOTICE '✅ ZhiYiQuant V2.1.1 database migration completed!';
END $$;
```

### 🗑️ Removed
- Old multi-agent AI analysis system (`backend_api_python/app/services/agents/` directory)
- Old analysis routes and services
- Standalone Global Market page (merged into AI Analysis)
- Reflection worker background process

### ⚠️ Breaking Changes
- AI Analysis API endpoints changed from `/api/analysis/*` to `/api/fast-analysis/*`
- Old analysis history data is not compatible with new format

### 📝 Configuration Notes
- No new environment variables required
- Existing LLM configuration in System Settings will be used for AI Analysis

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| V2.1.1 | 2026-01-31 | AI Analysis overhaul, Global Market integration, Indicator Community enhancements |

---

*For questions or issues, please open a GitHub issue or contact the maintainers.*
