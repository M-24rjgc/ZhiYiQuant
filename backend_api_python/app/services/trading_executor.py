"""
瀹炴椂浜ゆ槗鎵ц鏈嶅姟
"""
import time
import threading
import traceback
import os
try:
    import resource  # Linux/Unix only
except Exception:
    resource = None
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import pandas as pd
import numpy as np
import ccxt

from app.utils.logger import get_logger
from app.utils.db import get_db_connection
from app.data_sources import DataSourceFactory
from app.services.kline import KlineService
from app.services.indicator_params import IndicatorParamsParser, IndicatorCaller

logger = get_logger(__name__)


class TradingExecutor:
    """Desktop runtime helper."""
    
    def __init__(self):
        # 涓嶅啀浣跨敤鍏ㄥ眬杩炴帴锛屾敼涓烘瘡娆′娇鐢ㄦ椂浠庤繛鎺ユ睜鑾峰彇
        self.running_strategies = {}  # {strategy_id: thread}
        self.lock = threading.Lock()
        # Local-only lightweight in-memory price cache (symbol -> (price, expiry_ts)).
        # This replaces the old Redis-based PriceCache for local deployments.
        self._price_cache = {}
        self._price_cache_lock = threading.Lock()
        # Default to 10s to match the unified tick cadence.
        self._price_cache_ttl_sec = int(os.getenv("PRICE_CACHE_TTL_SEC", "10"))

        # In-memory signal de-dup cache to prevent repeated orders on the same candle signal.
        # Keyed by (strategy_id, symbol, signal_type, signal_timestamp).
        self._signal_dedup = {}  # type: Dict[int, Dict[str, float]]
        self._signal_dedup_lock = threading.Lock()
        self.kline_service = KlineService()   # K绾挎湇鍔★紙甯︾紦瀛橈級
        
        # 鍗曞疄渚嬬嚎绋嬩笂闄愶紝閬垮厤鏃犻檺鍒跺垱寤虹嚎绋嬪鑷?can't start new thread/OOM
        self.max_threads = int(os.getenv('STRATEGY_MAX_THREADS', '64'))
        
        # 纭繚鏁版嵁搴撳瓧娈靛瓨鍦?
        self._ensure_db_columns()

    def _ensure_db_columns(self):
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                try:
                    cursor.execute("PRAGMA table_info(zhiyiquant_strategy_positions)")
                    cols = cursor.fetchall() or []
                    col_names = {c.get('name') for c in cols if isinstance(c, dict)}
                except Exception:
                    col_names = set()

                if 'highest_price' not in col_names:
                    logger.info("Adding highest_price column to zhiyiquant_strategy_positions...")
                    cursor.execute("ALTER TABLE zhiyiquant_strategy_positions ADD COLUMN highest_price REAL DEFAULT 0")
                    db.commit()
                    logger.info("highest_price column added")

                if 'lowest_price' not in col_names:
                    logger.info("Adding lowest_price column to zhiyiquant_strategy_positions...")
                    cursor.execute("ALTER TABLE zhiyiquant_strategy_positions ADD COLUMN lowest_price REAL DEFAULT 0")
                    db.commit()
                    logger.info("lowest_price column added")

                cursor.close()
        except Exception as e:
            logger.error(f"Failed to check or ensure DB columns: {str(e)}")

    def _normalize_trade_symbol(self, exchange: Any, symbol: str, market_type: str, exchange_id: str) -> str:
        """
        灏嗘暟鎹簱/閰嶇疆閲岀殑 symbol 瑙勮寖鍖栦负浜ゆ槗鎵€鍚堢害鍙敤鐨?CCXT symbol銆?

        鍏稿瀷鍦烘櫙锛歄KX 姘哥画缁熶竴绗﹀彿閫氬父鏄?`BNB/USDT:USDT`锛屼絾鍓嶇/鏁版嵁搴撳彲鑳戒紶 `BNB/USDT`銆?
        """
        try:
            # 鏂扮郴缁燂細浠呮敮鎸?swap(鍚堢害姘哥画) / spot(鐜拌揣)
            if market_type != 'swap':
                return symbol
            if not symbol or ':' in symbol:
                return symbol
            if not getattr(exchange, 'markets', None):
                return symbol

            # 濡傛灉 symbol 鏈韩灏辨槸鍚堢害甯傚満锛岀洿鎺ヨ繑鍥?
            try:
                m = exchange.market(symbol)
                if m and (m.get('swap') or m.get('future') or m.get('contract')):
                    return symbol
            except Exception:
                pass

            # OKX/閮ㄥ垎浜ゆ槗鎵€锛氭案缁父瑙佷负 BASE/QUOTE:QUOTE 鎴?BASE/QUOTE:USDT
            if '/' not in symbol:
                return symbol
            base, quote = symbol.split('/', 1)
            candidates = []
            if quote:
                candidates.append(f"{base}/{quote}:{quote}")
                if quote.upper() != 'USDT':
                    candidates.append(f"{base}/{quote}:USDT")

            for cand in candidates:
                if cand in exchange.markets:
                    cm = exchange.markets[cand]
                    if cm and (cm.get('swap') or cm.get('future') or cm.get('contract')):
                        logger.info(f"symbol normalized: {symbol} -> {cand} (exchange={exchange_id}, market_type={market_type})")
                        return cand

            return symbol
        except Exception:
            return symbol

    def _log_resource_status(self, prefix: str = ""):
        """Desktop runtime helper."""
        try:
            import psutil  # 濡傛灉鏈夊畨瑁呭垯浣跨敤鏇寸簿纭殑鎸囨爣
            p = psutil.Process()
            mem = p.memory_info().rss / 1024 / 1024
            th = p.num_threads()
            logger.warning(f"{prefix}resource status: memory={mem:.1f}MB, threads={th}, "
                           f"running_strategies={len(self.running_strategies)}")
        except Exception:
            try:
                th = threading.active_count()
                # 浠?/proc/self/status 璇诲彇 VmRSS锛堥€傜敤浜?Linux 瀹瑰櫒锛?
                vmrss = None
                try:
                    with open('/proc/self/status') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                vmrss = line.split()[1:3]  # e.g. ['123456', 'kB']
                                break
                except Exception:
                    pass
                vmrss_str = f"{vmrss[0]}{vmrss[1]}" if vmrss else "N/A"
                logger.warning(f"{prefix}resource status: VmRSS={vmrss_str}, active_threads={th}, "
                               f"running_strategies={len(self.running_strategies)}")
            except Exception:
                pass

    def _console_print(self, msg: str) -> None:
        """
        Local-only observability: print to stdout so user can see strategy status in console.
        """
        try:
            print(str(msg or ""), flush=True)
        except Exception:
            pass

    def _position_state(self, positions: List[Dict[str, Any]]) -> str:
        """
        Return current position state for a strategy+symbol in local single-position mode.

        Returns: 'flat' | 'long' | 'short'
        """
        try:
            if not positions:
                return "flat"
            # Local mode assumes single-direction position per symbol.
            side = (positions[0].get("side") or "").strip().lower()
            if side in ("long", "short"):
                return side
        except Exception:
            pass
        return "flat"

    def _is_signal_allowed(self, state: str, signal_type: str) -> bool:
        """
        Enforce strict state machine:
        - flat: only open_long/open_short
        - long: only add_long/close_long
        - short: only add_short/close_short
        """
        st = (state or "flat").strip().lower()
        sig = (signal_type or "").strip().lower()
        if st == "flat":
            return sig in ("open_long", "open_short")
        if st == "long":
            return sig in ("add_long", "reduce_long", "close_long")
        if st == "short":
            return sig in ("add_short", "reduce_short", "close_short")
        return False

    def _signal_priority(self, signal_type: str) -> int:
        """
        Lower value = higher priority. We always close before (re)opening/adding.
        """
        sig = (signal_type or "").strip().lower()
        if sig.startswith("close_"):
            return 0
        if sig.startswith("reduce_"):
            return 1
        if sig.startswith("open_"):
            return 2
        if sig.startswith("add_"):
            return 3
        return 99

    def _dedup_key(self, strategy_id: int, symbol: str, signal_type: str, signal_ts: int) -> str:
        sym = (symbol or "").strip().upper()
        if ":" in sym:
            sym = sym.split(":", 1)[0]
        return f"{int(strategy_id)}|{sym}|{(signal_type or '').strip().lower()}|{int(signal_ts or 0)}"

    def _should_skip_signal_once_per_candle(
        self,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        signal_ts: int,
        timeframe_seconds: int,
        now_ts: Optional[int] = None,
    ) -> bool:
        """
        Prevent repeated orders for the same candle signal across ticks.

        This is especially important for 'confirmed' signals that point to the previous closed candle:
        the signal timestamp stays constant for the entire next candle, so without de-dup the system
        would re-enqueue the same order every tick.
        """
        try:
            now = int(now_ts or time.time())
            tf = int(timeframe_seconds or 0)
            if tf <= 0:
                tf = 60
            # Keep keys long enough to cover at least the next candle.
            ttl_sec = max(tf * 2, 120)
            expiry = float(now + ttl_sec)
            key = self._dedup_key(strategy_id, symbol, signal_type, int(signal_ts or 0))

            with self._signal_dedup_lock:
                bucket = self._signal_dedup.get(int(strategy_id))
                if bucket is None:
                    bucket = {}
                    self._signal_dedup[int(strategy_id)] = bucket

                # Opportunistic cleanup
                stale = [k for k, exp in bucket.items() if float(exp) <= now]
                for k in stale[:512]:
                    try:
                        del bucket[k]
                    except Exception:
                        pass

                exp = bucket.get(key)
                if exp is not None and float(exp) > now:
                    return True

                # Reserve the key (best-effort). Caller may still fail to enqueue; that's acceptable
                # because repeated failures should not flood the queue.
                bucket[key] = expiry
                return False
        except Exception:
            return False

    def _to_ratio(self, v: Any, default: float = 0.0) -> float:
        """
        Convert a percent-like value into ratio in [0, 1].
        Accepts both 0~1 and 0~100 inputs.
        """
        try:
            x = float(v if v is not None else default)
        except Exception:
            x = float(default or 0.0)
        if x > 1.0:
            x = x / 100.0
        if x < 0:
            x = 0.0
        if x > 1.0:
            x = 1.0
        return float(x)

    def _build_cfg_from_trading_config(self, trading_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a backtest-modal config dict for indicator scripts.

        Frontend (trading assistant) stores most params as flat keys under `trading_config`.
        Backtest service expects nested structure: cfg.risk/cfg.scale/cfg.position (camelCase).

        We provide BOTH:
        - `trading_config`: the original flat dict (so existing scripts keep working)
        - `cfg`: a normalized nested dict (so scripts can reuse backtest-style helpers)
        """
        tc = trading_config or {}

        # Risk / trailing
        stop_loss_pct = self._to_ratio(tc.get("stop_loss_pct"))
        take_profit_pct = self._to_ratio(tc.get("take_profit_pct"))
        trailing_enabled = bool(tc.get("trailing_enabled"))
        trailing_stop_pct = self._to_ratio(tc.get("trailing_stop_pct"))
        trailing_activation_pct = self._to_ratio(tc.get("trailing_activation_pct"))

        # Position sizing
        entry_pct = self._to_ratio(tc.get("entry_pct"))

        # Scale-in
        trend_add_enabled = bool(tc.get("trend_add_enabled"))
        trend_add_step_pct = self._to_ratio(tc.get("trend_add_step_pct"))
        trend_add_size_pct = self._to_ratio(tc.get("trend_add_size_pct"))
        trend_add_max_times = int(tc.get("trend_add_max_times") or 0)

        dca_add_enabled = bool(tc.get("dca_add_enabled"))
        dca_add_step_pct = self._to_ratio(tc.get("dca_add_step_pct"))
        dca_add_size_pct = self._to_ratio(tc.get("dca_add_size_pct"))
        dca_add_max_times = int(tc.get("dca_add_max_times") or 0)

        # Scale-out / reduce
        trend_reduce_enabled = bool(tc.get("trend_reduce_enabled"))
        trend_reduce_step_pct = self._to_ratio(tc.get("trend_reduce_step_pct"))
        trend_reduce_size_pct = self._to_ratio(tc.get("trend_reduce_size_pct"))
        trend_reduce_max_times = int(tc.get("trend_reduce_max_times") or 0)

        adverse_reduce_enabled = bool(tc.get("adverse_reduce_enabled"))
        adverse_reduce_step_pct = self._to_ratio(tc.get("adverse_reduce_step_pct"))
        adverse_reduce_size_pct = self._to_ratio(tc.get("adverse_reduce_size_pct"))
        adverse_reduce_max_times = int(tc.get("adverse_reduce_max_times") or 0)

        return {
            "risk": {
                "stopLossPct": stop_loss_pct,
                "takeProfitPct": take_profit_pct,
                "trailing": {
                    "enabled": trailing_enabled,
                    "pct": trailing_stop_pct,
                    "activationPct": trailing_activation_pct,
                },
            },
            "position": {
                "entryPct": entry_pct,
            },
            "scale": {
                "trendAdd": {
                    "enabled": trend_add_enabled,
                    "stepPct": trend_add_step_pct,
                    "sizePct": trend_add_size_pct,
                    "maxTimes": trend_add_max_times,
                },
                "dcaAdd": {
                    "enabled": dca_add_enabled,
                    "stepPct": dca_add_step_pct,
                    "sizePct": dca_add_size_pct,
                    "maxTimes": dca_add_max_times,
                },
                "trendReduce": {
                    "enabled": trend_reduce_enabled,
                    "stepPct": trend_reduce_step_pct,
                    "sizePct": trend_reduce_size_pct,
                    "maxTimes": trend_reduce_max_times,
                },
                "adverseReduce": {
                    "enabled": adverse_reduce_enabled,
                    "stepPct": adverse_reduce_step_pct,
                    "sizePct": adverse_reduce_size_pct,
                    "maxTimes": adverse_reduce_max_times,
                },
            },
        }
    
    def start_strategy(self, strategy_id: int) -> bool:
        """
        鍚姩绛栫暐
        
        Args:
            strategy_id: 绛栫暐ID
            
        Returns:
            鏄惁鎴愬姛
        """
        try:
            with self.lock:
                # 娓呯悊宸查€€鍑虹殑绾跨▼锛岄槻姝㈣鏁拌啫鑳€
                stale_ids = [sid for sid, th in self.running_strategies.items() if not th.is_alive()]
                for sid in stale_ids:
                    del self.running_strategies[sid]

                if len(self.running_strategies) >= self.max_threads:
                    logger.error(
                        f"Thread limit reached ({self.max_threads}); refuse to start strategy {strategy_id}. "
                        f"Reduce running strategies or increase STRATEGY_MAX_THREADS."
                    )
                    self._log_resource_status(prefix="start_denied: ")
                    return False

                if strategy_id in self.running_strategies:
                    logger.warning(f"Strategy {strategy_id} is already running")
                    return False
                
                # 鍒涘缓骞跺惎鍔ㄧ嚎绋?
                thread = threading.Thread(
                    target=self._run_strategy_loop,
                    args=(strategy_id,),
                    daemon=True
                )
                try:
                    thread.start()
                except Exception as e:
                    # 鎹曡幏 can't start new thread 绛夊紓甯革紝璁板綍璧勬簮鐘舵€?
                    self._log_resource_status(prefix="鍚姩寮傚父")
                    raise e
                self.running_strategies[strategy_id] = thread
                
                logger.info(f"Strategy {strategy_id} started")
                self._console_print(f"[strategy:{strategy_id}] started")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def stop_strategy(self, strategy_id: int) -> bool:
        """
        鍋滄绛栫暐
        
        Args:
            strategy_id: 绛栫暐ID
            
        Returns:
            鏄惁鎴愬姛
        """
        try:
            with self.lock:
                if strategy_id not in self.running_strategies:
                    logger.warning(f"Strategy {strategy_id} is not running")
                    return False
                
                # 鏍囪绛栫暐涓哄仠姝㈢姸鎬?
                with get_db_connection() as db:
                    cursor = db.cursor()
                    cursor.execute(
                        "UPDATE zhiyiquant_strategies_trading SET status = 'stopped' WHERE id = %s",
                        (strategy_id,)
                    )
                    db.commit()
                    cursor.close()
                
                # 浠庤繍琛屽垪琛ㄤ腑绉婚櫎锛堢嚎绋嬩細鍦ㄤ笅娆″惊鐜鏌ョ姸鎬佹椂閫€鍑猴級
                del self.running_strategies[strategy_id]
                
                logger.info(f"Strategy {strategy_id} stopped")
                self._console_print(f"[strategy:{strategy_id}] stopped (requested)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _run_strategy_loop(self, strategy_id: int):
        """
        绛栫暐杩愯寰幆
        
        Args:
            strategy_id: 绛栫暐ID
        """
        logger.info(f"Strategy {strategy_id} loop starting")
        self._console_print(f"[strategy:{strategy_id}] loop initializing")
        
        try:
            # 鍔犺浇绛栫暐閰嶇疆
            strategy = self._load_strategy(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return
            
            if strategy['strategy_type'] != 'IndicatorStrategy':
                logger.error(f"Strategy {strategy_id} has unsupported strategy_type for realtime execution: {strategy['strategy_type']}")
                return
            
            # 鍒濆鍖栫瓥鐣ョ姸鎬?
            trading_config = strategy['trading_config']
            indicator_config = strategy['indicator_config']
            ai_model_config = strategy.get('ai_model_config') or {}
            execution_mode = (strategy.get('execution_mode') or 'signal').strip().lower()
            if execution_mode not in ['signal', 'live']:
                execution_mode = 'signal'
            notification_config = strategy.get('notification_config') or {}
            strategy_name = strategy.get('strategy_name') or f"strategy_{int(strategy_id)}"
            symbol = trading_config.get('symbol', '')
            timeframe = trading_config.get('timeframe', '1H')
            
            # 瀹夊叏鑾峰彇 leverage 鍜?trade_direction
            try:
                leverage_val = trading_config.get('leverage', 1)
                if isinstance(leverage_val, (list, tuple)):
                    leverage_val = leverage_val[0] if leverage_val else 1
                leverage = float(leverage_val)
            except:
                logger.warning(f"Strategy {strategy_id} invalid leverage format, reset to 1: {trading_config.get('leverage')}")
                leverage = 1.0
            
            # 鑾峰彇甯傚満绫诲瀷锛岄粯璁や负鍚堢害
            # 鏍规嵁鏉犳潌鑷姩鍒ゆ柇锛氭潬鏉?1涓虹幇璐э紝鏉犳潌>1涓哄悎绾?
            market_type = trading_config.get('market_type', 'swap')
            if market_type not in ['swap', 'spot']:
                logger.error(f"Strategy {strategy_id} invalid market_type={market_type} (only swap/spot supported); refusing to start")
                return
            
            # 鏍规嵁鏉犳潌鑷姩璋冩暣甯傚満绫诲瀷
            if leverage == 1.0:
                market_type = 'spot'  # 鐜拌揣鍥哄畾1鍊嶆潬鏉?
                logger.info(f"Strategy {strategy_id} leverage=1; auto-switch market_type to spot")
            else:
                # 鍚堢害甯傚満锛氱粺涓€浣跨敤 swap锛堟案缁級锛岄伩鍏?futures/delivery 娣锋穯瀵艰嚧鎸佷粨/涓嬪崟鏌ラ敊甯傚満
                market_type = 'swap'
                logger.info(f"Strategy {strategy_id} derivatives trading; normalize market_type to: {market_type}")
            
            # 鏍规嵁甯傚満绫诲瀷闄愬埗鏉犳潌
            if market_type == 'spot':
                leverage = 1.0  # 鐜拌揣鍥哄畾1鍊嶆潬鏉?
            elif leverage < 1:
                leverage = 1.0
            elif leverage > 125:
                leverage = 125.0
                logger.warning(f"Strategy {strategy_id} leverage > 125; capped to 125")
            
            # 鑾峰彇浜ゆ槗鏂瑰悜锛岀幇璐у彧鑳藉仛澶?
            trade_direction = trading_config.get('trade_direction', 'long')
            if market_type == 'spot':
                trade_direction = 'long'  # 鐜拌揣鍙兘鍋氬
                logger.info(f"Strategy {strategy_id} spot trading; force trade_direction=long")

            # 鑾峰彇甯傚満绫诲埆锛圕rypto, USStock, Forex, Futures, AShare, HShare锛?
            # 杩欏喅瀹氫簡浣跨敤鍝釜鏁版嵁婧愭潵鑾峰彇浠锋牸鍜孠绾挎暟鎹?
            market_category = (strategy.get('market_category') or 'Crypto').strip()
            logger.info(f"Strategy {strategy_id} market_category: {market_category}")

            # Check if this is a cross-sectional strategy
            cs_strategy_type = trading_config.get('cs_strategy_type', 'single')
            if cs_strategy_type == 'cross_sectional':
                # Run cross-sectional strategy loop
                self._run_cross_sectional_strategy_loop(
                    strategy_id, strategy, trading_config, indicator_config, 
                    ai_model_config, execution_mode, notification_config, 
                    strategy_name, market_category, market_type, leverage, 
                    initial_capital, indicator_code, indicator_id
                )
                return

            # 鍒濆鍖栦氦鏄撴墍杩炴帴锛堜俊鍙锋ā寮忎笅鏃犻渶鐪熷疄杩炴帴锛?
            exchange = None
            
            # 瀹夊叏鑾峰彇 initial_capital
            try:
                initial_capital_val = strategy.get('initial_capital', 1000)
                if isinstance(initial_capital_val, (list, tuple)):
                    initial_capital_val = initial_capital_val[0] if initial_capital_val else 1000
                initial_capital = float(initial_capital_val)
            except:
                logger.warning(f"Strategy {strategy_id} invalid initial_capital format, reset to 1000: {strategy.get('initial_capital')}")
                initial_capital = 1000.0
            
            # 鍑€鍊间細鍦ㄩ娆℃洿鏂版寔浠撴椂鑷姩璁＄畻鍜屾洿鏂?
            
            # 鑾峰彇鎸囨爣浠ｇ爜
            indicator_id = indicator_config.get('indicator_id')
            indicator_code = indicator_config.get('indicator_code', '')
            
            # 濡傛灉浠ｇ爜涓虹┖锛屽皾璇曚粠鏁版嵁搴撹幏鍙?
            if not indicator_code and indicator_id:
                indicator_code = self._get_indicator_code_from_db(indicator_id)
            
            if not indicator_code:
                logger.error(f"Strategy {strategy_id} indicator_code is empty")
                return
            
            # 纭繚 indicator_code 鏄瓧绗︿覆锛堝鐞?JSON 杞箟闂锛?
            if not isinstance(indicator_code, str):
                indicator_code = str(indicator_code)
            
            # 澶勭悊鍙兘鐨?JSON 杞箟闂
            if '\\n' in indicator_code and '\n' not in indicator_code:
                try:
                    import json
                    decoded = json.loads(f'"{indicator_code}"')
                    if isinstance(decoded, str):
                        indicator_code = decoded
                        logger.info(f"Strategy {strategy_id} decoded escaped indicator_code")
                except Exception as e:
                    logger.warning(f"Strategy {strategy_id} JSON decode failed; falling back to manual unescape: {str(e)}")
                    indicator_code = (
                        indicator_code
                        .replace('\\n', '\n')
                        .replace('\\t', '\t')
                        .replace('\\r', '\r')
                        .replace('\\"', '"')
                        .replace("\\'", "'")
                        .replace('\\\\', '\\')
                    )
            
            # ============================================
            # 鍒濆鍖栭樁娈碉細鑾峰彇鍘嗗彶K绾垮苟璁＄畻鎸囨爣
            # ============================================
            # logger.info(f"绛栫暐 {strategy_id} 鍒濆鍖栵細鑾峰彇鍘嗗彶K绾挎暟鎹?..")
            history_limit = int(os.getenv('K_LINE_HISTORY_GET_NUMBER', 500))
            klines = self._fetch_latest_kline(symbol, timeframe, limit=history_limit, market_category=market_category)
            if not klines or len(klines) < 2:
                logger.error(f"Strategy {strategy_id} failed to fetch K-lines")
                return
            logger.info(rf'Strategy {strategy_id} history kline number: {len(klines)}')
            
            # 杞崲涓篋ataFrame
            df = self._klines_to_dataframe(klines)
            if len(df) == 0:
                logger.error(f"Strategy {strategy_id} K-lines are empty after normalization")
                return

            # ============================================
            # 鍚姩鏃讹細瀹屽叏渚濊禆鏈湴鏁版嵁搴撶殑鎸佷粨鐘舵€侊紙铏氭嫙鎸佷粨锛?
            # ============================================
            # 淇″彿妯″紡涓嬶紝涓嶅啀鍚屾浜ゆ槗鎵€鎸佷粨
            pass

            # 鑾峰彇褰撳墠鎸佷粨鏈€楂樹环锛堜粠鏈湴鏁版嵁搴撹鍙栵級
            current_pos_list = self._get_current_positions(strategy_id, symbol)
            initial_highest = 0.0
            initial_position = 0  # 0=鏃犳寔浠? 1=澶氬ご, -1=绌哄ご
            initial_avg_entry_price = 0.0
            initial_position_count = 0
            initial_last_add_price = 0.0
            
            if current_pos_list:
                pos = current_pos_list[0]  # 鍙栫涓€涓寔浠擄紙鍗曞悜鎸佷粨妯″紡锛?
                initial_highest = float(pos.get('highest_price', 0) or 0)
                pos_side = pos.get('side', 'long')
                initial_position = 1 if pos_side == 'long' else -1
                initial_avg_entry_price = float(pos.get('entry_price', 0) or 0)
                initial_position_count = 1  # 绠€鍖栧鐞嗭紝鍋囪鏄崟绗旀寔浠?
                initial_last_add_price = initial_avg_entry_price

            # 鍏抽敭璇婃柇鏃ュ織锛氱‘璁ゆ寚鏍囨槸鍚︽嬁鍒颁簡鎸佷粨鐘舵€?
            logger.info(
                f"绛栫暐 {strategy_id} 鎸囨爣娉ㄥ叆鎸佷粨鐘舵€? count={len(current_pos_list)}, "
                f"position={initial_position}, entry_price={initial_avg_entry_price}, highest={initial_highest}"
            )

            # 鎵ц鎸囨爣浠ｇ爜锛岃幏鍙栦俊鍙峰拰瑙﹀彂浠锋牸
            indicator_result = self._execute_indicator_with_prices(
                indicator_code, df, trading_config, 
                initial_highest_price=initial_highest,
                initial_position=initial_position,
                initial_avg_entry_price=initial_avg_entry_price,
                initial_position_count=initial_position_count,
                initial_last_add_price=initial_last_add_price
            )
            if indicator_result is None:
                logger.error(f"Strategy {strategy_id} indicator execution failed")
                return
            
            # 鎻愬彇淇″彿鍜岃Е鍙戜环鏍?
            pending_signals = indicator_result.get('pending_signals', [])  # 寰呰Е鍙戠殑淇″彿鍒楄〃
            last_kline_time = indicator_result.get('last_kline_time', 0)  # 鏈€鍚庝竴鏍筀绾跨殑鏃堕棿
            
            logger.info(f"Strategy {strategy_id} initialized; pending_signals={len(pending_signals)}")
            if pending_signals:
                logger.info(f"Initial signals: {pending_signals}")
            
            # ============================================
            # Main loop: unified tick cadence (default: 10s)
            # ============================================
            # One tick = fetch current price once + evaluate triggers once + (if needed) refresh K-lines / recalc indicator.
            # Note: `pending_orders` scanning stays at 1s (see PendingOrderWorker) to reduce live dispatch latency.
            try:
                # Global-only (no per-strategy override)
                tick_interval_sec = int(os.getenv('STRATEGY_TICK_INTERVAL_SEC', '10'))
            except Exception:
                tick_interval_sec = 10
            if tick_interval_sec < 1:
                tick_interval_sec = 1

            last_tick_time = 0.0
            last_kline_update_time = time.time()
            
            # 璁＄畻K绾垮懆鏈燂紙绉掞級
            from app.data_sources.base import TIMEFRAME_SECONDS
            timeframe_seconds = TIMEFRAME_SECONDS.get(timeframe, 3600)
            kline_update_interval = timeframe_seconds  # 姣忎釜K绾垮懆鏈熸洿鏂颁竴娆?
            
            while True:
                try:
                    # 妫€鏌ョ瓥鐣ョ姸鎬?
                    if not self._is_strategy_running(strategy_id):
                        logger.info(f"Strategy {strategy_id} stopped")
                        break
                    
                    current_time = time.time()

                    # Sleep until next tick to avoid CPU spin.
                    if last_tick_time > 0:
                        sleep_sec = (last_tick_time + tick_interval_sec) - current_time
                        if sleep_sec > 0:
                            time.sleep(min(sleep_sec, 1.0))
                            continue
                    last_tick_time = current_time

                    # ============================================
                    # 0. 铏氭嫙鎸佷粨妯″紡锛屾棤闇€鍚屾浜ゆ槗鎵€
                    # ============================================
                    # pass
                    
                    # ============================================
                    # 1. Fetch current price once per tick
                    # ============================================
                    current_price = self._fetch_current_price(exchange, symbol, market_type=market_type, market_category=market_category)
                    if current_price is None:
                        logger.warning(f"Strategy {strategy_id} failed to fetch current price for {market_category}:{symbol}")
                        continue

                    # ============================================
                    # 2. 妫€鏌ユ槸鍚﹂渶瑕佹洿鏂癒绾匡紙姣忎釜K绾垮懆鏈熸洿鏂颁竴娆★紝浠嶢PI鎷夊彇锛?
                    # ============================================
                    if current_time - last_kline_update_time >= kline_update_interval:
                        klines = self._fetch_latest_kline(symbol, timeframe, limit=history_limit, market_category=market_category)
                        if klines and len(klines) >= 2:
                            df = self._klines_to_dataframe(klines)
                            if len(df) > 0:
                                current_pos_list = self._get_current_positions(strategy_id, symbol)
                                initial_highest = 0.0
                                initial_position = 0
                                initial_avg_entry_price = 0.0
                                initial_position_count = 0
                                initial_last_add_price = 0.0

                                if current_pos_list:
                                    pos = current_pos_list[0]
                                    initial_highest = float(pos.get('highest_price', 0) or 0)
                                    pos_side = pos.get('side', 'long')
                                    initial_position = 1 if pos_side == 'long' else -1
                                    initial_avg_entry_price = float(pos.get('entry_price', 0) or 0)
                                    initial_position_count = 1
                                    initial_last_add_price = initial_avg_entry_price

                                indicator_result = self._execute_indicator_with_prices(
                                    indicator_code, df, trading_config,
                                    initial_highest_price=initial_highest,
                                    initial_position=initial_position,
                                    initial_avg_entry_price=initial_avg_entry_price,
                                    initial_position_count=initial_position_count,
                                    initial_last_add_price=initial_last_add_price
                                )
                                if indicator_result:
                                    pending_signals = indicator_result.get('pending_signals', [])
                                    last_kline_time = indicator_result.get('last_kline_time', 0)
                                    new_hp = indicator_result.get('new_highest_price', 0)

                                    last_kline_update_time = current_time

                                    # 鏇存柊 highest_price锛堜娇鐢ㄦ渶鏂?close 浣滀负 current_price 鐨勮繎浼硷級
                                    if new_hp > 0 and current_pos_list:
                                        current_close = float(df['close'].iloc[-1])
                                        for p in current_pos_list:
                                            self._update_position(
                                                strategy_id, p['symbol'], p['side'],
                                                float(p['size']), float(p['entry_price']),
                                                current_close,
                                                highest_price=new_hp
                                            )
                    else:
                        # ============================================
                        # 3. 闈濳绾挎洿鏂皌ick锛氱敤褰撳墠浠锋洿鏂版渶鍚庝竴鏍筀绾垮苟閲嶇畻鎸囨爣锛堢粺涓€tick鑺傚锛?
                        # ============================================
                        if 'df' in locals() and df is not None and len(df) > 0:
                            try:
                                realtime_df = df.copy()
                                realtime_df = self._update_dataframe_with_current_price(realtime_df, current_price, timeframe)

                                current_pos_list = self._get_current_positions(strategy_id, symbol)
                                initial_highest = 0.0
                                initial_position = 0
                                initial_avg_entry_price = 0.0
                                initial_position_count = 0
                                initial_last_add_price = 0.0

                                if current_pos_list:
                                    pos = current_pos_list[0]
                                    initial_highest = float(pos.get('highest_price', 0) or 0)
                                    pos_side = pos.get('side', 'long')
                                    initial_position = 1 if pos_side == 'long' else -1
                                    initial_avg_entry_price = float(pos.get('entry_price', 0) or 0)
                                    initial_position_count = 1
                                    initial_last_add_price = initial_avg_entry_price

                                indicator_result = self._execute_indicator_with_prices(
                                    indicator_code, realtime_df, trading_config,
                                    initial_highest_price=initial_highest,
                                    initial_position=initial_position,
                                    initial_avg_entry_price=initial_avg_entry_price,
                                    initial_position_count=initial_position_count,
                                    initial_last_add_price=initial_last_add_price
                                )
                                if indicator_result:
                                    pending_signals = indicator_result.get('pending_signals', [])
                                    new_hp = indicator_result.get('new_highest_price', 0)

                                    if new_hp > 0 and current_pos_list:
                                        for p in current_pos_list:
                                            self._update_position(
                                                strategy_id, p['symbol'], p['side'],
                                                float(p['size']), float(p['entry_price']),
                                                current_price,
                                                highest_price=new_hp
                                            )
                            except Exception as e:
                                logger.warning(f"Strategy {strategy_id} realtime indicator recompute failed: {str(e)}")
                    
                    # ============================================
                    # 4. Evaluate triggers once per tick
                    # ============================================
                    # 浼樺寲鐐?: 淇″彿鏈夋晥鏈熸竻鐞?(Signal Expiration)
                    current_ts = int(time.time())
                    if pending_signals:
                        expiration_threshold = timeframe_seconds * 2
                        valid_signals = []
                        for s in pending_signals:
                            signal_time = s.get('timestamp', 0)
                            if signal_time == 0 or (current_ts - signal_time) < expiration_threshold:
                                valid_signals.append(s)
                            else:
                                logger.warning(f"Signal expired and removed: {s}")
                        if len(valid_signals) != len(pending_signals):
                            pending_signals = valid_signals

                    # Unified cadence log: at most once per tick.
                    if pending_signals:
                        logger.info(f"[monitoring] strategy={strategy_id} price={current_price}, pending_signals={len(pending_signals)}")

                    # 妫€鏌ユ槸鍚︽湁寰呰Е鍙戠殑淇″彿
                    triggered_signals = []
                    signals_to_remove = []
                        
                    for signal_info in pending_signals:
                        signal_type = signal_info.get('type')  # 'open_long', 'close_long', 'open_short', 'close_short'
                        trigger_price = signal_info.get('trigger_price', 0)
                        
                        # 妫€鏌ヤ环鏍兼槸鍚﹁Е鍙?
                        triggered = False

                        # 銆愬叧閿慨澶嶃€戝钩浠?姝㈡崯姝㈢泩淇″彿榛樿鈥滅珛鍗宠Е鍙戔€?
                        exit_trigger_mode = trading_config.get('exit_trigger_mode', 'immediate')  # 'immediate' or 'price'
                        if signal_type in ['close_long', 'close_short'] and exit_trigger_mode == 'immediate':
                            triggered = True
                        
                        # 銆愬彲閫夈€戝紑浠?鍔犱粨淇″彿鏄惁鈥滅珛鍗宠Е鍙戔€?
                        entry_trigger_mode = trading_config.get('entry_trigger_mode', 'price')  # 'price' or 'immediate'
                        if signal_type in ['open_long', 'open_short', 'add_long', 'add_short'] and entry_trigger_mode == 'immediate':
                            triggered = True

                        if trigger_price > 0:
                            if signal_type in ['open_long', 'close_short', 'add_long']:
                                if current_price >= trigger_price:
                                    triggered = True
                            elif signal_type in ['open_short', 'close_long', 'add_short']:
                                if current_price <= trigger_price:
                                    triggered = True
                        else:
                            triggered = True
                        
                        if triggered:
                            triggered_signals.append(signal_info)
                            signals_to_remove.append(signal_info)

                    # ============================================
                    # 4.1 Server-side exits (config-driven): SL / TP / trailing
                    # ============================================
                    # Note: stop-loss is only applied when stop_loss_pct > 0. No default fallback.
                    risk_tp = self._server_side_take_profit_or_trailing_signal(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        current_price=float(current_price),
                        market_type=market_type,
                        leverage=float(leverage),
                        trading_config=trading_config,
                        timeframe_seconds=int(timeframe_seconds or 60),
                    )
                    if risk_tp:
                        triggered_signals.append(risk_tp)

                    risk_sl = self._server_side_stop_loss_signal(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        current_price=float(current_price),
                        market_type=market_type,
                        leverage=float(leverage),
                        trading_config=trading_config,
                        timeframe_seconds=int(timeframe_seconds or 60),
                    )
                    if risk_sl:
                        triggered_signals.append(risk_sl)
                        
                    # 浠庡緟瑙﹀彂鍒楄〃涓Щ闄ゅ凡瑙﹀彂鐨勪俊鍙?
                    for signal_info in signals_to_remove:
                        if signal_info in pending_signals:
                            pending_signals.remove(signal_info)
                        
                    # 鎵ц瑙﹀彂鐨勪俊鍙?
                    if triggered_signals:
                        logger.info(f"Strategy {strategy_id} triggered signals: {triggered_signals}")

                        current_positions = self._get_current_positions(strategy_id, symbol)
                        state = self._position_state(current_positions)

                        # Strict state machine + priority:
                        # - Only allow signals matching current state (flat/long/short).
                        # - Always prefer close_* over open_*/add_*.
                        # - Execute at most ONE signal per tick to avoid duplicated/re-entrant orders.
                        candidates = [s for s in triggered_signals if self._is_signal_allowed(state, s.get('type'))]

                        # If both directions are present while flat, choose by trade_direction (deterministic).
                        if state == "flat" and candidates:
                            td = (trade_direction or "both").strip().lower()
                            if td == "long":
                                candidates = [s for s in candidates if s.get("type") == "open_long"]
                            elif td == "short":
                                candidates = [s for s in candidates if s.get("type") == "open_short"]

                        candidates = sorted(
                            candidates,
                            key=lambda s: (
                                self._signal_priority(s.get("type")),
                                int(s.get("timestamp") or 0),
                                str(s.get("type") or ""),
                            ),
                        )

                        selected = None
                        now_i = int(time.time())
                        for s in candidates:
                            stype = s.get("type")
                            sts = int(s.get("timestamp") or 0)
                            if self._should_skip_signal_once_per_candle(
                                strategy_id=strategy_id,
                                symbol=symbol,
                                signal_type=str(stype or ""),
                                signal_ts=sts,
                                timeframe_seconds=int(timeframe_seconds or 60),
                                now_ts=now_i,
                            ):
                                continue
                            selected = s
                            break

                        if selected:
                            signal_type = selected.get('type')
                            position_size = selected.get('position_size', 0)
                            trigger_price = selected.get('trigger_price', current_price)
                            execute_price = trigger_price if trigger_price > 0 else current_price
                            signal_ts = int(selected.get("timestamp") or 0)

                            ok = self._execute_signal(
                                strategy_id=strategy_id,
                                strategy_name=strategy_name,
                                exchange=exchange,
                                symbol=symbol,
                                current_price=execute_price,
                                signal_type=signal_type,
                                position_size=position_size,
                                signal_ts=signal_ts,
                                current_positions=current_positions,
                                trade_direction=trade_direction,
                                leverage=leverage,
                                initial_capital=initial_capital,
                                market_type=market_type,
                                market_category=market_category,
                                execution_mode=execution_mode,
                                notification_config=notification_config,
                                trading_config=trading_config,
                                ai_model_config=ai_model_config,
                            )
                            if ok:
                                logger.info(f"Strategy {strategy_id} signal executed: {signal_type} @ {execute_price}")
                                # Notify portfolio positions linked to this symbol
                                try:
                                    from app.services.portfolio_monitor import notify_strategy_signal_for_positions
                                    notify_strategy_signal_for_positions(
                                        market=market_type or 'Crypto',
                                        symbol=symbol,
                                        signal_type=signal_type,
                                        signal_detail=f"绛栫暐: {strategy_name}\n淇″彿: {signal_type}\n浠锋牸: {execute_price:.4f}"
                                    )
                                except Exception as link_e:
                                    logger.warning(f"Strategy signal linkage notification failed: {link_e}")
                            else:
                                logger.warning(f"Strategy {strategy_id} signal rejected/failed: {signal_type}")

                    # Update positions once per tick.
                    self._update_positions(strategy_id, symbol, current_price)

                    # Heartbeat for UI observability (once per tick).
                    self._console_print(
                        f"[strategy:{strategy_id}] tick price={float(current_price or 0.0):.8f} pending_signals={len(pending_signals or [])}"
                    )
                    
                except Exception as e:
                    logger.error(f"Strategy {strategy_id} loop error: {str(e)}")
                    logger.error(traceback.format_exc())
                    self._console_print(f"[strategy:{strategy_id}] loop error: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            logger.error(f"Strategy {strategy_id} crashed: {str(e)}")
            logger.error(traceback.format_exc())
            self._console_print(f"[strategy:{strategy_id}] fatal error: {e}")
        finally:
            # 娓呯悊
            with self.lock:
                if strategy_id in self.running_strategies:
                    del self.running_strategies[strategy_id]
            self._console_print(f"[strategy:{strategy_id}] loop exited")
            logger.info(f"Strategy {strategy_id} loop exited")
    
    def _sync_positions_with_exchange(self, strategy_id: int, exchange: Any, symbol: str, market_type: str):
        """
        [Depracated] 淇″彿妯″紡涓嬫棤闇€鍚屾浜ゆ槗鎵€鎸佷粨
        """
        pass

    def _load_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                query = """
                    SELECT 
                        id, strategy_name, strategy_type, status,
                        initial_capital, leverage, decide_interval,
                        execution_mode, notification_config,
                        indicator_config, exchange_config, trading_config, ai_model_config,
                        market_category
                    FROM zhiyiquant_strategies_trading
                    WHERE id = %s
                """
                cursor.execute(query, (strategy_id,))
                strategy = cursor.fetchone()
                cursor.close()
            
            if strategy:
                # 瑙ｆ瀽JSON瀛楁
                for field in ['indicator_config', 'trading_config', 'notification_config', 'ai_model_config']:
                    if isinstance(strategy.get(field), str):
                        try:
                            strategy[field] = json.loads(strategy[field])
                        except:
                            strategy[field] = {}
                
                # exchange_config: local deployment stores plaintext JSON
                exchange_config_str = strategy.get('exchange_config', '{}')
                if isinstance(exchange_config_str, str) and exchange_config_str:
                    try:
                        strategy['exchange_config'] = json.loads(exchange_config_str)
                    except Exception as e:
                        logger.error(f"Strategy {strategy_id} failed to parse exchange_config: {str(e)}")
                        # 灏濊瘯鐩存帴瑙ｆ瀽 JSON锛堝悜鍚庡吋瀹癸級
                        try:
                            strategy['exchange_config'] = json.loads(exchange_config_str)
                        except:
                            strategy['exchange_config'] = {}
                else:
                    strategy['exchange_config'] = {}
            
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to load strategy config: {str(e)}")
            return None
    
    def _is_strategy_running(self, strategy_id: int) -> bool:
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute(
                    "SELECT status FROM zhiyiquant_strategies_trading WHERE id = %s",
                    (strategy_id,)
                )
                result = cursor.fetchone()
                cursor.close()
                return result and result.get('status') == 'running'
        except:
            return False
    
    def _init_exchange(
        self,
        exchange_config: Dict[str, Any],
        market_type: str = None,
        leverage: float = None,
        strategy_id: int = None
    ) -> Optional[ccxt.Exchange]:
        """Desktop runtime helper."""
        return None
    
    def _fetch_latest_kline(self, symbol: str, timeframe: str, limit: int = 500, market_category: str = 'Crypto') -> List[Dict[str, Any]]:
        """鑾峰彇鏈€鏂癒绾挎暟鎹紙浼樺厛浠庣紦瀛樿幏鍙栵級
        
        Args:
            symbol: 浜ゆ槗瀵?浠ｇ爜
            timeframe: 鏃堕棿鍛ㄦ湡
            limit: 鏁版嵁鏉℃暟
            market_category: 甯傚満绫诲瀷 (Crypto, USStock, Forex, Futures, AShare, HShare)
        """
        try:
            # 浣跨敤 KlineService 鑾峰彇K绾挎暟鎹紙鑷姩澶勭悊缂撳瓨锛?
            return self.kline_service.get_kline(
                market=market_category,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                before_time=int(time.time())
            )
        except Exception as e:
            logger.error(f"Failed to fetch K-lines for {market_category}:{symbol}: {str(e)}")
            return []
    
    def _fetch_current_price(self, exchange: Any, symbol: str, market_type: str = None, market_category: str = 'Crypto') -> Optional[float]:
        """鑾峰彇褰撳墠浠锋牸 (鏍规嵁 market_category 閫夋嫨姝ｇ‘鐨勬暟鎹簮)
        
        Args:
            exchange: 浜ゆ槗鎵€瀹炰緥锛堜俊鍙锋ā寮忎笅涓?None锛?
            symbol: 浜ゆ槗瀵?浠ｇ爜
            market_type: 浜ゆ槗绫诲瀷 (swap/spot)
            market_category: 甯傚満绫诲瀷 (Crypto, USStock, Forex, Futures, AShare, HShare)
        """
        # Local in-memory cache first
        cache_key = f"{market_category}:{(symbol or '').strip().upper()}"
        if cache_key and self._price_cache_ttl_sec > 0:
            now = time.time()
            try:
                with self._price_cache_lock:
                    item = self._price_cache.get(cache_key)
                    if item:
                        price, expiry = item
                        if expiry > now:
                            return float(price)
                        # expired
                        del self._price_cache[cache_key]
            except Exception:
                pass
            
        try:
            # 鏍规嵁 market_category 閫夋嫨姝ｇ‘鐨勬暟鎹簮
            # 鏀寔: Crypto, USStock, Forex, Futures, AShare, HShare
            ticker = DataSourceFactory.get_ticker(market_category, symbol)
            if ticker:
                price = float(ticker.get('last') or ticker.get('close') or 0)
                if price > 0:
                    if cache_key and self._price_cache_ttl_sec > 0:
                        try:
                            with self._price_cache_lock:
                                self._price_cache[cache_key] = (float(price), time.time() + self._price_cache_ttl_sec)
                        except Exception:
                            pass
                    return price
        except Exception as e:
            logger.warning(f"Failed to fetch price for {market_category}:{symbol}: {e}")
            
        return None

    def _server_side_stop_loss_signal(
        self,
        strategy_id: int,
        symbol: str,
        current_price: float,
        market_type: str,
        leverage: float,
        trading_config: Dict[str, Any],
        timeframe_seconds: int,
    ) -> Optional[Dict[str, Any]]:
        """
        鏈嶅姟绔厹搴曟鎹燂細褰撲环鏍肩┛閫忔鎹熺嚎鏃讹紝鐩存帴鐢熸垚 close_long/close_short 淇″彿銆?

        鐩殑锛氶槻姝⑩€滄寚鏍囧洖鏀鹃€昏緫瀵艰嚧鏈€鍚庝竴鏍筀绾挎病鏈?close_* 淇″彿鈥濇垨鈥滄彃閽堝弽寮瑰鑷翠簩娆¤Е鍙戞潯浠朵笉婊¤冻鈥濇椂涓嶆鎹熴€?
        """
        try:
            if trading_config is None:
                return None

            enabled = trading_config.get('enable_server_side_stop_loss', True)
            if str(enabled).lower() in ['0', 'false', 'no', 'off']:
                return None

            # 鑾峰彇褰撳墠鎸佷粨锛堜娇鐢ㄦ湰鍦版暟鎹簱璁板綍浣滀负椋庢帶渚濇嵁锛?
            current_positions = self._get_current_positions(strategy_id, symbol)
            if not current_positions:
                return None

            pos = current_positions[0]
            side = pos.get('side')
            if side not in ['long', 'short']:
                return None

            entry_price = float(pos.get('entry_price', 0) or 0)
            if entry_price <= 0 or current_price <= 0:
                return None

            # Stop-loss is config-driven: if stop_loss_pct is not set or <= 0, do NOT stop-loss.
            sl_cfg = trading_config.get('stop_loss_pct', 0)
            sl = 0.0
            try:
                sl_cfg = float(sl_cfg or 0)
                if sl_cfg > 1:
                    sl = sl_cfg / 100.0
                else:
                    sl = sl_cfg
            except Exception:
                sl = 0.0

            if sl <= 0:
                return None

            # Align with backtest semantics: risk percentages are defined on margin PnL,
            # so we convert to price move threshold by dividing by leverage.
            lev = max(1.0, float(leverage or 1.0))
            sl = sl / lev

            # Use candle start timestamp to deduplicate exit attempts within a candle.
            now_ts = int(time.time())
            tf = int(timeframe_seconds or 60)
            candle_ts = int(now_ts // tf) * tf

            # 澶氬ご锛氳穼鐮存鎹熺嚎
            if side == 'long':
                stop_line = entry_price * (1 - sl)
                if current_price <= stop_line:
                    return {
                        'type': 'close_long',
                        'trigger_price': 0,  # 绔嬪嵆瑙﹀彂锛堢敱 exit_trigger_mode 鎺у埗锛?
                        'position_size': 0,
                        'timestamp': candle_ts,
                        'reason': 'server_stop_loss',
                        'stop_loss_price': stop_line,
                    }
            # 绌哄ご锛氱獊鐮存鎹熺嚎
            elif side == 'short':
                stop_line = entry_price * (1 + sl)
                if current_price >= stop_line:
                    return {
                        'type': 'close_short',
                        'trigger_price': 0,
                        'position_size': 0,
                        'timestamp': candle_ts,
                        'reason': 'server_stop_loss',
                        'stop_loss_price': stop_line,
                    }

            return None
        except Exception as e:
            logger.warning(f"Strategy {strategy_id} server-side stop-loss check failed: {str(e)}")
            return None

    def _server_side_take_profit_or_trailing_signal(
        self,
        strategy_id: int,
        symbol: str,
        current_price: float,
        market_type: str,
        leverage: float,
        trading_config: Dict[str, Any],
        timeframe_seconds: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Server-side exits driven by trading_config (no indicator script required):
        - Fixed take-profit: take_profit_pct
        - Trailing stop: trailing_enabled + trailing_stop_pct + trailing_activation_pct

        Semantics align with BacktestService:
        - Percentages are defined on margin PnL; effective price threshold = pct / leverage.
        - When trailing is enabled, fixed take-profit is disabled to avoid ambiguity.
        """
        try:
            if not trading_config:
                return None

            current_positions = self._get_current_positions(strategy_id, symbol)
            if not current_positions:
                return None

            pos = current_positions[0]
            side = (pos.get('side') or '').strip().lower()
            if side not in ['long', 'short']:
                return None

            entry_price = float(pos.get('entry_price', 0) or 0)
            if entry_price <= 0 or current_price <= 0:
                return None

            lev = max(1.0, float(leverage or 1.0))

            tp = self._to_ratio(trading_config.get('take_profit_pct'))
            trailing_enabled = bool(trading_config.get('trailing_enabled'))
            trailing_pct = self._to_ratio(trading_config.get('trailing_stop_pct'))
            trailing_act = self._to_ratio(trading_config.get('trailing_activation_pct'))

            tp_eff = (tp / lev) if tp > 0 else 0.0
            trailing_pct_eff = (trailing_pct / lev) if trailing_pct > 0 else 0.0
            trailing_act_eff = (trailing_act / lev) if trailing_act > 0 else 0.0

            # Conflict rule: when trailing is enabled, fixed TP is disabled.
            if trailing_enabled and trailing_pct_eff > 0:
                tp_eff = 0.0
                # If activationPct is missing, reuse take_profit_pct as activation threshold.
                if trailing_act_eff <= 0 and tp > 0:
                    trailing_act_eff = tp / lev

            now_ts = int(time.time())
            tf = int(timeframe_seconds or 60)
            candle_ts = int(now_ts // tf) * tf

            # Highest/lowest tracking (persisted in DB so restart continues trailing correctly)
            try:
                hp = float(pos.get('highest_price') or 0.0)
            except Exception:
                hp = 0.0
            try:
                lp = float(pos.get('lowest_price') or 0.0)
            except Exception:
                lp = 0.0

            if hp <= 0:
                hp = entry_price
            hp = max(hp, float(current_price))

            if lp <= 0:
                lp = entry_price
            lp = min(lp, float(current_price))

            # Persist best-effort
            try:
                self._update_position(
                    strategy_id=strategy_id,
                    symbol=pos.get('symbol') or symbol,
                    side=side,
                    size=float(pos.get('size') or 0.0),
                    entry_price=entry_price,
                    current_price=float(current_price),
                    highest_price=hp,
                    lowest_price=lp,
                )
            except Exception:
                pass

            # 1) Trailing stop
            if trailing_enabled and trailing_pct_eff > 0:
                if side == 'long':
                    active = True
                    if trailing_act_eff > 0:
                        active = hp >= entry_price * (1 + trailing_act_eff)
                    if active:
                        stop_line = hp * (1 - trailing_pct_eff)
                        if current_price <= stop_line:
                            return {
                                'type': 'close_long',
                                'trigger_price': 0,
                                'position_size': 0,
                                'timestamp': candle_ts,
                                'reason': 'server_trailing_stop',
                                'trailing_stop_price': stop_line,
                                'highest_price': hp,
                            }
                else:
                    active = True
                    if trailing_act_eff > 0:
                        active = lp <= entry_price * (1 - trailing_act_eff)
                    if active:
                        stop_line = lp * (1 + trailing_pct_eff)
                        if current_price >= stop_line:
                            return {
                                'type': 'close_short',
                                'trigger_price': 0,
                                'position_size': 0,
                                'timestamp': candle_ts,
                                'reason': 'server_trailing_stop',
                                'trailing_stop_price': stop_line,
                                'lowest_price': lp,
                            }

            # 2) Fixed take-profit (only when trailing is disabled)
            if tp_eff > 0:
                if side == 'long':
                    tp_line = entry_price * (1 + tp_eff)
                    if current_price >= tp_line:
                        return {
                            'type': 'close_long',
                            'trigger_price': 0,
                            'position_size': 0,
                            'timestamp': candle_ts,
                            'reason': 'server_take_profit',
                            'take_profit_price': tp_line,
                        }
                else:
                    tp_line = entry_price * (1 - tp_eff)
                    if current_price <= tp_line:
                        return {
                            'type': 'close_short',
                            'trigger_price': 0,
                            'position_size': 0,
                            'timestamp': candle_ts,
                            'reason': 'server_take_profit',
                            'take_profit_price': tp_line,
                        }

            return None
        except Exception:
            return None
    
    def _klines_to_dataframe(self, klines: List[Dict[str, Any]]) -> pd.DataFrame:
        """Desktop runtime helper."""
        if not klines:
            # 杩斿洖绌虹殑 DataFrame锛屽寘鍚纭殑鍒?
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # 鍒涘缓 DataFrame
        df = pd.DataFrame(klines)
        
        # Convert time column.
        # IMPORTANT: use UTC tz-aware index to avoid timezone skew when computing candle boundaries.
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
            df = df.set_index('time')
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            df = df.set_index('timestamp')
        
        # 纭繚鍙寘鍚渶瑕佺殑鍒?
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        available_columns = [col for col in required_columns if col in df.columns]
        if not available_columns:
            logger.warning("K-lines are missing required columns")
            return pd.DataFrame(columns=required_columns)
        
        df = df[available_columns]
        
        # 寮哄埗杞崲鎵€鏈夋暟鍊煎垪涓?float64 绫诲瀷
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                # 鍏堣浆鎹负鏁板€肩被鍨嬶紝鐒跺悗寮哄埗杞崲涓?float64
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
        
        # 鍒犻櫎鍖呭惈 NaN 鐨勮
        df = df.dropna()
        
        return df

    def _update_dataframe_with_current_price(self, df: pd.DataFrame, current_price: float, timeframe: str) -> pd.DataFrame:
        """
        浣跨敤褰撳墠浠锋牸鏇存柊DataFrame鐨勬渶鍚庝竴鏍筀绾匡紙鐢ㄤ簬瀹炴椂璁＄畻锛?
        """
        if df is None or len(df) == 0:
            return df
            
        try:
            # 鑾峰彇鏈€鍚庝竴鏍筀绾跨殑鏃堕棿
            last_time = df.index[-1]
            
            # 璁＄畻褰撳墠鏃堕棿瀵瑰簲鐨凨绾胯捣濮嬫椂闂?
            from app.data_sources.base import TIMEFRAME_SECONDS
            timeframe_key = timeframe
            if timeframe_key not in TIMEFRAME_SECONDS:
                timeframe_key = str(timeframe_key).upper()
            if timeframe_key not in TIMEFRAME_SECONDS:
                timeframe_key = str(timeframe_key).lower()
            tf_seconds = TIMEFRAME_SECONDS.get(timeframe_key, 60)
            
            # Use epoch seconds directly to avoid naive datetime timezone conversion issues.
            last_ts = float(last_time.timestamp())
            now_ts = float(time.time())
            
            # 璁＄畻褰撳墠浠锋牸鎵€灞炵殑 K 绾垮紑濮嬫椂闂?
            current_period_start = int(now_ts // tf_seconds) * tf_seconds
            
            # 妫€鏌ユ渶鍚庝竴鏍筀绾挎槸鍚﹀氨鏄綋鍓嶅懆鏈熺殑
            if abs(last_ts - current_period_start) < 2:
                # 鏇存柊鏈€鍚庝竴鏍?
                df.iloc[-1, df.columns.get_loc('close')] = current_price
                df.iloc[-1, df.columns.get_loc('high')] = max(df.iloc[-1]['high'], current_price)
                df.iloc[-1, df.columns.get_loc('low')] = min(df.iloc[-1]['low'], current_price)
            elif current_period_start > last_ts:
                # 杩藉姞鏂拌
                new_row = pd.DataFrame({
                    'open': [current_price],
                    'high': [current_price],
                    'low': [current_price],
                    'close': [current_price],
                    'volume': [0.0]
                }, index=[pd.to_datetime(current_period_start, unit='s', utc=True)])
                
                df = pd.concat([df, new_row])
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to update realtime candle: {str(e)}")
            return df
    
    def _execute_indicator_with_prices(
        self, indicator_code: str, df: pd.DataFrame, trading_config: Dict[str, Any], 
        initial_highest_price: float = 0.0,
        initial_position: int = 0,
        initial_avg_entry_price: float = 0.0,
        initial_position_count: int = 0,
        initial_last_add_price: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        鎵ц鎸囨爣浠ｇ爜骞舵彁鍙栧緟瑙﹀彂鐨勪俊鍙峰拰浠锋牸
        """
        try:
            # 鎵ц鎸囨爣浠ｇ爜
            executed_df, exec_env = self._execute_indicator_df(
                indicator_code, df, trading_config, 
                initial_highest_price=initial_highest_price,
                initial_position=initial_position,
                initial_avg_entry_price=initial_avg_entry_price,
                initial_position_count=initial_position_count,
                initial_last_add_price=initial_last_add_price
            )
            if executed_df is None:
                return None
            
            # 鎻愬彇鏈€鏂扮殑 highest_price
            new_highest_price = exec_env.get('highest_price', 0.0)
            
            # 鎻愬彇鏈€鍚庝竴鏍筀绾跨殑鏃堕棿
            last_kline_time = int(df.index[-1].timestamp()) if hasattr(df.index[-1], 'timestamp') else int(time.time())
            
            # 鎻愬彇寰呰Е鍙戠殑淇″彿
            pending_signals = []
            
            # Supported indicator signal formats:
            # - Preferred (simple): df['buy'], df['sell'] as boolean
            # - Internal (4-way): df['open_long'], df['close_long'], df['open_short'], df['close_short'] as boolean
            if all(col in executed_df.columns for col in ['buy', 'sell']) and not all(col in executed_df.columns for col in ['open_long', 'close_long', 'open_short', 'close_short']):
                # Normalize buy/sell into 4-way columns for execution.
                td = trading_config.get('trade_direction', trading_config.get('tradeDirection', 'both'))
                td = str(td or 'both').lower()
                if td not in ['long', 'short', 'both']:
                    td = 'both'

                buy = executed_df['buy'].fillna(False).astype(bool)
                sell = executed_df['sell'].fillna(False).astype(bool)

                executed_df = executed_df.copy()
                if td == 'long':
                    executed_df['open_long'] = buy
                    executed_df['close_long'] = sell
                    executed_df['open_short'] = False
                    executed_df['close_short'] = False
                elif td == 'short':
                    executed_df['open_long'] = False
                    executed_df['close_long'] = False
                    executed_df['open_short'] = sell
                    executed_df['close_short'] = buy
                else:
                    executed_df['open_long'] = buy
                    executed_df['close_short'] = buy
                    executed_df['open_short'] = sell
                    executed_df['close_long'] = sell

            # Check for 4-way columns after normalization
            if all(col in executed_df.columns for col in ['open_long', 'close_long', 'open_short', 'close_short']):
                # 浼樺寲鐐?: 闃测€滀俊鍙烽棯鐑佲€?(Repainting)
                signal_mode = trading_config.get('signal_mode', 'confirmed') # 'confirmed' or 'aggressive'
                exit_signal_mode = trading_config.get('exit_signal_mode', 'aggressive') # 'confirmed' or 'aggressive'
                
                entry_check_set = set()
                exit_check_set = set()
                
                if len(executed_df) > 1:
                    # 濮嬬粓妫€鏌ヤ笂涓€鏍瑰凡瀹屾垚K绾?
                    entry_check_set.add(len(executed_df) - 2)
                    exit_check_set.add(len(executed_df) - 2)
                
                if signal_mode == 'aggressive' and len(executed_df) > 0:
                    entry_check_set.add(len(executed_df) - 1)
                
                if exit_signal_mode == 'aggressive' and len(executed_df) > 0:
                    exit_check_set.add(len(executed_df) - 1)
                
                # 缁熶竴閬嶅巻绱㈠紩锛堜繚鎸佺‘瀹氭€ф帓搴忥級
                check_indices = sorted(entry_check_set.union(exit_check_set), reverse=True)
                
                for idx in check_indices:
                    # 鑾峰彇璇绾跨殑鏀剁洏浠凤紙浣滀负榛樿瑙﹀彂浠凤級
                    close_price = float(executed_df['close'].iloc[idx])
                    # 璇ヤ俊鍙风殑鏃堕棿鎴?
                    signal_timestamp = int(executed_df.index[idx].timestamp()) if hasattr(executed_df.index[idx], 'timestamp') else last_kline_time
                    
                    # 寮€澶氫俊鍙凤紙浠呭湪 entry_check_set 涓鏌ワ級
                    if idx in entry_check_set and executed_df['open_long'].iloc[idx]:
                        trigger_price = close_price
                        position_size = 0.08
                        if 'position_size' in executed_df.columns:
                            pos_size = executed_df['position_size'].iloc[idx]
                            if pos_size > 0:
                                position_size = float(pos_size)
                        
                        if not any(s['type'] == 'open_long' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'open_long',
                                'trigger_price': trigger_price,
                                'position_size': position_size,
                                'timestamp': signal_timestamp
                            })
                    
                    # 骞冲淇″彿
                    if idx in exit_check_set and executed_df['close_long'].iloc[idx]:
                        trigger_price = close_price
                        if not any(s['type'] == 'close_long' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'close_long',
                                'trigger_price': trigger_price,
                                'position_size': 0,
                                'timestamp': signal_timestamp
                            })
                    
                    # 寮€绌轰俊鍙?
                    if idx in entry_check_set and executed_df['open_short'].iloc[idx]:
                        trigger_price = close_price
                        position_size = 0.08
                        if 'position_size' in executed_df.columns:
                            pos_size = executed_df['position_size'].iloc[idx]
                            if pos_size > 0:
                                position_size = float(pos_size)
                        
                        if not any(s['type'] == 'open_short' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'open_short',
                                'trigger_price': trigger_price,
                                'position_size': position_size,
                                'timestamp': signal_timestamp
                            })
                    
                    # 骞崇┖淇″彿
                    if idx in exit_check_set and executed_df['close_short'].iloc[idx]:
                        trigger_price = close_price
                        if not any(s['type'] == 'close_short' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'close_short',
                                'trigger_price': trigger_price,
                                'position_size': 0,
                                'timestamp': signal_timestamp
                            })
                            
                    # 鍔犲淇″彿
                    if idx in entry_check_set and 'add_long' in executed_df.columns and executed_df['add_long'].iloc[idx]:
                        trigger_price = close_price
                        position_size = 0.06
                        if 'position_size' in executed_df.columns:
                            pos_size = executed_df['position_size'].iloc[idx]
                            if pos_size > 0:
                                position_size = float(pos_size)

                        if not any(s['type'] == 'add_long' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'add_long',
                                'trigger_price': trigger_price,
                                'position_size': position_size,
                                'timestamp': signal_timestamp
                            })
                            
                    # 鍔犵┖淇″彿
                    if idx in entry_check_set and 'add_short' in executed_df.columns and executed_df['add_short'].iloc[idx]:
                        trigger_price = close_price
                        position_size = 0.06
                        if 'position_size' in executed_df.columns:
                            pos_size = executed_df['position_size'].iloc[idx]
                            if pos_size > 0:
                                position_size = float(pos_size)

                        if not any(s['type'] == 'add_short' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'add_short',
                                'trigger_price': trigger_price,
                                'position_size': position_size,
                                'timestamp': signal_timestamp
                            })

                    # Reduce / scale-out signals (optional)
                    # These are used by position management rules (trend/adverse reduce) and should be treated as exits.
                    if idx in exit_check_set and 'reduce_long' in executed_df.columns and executed_df['reduce_long'].iloc[idx]:
                        trigger_price = close_price
                        reduce_pct = 0.1
                        if 'reduce_size' in executed_df.columns:
                            try:
                                reduce_pct = float(executed_df['reduce_size'].iloc[idx] or 0)
                            except Exception:
                                reduce_pct = 0.1
                        elif 'position_size' in executed_df.columns:
                            try:
                                reduce_pct = float(executed_df['position_size'].iloc[idx] or 0)
                            except Exception:
                                reduce_pct = 0.1
                        if reduce_pct <= 0:
                            reduce_pct = 0.1
                        if not any(s['type'] == 'reduce_long' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'reduce_long',
                                'trigger_price': trigger_price,
                                'position_size': reduce_pct,
                                'timestamp': signal_timestamp
                            })

                    if idx in exit_check_set and 'reduce_short' in executed_df.columns and executed_df['reduce_short'].iloc[idx]:
                        trigger_price = close_price
                        reduce_pct = 0.1
                        if 'reduce_size' in executed_df.columns:
                            try:
                                reduce_pct = float(executed_df['reduce_size'].iloc[idx] or 0)
                            except Exception:
                                reduce_pct = 0.1
                        elif 'position_size' in executed_df.columns:
                            try:
                                reduce_pct = float(executed_df['position_size'].iloc[idx] or 0)
                            except Exception:
                                reduce_pct = 0.1
                        if reduce_pct <= 0:
                            reduce_pct = 0.1
                        if not any(s['type'] == 'reduce_short' and s.get('timestamp') == signal_timestamp for s in pending_signals):
                            pending_signals.append({
                                'type': 'reduce_short',
                                'trigger_price': trigger_price,
                                'position_size': reduce_pct,
                                'timestamp': signal_timestamp
                            })
            
            return {
                'pending_signals': pending_signals,
                'last_kline_time': last_kline_time,
                'new_highest_price': new_highest_price
            }
            
        except Exception as e:
            logger.error(f"Failed to execute indicator and extract prices: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _execute_indicator_df(
        self, indicator_code: str, df: pd.DataFrame, trading_config: Dict[str, Any], 
        initial_highest_price: float = 0.0,
        initial_position: int = 0,
        initial_avg_entry_price: float = 0.0,
        initial_position_count: int = 0,
        initial_last_add_price: float = 0.0
    ) -> tuple[Optional[pd.DataFrame], dict]:
        """Desktop runtime helper."""
        try:
            # 纭繚 DataFrame 鐨勬墍鏈夋暟鍊煎垪閮芥槸 float64 绫诲瀷
            df = df.copy()
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
                    else:
                        df[col] = df[col].astype('float64')
            
            # 鍒犻櫎鍖呭惈 NaN 鐨勮
            df = df.dropna()
            
            if len(df) == 0:
                logger.warning("DataFrame is empty; cannot execute indicator script")
                return None, {}
            
            # 鍒濆鍖栦俊鍙稴eries
            signals = pd.Series(0, index=df.index, dtype='float64')
            
            # 鍑嗗鎵ц鐜
            # Expose the full trading config to indicator scripts so frontend parameters
            # (scale-in/out, position sizing, risk params) can be used directly.
            # Also provide a backtest-modal compatible nested config object: cfg.risk/cfg.scale/cfg.position.
            tc = dict(trading_config or {})
            cfg = self._build_cfg_from_trading_config(tc)
            
            # === 鎸囨爣鍙傛暟鏀寔 ===
            # 浠?trading_config 鑾峰彇鐢ㄦ埛璁剧疆鐨勬寚鏍囧弬鏁?
            user_indicator_params = tc.get('indicator_params', {})
            # 瑙ｆ瀽鎸囨爣浠ｇ爜涓０鏄庣殑鍙傛暟
            declared_params = IndicatorParamsParser.parse_params(indicator_code)
            # 鍚堝苟鍙傛暟锛堢敤鎴峰€间紭鍏堬紝鍚﹀垯浣跨敤榛樿鍊硷級
            merged_params = IndicatorParamsParser.merge_params(declared_params, user_indicator_params)
            
            # === 鎸囨爣璋冪敤鍣ㄦ敮鎸?===
            # 鑾峰彇鐢ㄦ埛ID鍜屾寚鏍嘔D锛堢敤浜?call_indicator 鏉冮檺妫€鏌ワ級
            user_id = tc.get('user_id', 1)
            indicator_id = tc.get('indicator_id')
            indicator_caller = IndicatorCaller(user_id, indicator_id)
            
            local_vars = {
                'df': df,
                'open': df['open'].astype('float64'),
                'high': df['high'].astype('float64'),
                'low': df['low'].astype('float64'),
                'close': df['close'].astype('float64'),
                'volume': df['volume'].astype('float64'),
                'signals': signals,
                'np': np,
                'pd': pd,
                'trading_config': tc,
                'config': tc,  # alias
                'cfg': cfg,    # normalized nested config
                'params': merged_params,  # 鎸囨爣鍙傛暟 (鏂板)
                'call_indicator': indicator_caller.call_indicator,  # 璋冪敤鍏朵粬鎸囨爣 (鏂板)
                'leverage': float(trading_config.get('leverage', 1)),
                'initial_capital': float(trading_config.get('initial_capital', 1000)),
                'commission': 0.001,
                'trade_direction': str(trading_config.get('trade_direction', 'long')),
                'initial_highest_price': float(initial_highest_price),
                'initial_position': int(initial_position),
                'initial_avg_entry_price': float(initial_avg_entry_price),
                'initial_position_count': int(initial_position_count),
                'initial_last_add_price': float(initial_last_add_price)
            }
            
            import builtins
            def safe_import(name, *args, **kwargs):
                allowed_modules = ['numpy', 'pandas', 'math', 'json', 'time']
                if name in allowed_modules or name.split('.')[0] in allowed_modules:
                    return builtins.__import__(name, *args, **kwargs)
                raise ImportError(f"涓嶅厑璁稿鍏ユā鍧? {name}")
            
            safe_builtins = {k: getattr(builtins, k) for k in dir(builtins) 
                           if not k.startswith('_') and k not in [
                               'eval', 'exec', 'compile', 'open', 'input',
                               'help', 'exit', 'quit', '__import__',
                                'copyright', 'license'
                           ]}
            safe_builtins['__import__'] = safe_import
            
            exec_env = local_vars.copy()
            exec_env['__builtins__'] = safe_builtins
            
            pre_import_code = "import numpy as np\nimport pandas as pd\n"
            exec(pre_import_code, exec_env)
            
            # 杩欓噷鐨?safe_exec_code 鍋囪宸插瓨鍦?
            exec(indicator_code, exec_env)
            
            executed_df = exec_env.get('df', df)

            # Validation: if chart signals are provided, df['buy']/df['sell'] must exist for execution normalization.
            output_obj = exec_env.get('output')
            has_output_signals = isinstance(output_obj, dict) and isinstance(output_obj.get('signals'), list) and len(output_obj.get('signals')) > 0
            if has_output_signals and not all(col in executed_df.columns for col in ['buy', 'sell']):
                raise ValueError(
                    "Invalid indicator script: output['signals'] is provided, but df['buy'] and df['sell'] are missing. "
                    "Please set df['buy'] and df['sell'] as boolean columns (len == len(df))."
                )
            
            return executed_df, exec_env
            
        except Exception as e:
            logger.error(f"Failed to execute indicator script: {str(e)}")
            logger.error(traceback.format_exc())
            return None, {}
    
    def _execute_indicator(self, indicator_code: str, df: pd.DataFrame, trading_config: Dict[str, Any]) -> Optional[Any]:
        # Scalar adapter for callers that still expect a single return value.
        executed_df, _ = self._execute_indicator_df(indicator_code, df, trading_config)
        if executed_df is None:
            return None
        return 0

    def _get_current_positions(self, strategy_id: int, symbol: str) -> List[Dict[str, Any]]:
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                query = """
                    SELECT id, symbol, side, size, entry_price, highest_price, lowest_price
                    FROM zhiyiquant_strategy_positions
                    WHERE strategy_id = %s
                """
                cursor.execute(query, (strategy_id,))
                all_positions = cursor.fetchall()
                
                matched_positions = []
                for pos in all_positions:
                    # 绠€鍖栧尮閰嶉€昏緫锛氬彧鍖归厤鍓嶇紑
                    if pos['symbol'].split(':')[0] == symbol.split(':')[0]:
                        matched_positions.append(pos)
                
                cursor.close()
                return matched_positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {str(e)}")
            return []

    def _execute_trading_logic(self, *args, **kwargs):
        # Deprecated placeholder.
        pass
    
    def _execute_signal(
        self,
        strategy_id: int,
        strategy_name: str,
        exchange: Any,
        symbol: str,
        current_price: float,
        signal_type: str,
        position_size: float,
        current_positions: List[Dict[str, Any]],
        trade_direction: str,
        leverage: int,
        initial_capital: float,
        market_type: str = 'swap',
        market_category: str = 'Crypto',
        margin_mode: str = 'cross',
        stop_loss_price: float = None,
        take_profit_price: float = None,
        execution_mode: str = 'signal',
        notification_config: Optional[Dict[str, Any]] = None,
        trading_config: Optional[Dict[str, Any]] = None,
        ai_model_config: Optional[Dict[str, Any]] = None,
        signal_ts: int = 0,
    ):
        """Desktop runtime helper."""
        try:
            # Hard state-machine guard (double safety in addition to loop-level filtering).
            state = self._position_state(current_positions)
            if not self._is_signal_allowed(state, signal_type):
                return False

            # 1. 妫€鏌ヤ氦鏄撴柟鍚戦檺鍒?
            if market_type == 'spot' and 'short' in signal_type:
                 return False

            sig = (signal_type or "").strip().lower()

            # 1.1 寮€浠?AI 杩囨护锛堜粎 open_*锛?
            if sig in ("open_long", "open_short") and self._is_entry_ai_filter_enabled(ai_model_config=ai_model_config, trading_config=trading_config):
                ok_ai, ai_info = self._entry_ai_filter_allows(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    signal_type=sig,
                    ai_model_config=ai_model_config,
                    trading_config=trading_config,
                )
                if not ok_ai:
                    # Best-effort persist a browser notification so UI can show "HOLD due to AI filter".
                    reason = (ai_info or {}).get("reason") or "ai_filter_rejected"
                    ai_decision = (ai_info or {}).get("ai_decision") or ""
                    title = f"AI filter blocked signal | {symbol}"
                    msg = f"signal={sig}; ai={ai_decision or 'UNKNOWN'}; reason={reason}; action=hold"
                    self._persist_browser_notification(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        signal_type="ai_filter_hold",
                        title=title,
                        message=msg,
                        payload={
                            "event": "qd.ai_filter",
                            "strategy_id": int(strategy_id),
                            "strategy_name": str(strategy_name or ""),
                            "symbol": str(symbol or ""),
                            "signal_type": str(sig),
                            "ai_decision": str(ai_decision),
                            "reason": str(reason),
                            "signal_ts": int(signal_ts or 0),
                        },
                    )
                    logger.info(
                        f"AI entry filter rejected: strategy_id={strategy_id} symbol={symbol} signal={sig} ai={ai_decision} reason={reason}"
                    )
                    return False

            # 2. 璁＄畻涓嬪崟鏁伴噺
            available_capital = self._get_available_capital(strategy_id, initial_capital)
            
            amount = 0.0

            # Frontend position sizing alignment:
            # - open_* uses entry_pct from trading_config if provided (0~1 or 0~100 are both accepted)
            if sig in ("open_long", "open_short") and isinstance(trading_config, dict):
                ep = trading_config.get("entry_pct")
                if ep is not None:
                    position_size = self._to_ratio(ep, default=position_size if position_size is not None else 0.0)

            # Open / add sizing: position_size is treated as capital ratio in [0,1].
            if ('open' in sig or 'add' in sig):
                 if position_size is None or float(position_size) <= 0:
                     position_size = 0.05
                 position_ratio = self._to_ratio(position_size, default=0.05)
                 if market_type == 'spot':
                     amount = available_capital * position_ratio / current_price
                 else:
                     # Futures sizing: treat available_capital as margin budget.
                     # Notional = margin * leverage, so base quantity = (margin * leverage) / price.
                     amount = (available_capital * position_ratio * leverage) / current_price

            # Reduce sizing: position_size is treated as a reduce ratio (close X% of current position).
            if sig in ("reduce_long", "reduce_short"):
                pos_side = "long" if "long" in sig else "short"
                pos = next((p for p in current_positions if (p.get('side') or '').strip().lower() == pos_side), None)
                if not pos:
                    return False
                cur_size = float(pos.get("size") or 0.0)
                if cur_size <= 0:
                    return False
                reduce_ratio = self._to_ratio(position_size, default=0.1)
                reduce_amount = cur_size * reduce_ratio
                # If reduce is effectively full, treat as close_*.
                if reduce_amount >= cur_size * 0.999:
                    sig = "close_long" if pos_side == "long" else "close_short"
                    signal_type = sig
                    amount = cur_size
                else:
                    amount = reduce_amount
            
            # 3. 妫€鏌ュ弽鍚戞寔浠擄紙鍗曞悜鎸佷粨閫昏緫锛?
            # ... (绠€鍖栧鐞嗭紝鍋囪鏃犲弽鍚戞垨鐢辩敤鎴峰鐞? ...

            # 4. Execute order enqueue (PendingOrderWorker will dispatch notifications in signal mode)
            if 'close' in sig:
                # 骞充粨閫昏緫锛氭壘鍒板搴旀寔浠撳ぇ灏?
                pos = next((p for p in current_positions if p.get('side') and p['side'] in signal_type), None)
                if not pos:
                    return False
                amount = float(pos['size'] or 0.0)
                if amount <= 0:
                    return False

            if amount <= 0 and ('open' in signal_type or 'add' in signal_type):
                return False
            
            order_result = self._execute_exchange_order(
                exchange=exchange,
                strategy_id=strategy_id,
                symbol=symbol,
                signal_type=signal_type,
                amount=amount,
                ref_price=float(current_price or 0.0),
                market_type=market_type,
                market_category=market_category,
                leverage=leverage,
                execution_mode=execution_mode,
                notification_config=notification_config,
                signal_ts=int(signal_ts or 0),
            )
            
            if order_result and order_result.get('success'):
                # For live execution, the order is only enqueued here.
                # The actual fill/trade/position updates are performed by PendingOrderWorker.
                if str(execution_mode or "").strip().lower() == "live":
                    return True

                # 鏇存柊鏁版嵁搴撶姸鎬?(signal mode / local simulation)
                if 'open' in sig or 'add' in sig:
                    self._record_trade(
                        strategy_id=strategy_id, symbol=symbol, type=signal_type,
                        price=current_price, amount=amount, value=amount*current_price
                    )
                    side = 'short' if 'short' in signal_type else 'long'
                    
                    # 鏌ユ壘鐜版湁鎸佷粨浠ヨ绠楀潎浠?
                    old_pos = next((p for p in current_positions if p['side'] == side), None)
                    new_size = amount
                    new_entry = current_price
                    if old_pos:
                        old_size = float(old_pos['size'])
                        old_entry = float(old_pos['entry_price'])
                        new_size += old_size
                        new_entry = ((old_size * old_entry) + (amount * current_price)) / new_size

                    self._update_position(
                        strategy_id=strategy_id, symbol=symbol, side=side,
                        size=new_size, entry_price=new_entry, current_price=current_price
                    )
                elif sig.startswith("reduce_"):
                    # Partial scale-out: reduce position size, keep entry price unchanged.
                    # 淇″彿妯″紡涓嬭绠楅儴鍒嗗钩浠撶泩浜?
                    side = 'short' if 'short' in signal_type else 'long'
                    old_pos = next((p for p in current_positions if p.get('side') == side), None)
                    if not old_pos:
                        return True
                    old_size = float(old_pos.get('size') or 0.0)
                    old_entry = float(old_pos.get('entry_price') or 0.0)
                    
                    # 璁＄畻鍑忎粨閮ㄥ垎鐨勭泩浜忥紙淇″彿妯″紡涓嬶紝涓嶅惈鎵嬬画璐癸級
                    reduce_profit = None
                    if old_entry > 0 and amount > 0:
                        if side == 'long':
                            reduce_profit = (current_price - old_entry) * amount
                        else:
                            reduce_profit = (old_entry - current_price) * amount
                    
                    self._record_trade(
                        strategy_id=strategy_id, symbol=symbol, type=signal_type,
                        price=current_price, amount=amount, value=amount*current_price,
                        profit=reduce_profit
                    )
                    
                    new_size = max(0.0, old_size - float(amount or 0.0))
                    if new_size <= old_size * 0.001:
                        self._close_position(strategy_id, symbol, side)
                    else:
                        self._update_position(
                            strategy_id=strategy_id, symbol=symbol, side=side,
                            size=new_size, entry_price=old_entry, current_price=current_price
                        )
                elif 'close' in sig:
                    # 淇″彿妯″紡涓嬭绠楀钩浠撶泩浜?
                    side = 'short' if 'short' in signal_type else 'long'
                    old_pos = next((p for p in current_positions if p.get('side') == side), None)
                    
                    # 璁＄畻鐩堜簭锛堜俊鍙锋ā寮忎笅锛屼笉鍚墜缁垂锛?
                    close_profit = None
                    if old_pos:
                        entry_price = float(old_pos.get('entry_price') or 0)
                        if entry_price > 0 and amount > 0:
                            if side == 'long':
                                close_profit = (current_price - entry_price) * amount
                            else:
                                close_profit = (entry_price - current_price) * amount
                    
                    self._record_trade(
                        strategy_id=strategy_id, symbol=symbol, type=signal_type,
                        price=current_price, amount=amount, value=amount*current_price,
                        profit=close_profit
                    )
                    self._close_position(strategy_id, symbol, side)

                return True

            return False
            
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
            return False

    def _is_entry_ai_filter_enabled(self, *, ai_model_config: Optional[Dict[str, Any]], trading_config: Optional[Dict[str, Any]]) -> bool:
        """Desktop runtime helper."""
        amc = ai_model_config if isinstance(ai_model_config, dict) else {}
        tc = trading_config if isinstance(trading_config, dict) else {}

        # Accept multiple key names that may appear in saved configs.
        candidates = [
            amc.get("entry_ai_filter_enabled"),
            amc.get("entryAiFilterEnabled"),
            amc.get("ai_filter_enabled"),
            amc.get("aiFilterEnabled"),
            amc.get("enable_ai_filter"),
            amc.get("enableAiFilter"),
            tc.get("entry_ai_filter_enabled"),
            tc.get("ai_filter_enabled"),
            tc.get("enable_ai_filter"),
            tc.get("enableAiFilter"),
        ]
        for v in candidates:
            if v is None:
                continue
            if isinstance(v, bool):
                return bool(v)
            s = str(v).strip().lower()
            if s in ("1", "true", "yes", "y", "on", "enabled"):
                return True
            if s in ("0", "false", "no", "n", "off", "disabled"):
                return False
        return False

    def _entry_ai_filter_allows(
        self,
        *,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        ai_model_config: Optional[Dict[str, Any]],
        trading_config: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Run internal AI analysis and decide whether an entry signal is allowed.

        Returns:
          (allowed, info)
          - allowed: True -> proceed; False -> hold (reject open)
          - info: {ai_decision, reason, analysis_error?}
        """
        amc = ai_model_config if isinstance(ai_model_config, dict) else {}
        tc = trading_config if isinstance(trading_config, dict) else {}

        # Market for AnalysisService. Live trading executor is Crypto-focused.
        market = str(amc.get("market") or amc.get("analysis_market") or "Crypto").strip() or "Crypto"

        # Optional model override (OpenRouter model id)
        model = amc.get("model") or amc.get("openrouter_model") or amc.get("openrouterModel") or None
        model = str(model).strip() if model else None

        # Prefer zh-CN for local UI; can be overridden.
        language = amc.get("language") or amc.get("lang") or tc.get("language") or "zh-CN"
        language = str(language or "zh-CN")

        try:
            # 浣跨敤鏂扮殑 FastAnalysisService (鍗曟LLM璋冪敤锛屾洿蹇洿绋冲畾)
            from app.services.fast_analysis import get_fast_analysis_service

            service = get_fast_analysis_service()
            result = service.analyze(market, symbol, language, model=model)

            if isinstance(result, dict) and result.get("error"):
                return False, {"ai_decision": "", "reason": "analysis_error", "analysis_error": str(result.get("error") or "")}

            # FastAnalysisService 鐩存帴杩斿洖 decision 瀛楁
            ai_dec = str(result.get("decision", "")).strip().upper()
            if not ai_dec or ai_dec not in ("BUY", "SELL", "HOLD"):
                return False, {"ai_decision": ai_dec, "reason": "missing_ai_decision"}

            expected = "BUY" if signal_type == "open_long" else "SELL"
            confidence = result.get("confidence", 50)
            summary = result.get("summary", "")
            
            if ai_dec == expected:
                return True, {"ai_decision": ai_dec, "reason": "match", "confidence": confidence, "summary": summary}
            if ai_dec == "HOLD":
                return False, {"ai_decision": ai_dec, "reason": "ai_hold", "confidence": confidence, "summary": summary}
            return False, {"ai_decision": ai_dec, "reason": "direction_mismatch", "confidence": confidence, "summary": summary}
        except Exception as e:
            return False, {"ai_decision": "", "reason": "analysis_exception", "analysis_error": str(e)}

    def _extract_ai_trade_decision(self, analysis_result: Any) -> str:
        """
        Normalize AI analysis output into one of: BUY / SELL / HOLD / "".
        We primarily look at final_decision.decision, with fallbacks.
        """
        if not isinstance(analysis_result, dict):
            return ""

        def _pick(*paths: str) -> str:
            for p in paths:
                cur: Any = analysis_result
                ok = True
                for k in p.split("."):
                    if not isinstance(cur, dict):
                        ok = False
                        break
                    cur = cur.get(k)
                if ok and cur is not None:
                    s = str(cur).strip()
                    if s:
                        return s
            return ""

        raw = _pick("final_decision.decision", "trader_decision.decision", "decision", "final.decision")
        s = raw.strip().upper()
        if not s:
            return ""

        # Common variants / synonyms
        if "BUY" in s or s == "LONG" or "LONG" in s:
            return "BUY"
        if "SELL" in s or s == "SHORT" or "SHORT" in s:
            return "SELL"
        if "HOLD" in s or "WAIT" in s or "NEUTRAL" in s:
            return "HOLD"
        return s if s in ("BUY", "SELL", "HOLD") else ""

    def _persist_browser_notification(
        self,
        *,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        title: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        user_id: int = None,
    ) -> None:
        """Desktop runtime helper."""
        try:
            now = int(time.time())
            # Get user_id from strategy if not provided
            if user_id is None:
                try:
                    with get_db_connection() as db:
                        cur = db.cursor()
                        cur.execute("SELECT user_id FROM zhiyiquant_strategies_trading WHERE id = ?", (strategy_id,))
                        row = cur.fetchone()
                        cur.close()
                    user_id = int((row or {}).get('user_id') or 1)
                except Exception:
                    user_id = 1
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    INSERT INTO zhiyiquant_strategy_notifications
                    (user_id, strategy_id, symbol, signal_type, channels, title, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())
                    """,
                    (
                        int(user_id),
                        int(strategy_id),
                        str(symbol or ""),
                        str(signal_type or ""),
                        "browser",
                        str(title or ""),
                        str(message or ""),
                        json.dumps(payload or {}, ensure_ascii=False),
                    ),
                )
                db.commit()
                cur.close()
        except Exception as e:
            logger.warning(f"persist_browser_notification failed: {e}")

    def _execute_exchange_order(
        self,
        exchange: Any,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        amount: float,
        ref_price: Optional[float] = None,
        market_type: str = 'swap',
        market_category: str = 'Crypto',
        leverage: float = 1.0,
        margin_mode: str = 'cross',
        stop_loss_price: float = None,
        take_profit_price: float = None,
        # Order execution params (order_mode, maker_wait_sec, maker_offset_bps) are now
        # configured via environment variables: ORDER_MODE, MAKER_WAIT_SEC, MAKER_OFFSET_BPS
        # These parameters are accepted for call-site stability but ignored.
        order_mode: str = None,
        maker_wait_sec: float = None,
        maker_retries: int = 3,
        close_fallback_to_market: bool = True,
        open_fallback_to_market: bool = True,
        execution_mode: str = 'signal',
        notification_config: Optional[Dict[str, Any]] = None,
        signal_ts: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a signal into a concrete pending order and enqueue it into DB.

        A separate worker will poll `pending_orders` and dispatch:
        - execution_mode='signal': dispatch notifications (no real trading).
        - execution_mode='live': reserved for future live trading execution (not implemented).

        Note: Order execution settings (order_mode, maker_wait_sec, maker_offset_bps) are now
        configured via environment variables and not passed from strategy config.
        """
        try:
            # Reference price at enqueue time: use current tick price if provided to avoid extra fetch.
            if ref_price is None:
                ref_price = self._fetch_current_price(None, symbol, market_category=market_category) or 0.0
            ref_price = float(ref_price or 0.0)

            extra_payload = {
                "ref_price": float(ref_price or 0.0),
                "signal_ts": int(signal_ts or 0),
                "stop_loss_price": float(stop_loss_price or 0.0) if stop_loss_price is not None else 0.0,
                "take_profit_price": float(take_profit_price or 0.0) if take_profit_price is not None else 0.0,
                "margin_mode": str(margin_mode or "cross"),
                # Order execution params moved to env config (ORDER_MODE, MAKER_WAIT_SEC, MAKER_OFFSET_BPS)
                "maker_retries": int(maker_retries or 0),
                "close_fallback_to_market": bool(close_fallback_to_market),
                "open_fallback_to_market": bool(open_fallback_to_market),
            }
            pending_id = self._enqueue_pending_order(
                strategy_id=strategy_id,
                symbol=symbol,
                signal_type=signal_type,
                amount=float(amount or 0.0),
                price=float(ref_price or 0.0),
                signal_ts=int(signal_ts or 0),
                market_type=market_type,
                leverage=float(leverage or 1.0),
                execution_mode=execution_mode,
                notification_config=notification_config,
                extra_payload=extra_payload,
            )

            pending_flag = str(execution_mode or "").strip().lower() == "live"

            # Local "signal provider mode": we keep the local state machine moving forward.
            return {
                'success': True,
                'pending': bool(pending_flag),
                'order_id': f"pending_{pending_id or int(time.time()*1000)}",
                'filled_amount': 0 if pending_flag else amount,
                'filled_base_amount': 0 if pending_flag else amount,
                'filled_price': 0 if pending_flag else ref_price,
                'total_cost': 0 if pending_flag else (float(amount or 0.0) * float(ref_price or 0.0) if ref_price else 0),
                'fee': 0,
                'message': 'Order enqueued to pending_orders'
            }
        except Exception as e:
             logger.error(f"Signal execution failed: {e}")
             return {'success': False, 'error': str(e)}

    def _enqueue_pending_order(
        self,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        amount: float,
        price: float,
        signal_ts: int,
        market_type: str,
        leverage: float,
        execution_mode: str,
        notification_config: Optional[Dict[str, Any]] = None,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Desktop runtime helper."""
        try:
            now = int(time.time())
            # Local deployment supports both "signal" and "live" (live is executed by PendingOrderWorker).
            mode = (execution_mode or "signal").strip().lower()
            if mode not in ("signal", "live"):
                mode = "signal"

            payload: Dict[str, Any] = {
                "strategy_id": int(strategy_id),
                "symbol": symbol,
                "signal_type": signal_type,
                "market_type": market_type,
                "amount": float(amount or 0.0),
                "price": float(price or 0.0),
                "leverage": float(leverage or 1.0),
                "execution_mode": mode,
                "notification_config": notification_config or {},
                "signal_ts": int(signal_ts or 0),
            }
            if extra_payload and isinstance(extra_payload, dict):
                payload.update(extra_payload)

            with get_db_connection() as db:
                cur = db.cursor()

                # Extra dedup/cooldown guard (DB-based, more rigorous than local position state):
                # The indicator recompute runs on a fixed tick cadence, and some strategies may keep emitting the same
                # entry/exit signal across multiple ticks/candles (especially when orders fail).
                # We prevent spamming the queue by skipping if a very recent identical order already exists.
                #
                # Rules:
                # - If signal_ts is provided (>0), treat (strategy_id, symbol, signal_type, signal_ts) as the canonical
                #   "same candle" key: if any record already exists, do NOT enqueue again.
                # - Otherwise, fall back to the older (strategy_id, symbol, signal_type) cooldown guard.
                cooldown_sec = 30  # keep small; worker already retries the claimed order via attempts/max_attempts
                try:
                    stsig = int(signal_ts or 0)
                    # Strict "same candle" de-dup applies to open and close signals.
                    # Rationale: 
                    # - open_* signals should only trigger once per candle (prevents repeated entries)
                    # - close_* signals should only trigger once per candle (prevents repeated close attempts)
                    # - add_*/reduce_* signals may legitimately trigger multiple times within same candle
                    #   as price evolves for DCA/scaling strategies
                    sig_norm = str(signal_type or "").strip().lower()
                    strict_candle_dedup = stsig > 0 and sig_norm in ("open_long", "open_short", "close_long", "close_short")

                    if strict_candle_dedup:
                        cur.execute(
                            """
                            SELECT id, status, created_at
                            FROM pending_orders
                            WHERE strategy_id = %s
                              AND symbol = %s
                              AND signal_type = %s
                              AND signal_ts = %s
                            ORDER BY id DESC
                            LIMIT 1
                            """,
                            (int(strategy_id), str(symbol), str(signal_type), int(stsig)),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, status, created_at
                            FROM pending_orders
                            WHERE strategy_id = %s
                              AND symbol = %s
                              AND signal_type = %s
                            ORDER BY id DESC
                            LIMIT 1
                            """,
                            (int(strategy_id), str(symbol), str(signal_type)),
                        )
                    last = cur.fetchone() or {}
                    last_id = int(last.get("id") or 0)
                    last_status = str(last.get("status") or "").strip().lower()
                    last_created = int(last.get("created_at") or 0)
                    if last_id > 0:
                        if strict_candle_dedup:
                            logger.info(
                                f"enqueue_pending_order skipped (same candle): existing id={last_id} "
                                f"strategy_id={strategy_id} symbol={symbol} signal={signal_type} signal_ts={stsig} status={last_status}"
                            )
                            cur.close()
                            return None
                        if last_status in ("pending", "processing"):
                            logger.info(
                                f"enqueue_pending_order skipped: existing_inflight id={last_id} "
                                f"strategy_id={strategy_id} symbol={symbol} signal={signal_type} status={last_status}"
                            )
                            cur.close()
                            return None
                        if last_created > 0 and (now - last_created) < cooldown_sec:
                            logger.info(
                                f"enqueue_pending_order cooldown: last_id={last_id} last_status={last_status} "
                                f"age_sec={now - last_created} (<{cooldown_sec}) "
                                f"strategy_id={strategy_id} symbol={symbol} signal={signal_type}"
                            )
                            cur.close()
                            return None
                except Exception:
                    # Best-effort only; do not block enqueue on dedup query errors.
                    pass

                # Get user_id from strategy
                user_id = 1
                try:
                    cur.execute("SELECT user_id FROM zhiyiquant_strategies_trading WHERE id = %s", (strategy_id,))
                    row = cur.fetchone()
                    user_id = int((row or {}).get('user_id') or 1)
                except Exception:
                    pass

                cur.execute(
                    """
                    INSERT INTO pending_orders
                    (user_id, strategy_id, symbol, signal_type, signal_ts, market_type, order_type, amount, price,
                     execution_mode, status, priority, attempts, max_attempts, last_error, payload_json,
                     created_at, updated_at, processed_at, sent_at)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s,
                     NOW(), NOW(), NULL, NULL)
                    """,
                    (
                        int(user_id),
                        int(strategy_id),
                        symbol,
                        signal_type,
                        int(signal_ts or 0),
                        market_type or 'swap',
                        'market',
                        float(amount or 0.0),
                        float(price or 0.0),
                        mode,
                        'pending',
                        0,
                        0,
                        10,
                        '',
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                pending_id = cur.lastrowid
                db.commit()
                cur.close()
            return int(pending_id) if pending_id is not None else None
        except Exception as e:
            logger.error(f"enqueue_pending_order failed: {e}")
            return None

    def _place_stop_loss_order(self, *args, **kwargs):
        pass

    def _get_available_capital(self, strategy_id: int, initial_capital: float) -> float:
        """Desktop runtime helper."""
        return initial_capital

    def _calculate_current_equity(self, strategy_id: int, initial_capital: float) -> float:
        return initial_capital

    def _record_trade(self, strategy_id: int, symbol: str, type: str, price: float, amount: float, value: float, profit: float = None, commission: float = None):
        """Desktop runtime helper."""
        try:
            # Get user_id from strategy
            user_id = 1
            with get_db_connection() as db:
                cursor = db.cursor()
                try:
                    cursor.execute("SELECT user_id FROM zhiyiquant_strategies_trading WHERE id = %s", (strategy_id,))
                    row = cursor.fetchone()
                    user_id = int((row or {}).get('user_id') or 1)
                except Exception:
                    pass
                query = """
                    INSERT INTO zhiyiquant_strategy_trades (
                        user_id, strategy_id, symbol, type, price, amount, value, commission, profit, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """
                cursor.execute(query, (user_id, strategy_id, symbol, type, price, amount, value, commission or 0, profit))
                db.commit()
                cursor.close()
        except Exception as e:
            logger.error(f"Failed to record trade: {e}")

    def _update_position(
        self,
        strategy_id: int,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        current_price: float,
        highest_price: float = 0.0,
        lowest_price: float = 0.0,
    ):
        """Desktop runtime helper."""
        try:
            # Get user_id from strategy
            user_id = 1
            with get_db_connection() as db:
                cursor = db.cursor()
                try:
                    cursor.execute("SELECT user_id FROM zhiyiquant_strategies_trading WHERE id = %s", (strategy_id,))
                    row = cursor.fetchone()
                    user_id = int((row or {}).get('user_id') or 1)
                except Exception:
                    pass
                # 绠€鍖栵細鐩存帴 Update 鎴?Insert
                upsert_query = """
                    INSERT INTO zhiyiquant_strategy_positions (
                        user_id, strategy_id, symbol, side, size, entry_price, current_price, highest_price, lowest_price, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    ) ON CONFLICT(strategy_id, symbol, side) DO UPDATE SET
                        size = excluded.size,
                        entry_price = excluded.entry_price,
                        current_price = excluded.current_price,
                        highest_price = CASE WHEN excluded.highest_price > 0 THEN excluded.highest_price ELSE zhiyiquant_strategy_positions.highest_price END,
                        lowest_price = CASE WHEN excluded.lowest_price > 0 THEN excluded.lowest_price ELSE zhiyiquant_strategy_positions.lowest_price END,
                        updated_at = NOW()
                """
                cursor.execute(upsert_query, (
                    user_id, strategy_id, symbol, side, size, entry_price, current_price, highest_price, lowest_price
                ))
                db.commit()
                cursor.close()
        except Exception as e:
            logger.error(f"Failed to update position: {e}")

    def _close_position(self, strategy_id: int, symbol: str, side: str):
        """Delete a closed position snapshot."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("DELETE FROM zhiyiquant_strategy_positions WHERE strategy_id = %s AND symbol = %s AND side = %s", (strategy_id, symbol, side))
                db.commit()
                cursor.close()
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
    
    def _delete_position_by_id(self, position_id: int):
         pass

    def _update_positions(self, strategy_id: int, symbol: str, current_price: float):
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("UPDATE zhiyiquant_strategy_positions SET current_price = %s WHERE strategy_id = %s AND symbol = %s", (current_price, strategy_id, symbol))
                db.commit()
                cursor.close()
        except Exception:
            pass
            
    def _get_indicator_code_from_db(self, indicator_id: int) -> Optional[str]:
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SELECT code FROM zhiyiquant_indicator_codes WHERE id = %s", (indicator_id,))
                result = cursor.fetchone()
                return result['code'] if result else None
        except:
            return None
    
    def _get_all_positions(self, strategy_id: int) -> List[Dict[str, Any]]:
        """Get all positions for a strategy."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT id, symbol, side, size, entry_price, current_price, highest_price, lowest_price
                    FROM zhiyiquant_strategy_positions
                    WHERE strategy_id = %s
                """, (strategy_id,))
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get all positions: {e}")
            return []
    
    def _should_rebalance(self, strategy_id: int, rebalance_frequency: str) -> bool:
        """Check whether the strategy should rebalance."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT last_rebalance_at FROM zhiyiquant_strategies_trading WHERE id = %s
                """, (strategy_id,))
                result = cursor.fetchone()
                if not result or not result.get('last_rebalance_at'):
                    return True
                
                last_rebalance = result['last_rebalance_at']
                if isinstance(last_rebalance, str):
                    from datetime import datetime
                    last_rebalance = datetime.fromisoformat(last_rebalance.replace('Z', '+00:00'))
                
                now = datetime.now()
                delta = now - last_rebalance
                
                if rebalance_frequency == 'daily':
                    return delta.days >= 1
                elif rebalance_frequency == 'weekly':
                    return delta.days >= 7
                elif rebalance_frequency == 'monthly':
                    return delta.days >= 30
                return True
        except Exception as e:
            logger.error(f"Failed to check rebalance: {e}")
            return True
    
    def _update_last_rebalance(self, strategy_id: int):
        """Desktop runtime helper."""
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                # Try to update, if column doesn't exist, ignore
                try:
                    cursor.execute("""
                        UPDATE zhiyiquant_strategies_trading 
                        SET last_rebalance_at = NOW() 
                        WHERE id = %s
                    """, (strategy_id,))
                    db.commit()
                except Exception:
                    # Column may not exist, that's OK
                    pass
                cursor.close()
        except Exception as e:
            logger.warning(f"Failed to update last_rebalance_at: {e}")
    
    def _execute_cross_sectional_indicator(
        self,
        indicator_code: str,
        symbols: List[str],
        trading_config: Dict[str, Any],
        market_category: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """
        鎵ц鎴潰绛栫暐鎸囨爣锛岃繑鍥炴墍鏈夋爣鐨勭殑璇勫垎鍜屾帓搴?
        """
        try:
            # 鑾峰彇鎵€鏈夋爣鐨勭殑K绾挎暟鎹?
            all_data = {}
            for symbol in symbols:
                try:
                    klines = self._fetch_latest_kline(symbol, timeframe, limit=200, market_category=market_category)
                    if klines and len(klines) >= 2:
                        df = self._klines_to_dataframe(klines)
                        if len(df) > 0:
                            all_data[symbol] = df
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol}: {e}")
                    continue
            
            if not all_data:
                logger.error("No data available for cross-sectional strategy")
                return None
            
            # 鍑嗗鎵ц鐜
            exec_env = {
                'symbols': list(all_data.keys()),
                'data': all_data,  # {symbol: df}
                'scores': {},  # 鐢ㄤ簬瀛樺偍璇勫垎
                'rankings': [],  # 鐢ㄤ簬瀛樺偍鎺掑簭
                'np': np,
                'pd': pd,
                'trading_config': trading_config,
                'config': trading_config,
            }
            
            # 鎵ц鎸囨爣浠ｇ爜
            import builtins
            safe_builtins = {k: getattr(builtins, k) for k in dir(builtins) 
                           if not k.startswith('_') and k not in [
                               'eval', 'exec', 'compile', 'open', 'input',
                               'help', 'exit', 'quit', '__import__',
                           ]}
            exec_env['__builtins__'] = safe_builtins
            
            pre_import_code = "import numpy as np\nimport pandas as pd\n"
            exec(pre_import_code, exec_env)
            exec(indicator_code, exec_env)
            
            scores = exec_env.get('scores', {})
            rankings = exec_env.get('rankings', [])
            
            # 濡傛灉娌℃湁鎻愪緵rankings锛屾牴鎹畇cores鎺掑簭
            if not rankings and scores:
                rankings = sorted(scores.keys(), key=lambda x: scores.get(x, 0), reverse=True)
            
            return {
                'scores': scores,
                'rankings': rankings
            }
        except Exception as e:
            logger.error(f"Failed to execute cross-sectional indicator: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _generate_cross_sectional_signals(
        self,
        strategy_id: int,
        rankings: List[str],
        scores: Dict[str, float],
        trading_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        鏍规嵁鎺掑簭缁撴灉鐢熸垚鎴潰绛栫暐淇″彿
        """
        portfolio_size = trading_config.get('portfolio_size', 10)
        long_ratio = float(trading_config.get('long_ratio', 0.5))
        
        # 閫夋嫨鎸佷粨鏍囩殑
        long_count = int(portfolio_size * long_ratio)
        short_count = portfolio_size - long_count
        
        long_symbols = set(rankings[:long_count]) if long_count > 0 else set()
        short_symbols = set(rankings[-short_count:]) if short_count > 0 and len(rankings) >= short_count else set()
        
        # 鑾峰彇褰撳墠鎸佷粨
        current_positions = self._get_all_positions(strategy_id)
        current_long = {p['symbol'] for p in current_positions if p.get('side') == 'long'}
        current_short = {p['symbol'] for p in current_positions if p.get('side') == 'short'}
        
        signals = []
        
        # 鐢熸垚鍋氬淇″彿
        for symbol in long_symbols:
            if symbol not in current_long:
                # 濡傛灉褰撳墠娌℃湁澶氫粨锛屽紑澶?
                if symbol in current_short:
                    # 濡傛灉褰撳墠鏄┖浠擄紝鍏堝钩绌哄啀寮€澶?
                    signals.append({
                        'symbol': symbol,
                        'type': 'close_short',
                        'score': scores.get(symbol, 0)
                    })
                signals.append({
                    'symbol': symbol,
                    'type': 'open_long',
                    'score': scores.get(symbol, 0)
                })
        
        # 骞虫帀涓嶅湪鍋氬鍒楄〃涓殑澶氫粨
        for symbol in current_long:
            if symbol not in long_symbols:
                signals.append({
                    'symbol': symbol,
                    'type': 'close_long',
                    'score': scores.get(symbol, 0)
                })
        
        # 鐢熸垚鍋氱┖淇″彿
        for symbol in short_symbols:
            if symbol not in current_short:
                # 濡傛灉褰撳墠娌℃湁绌轰粨锛屽紑绌?
                if symbol in current_long:
                    # 濡傛灉褰撳墠鏄浠擄紝鍏堝钩澶氬啀寮€绌?
                    signals.append({
                        'symbol': symbol,
                        'type': 'close_long',
                        'score': scores.get(symbol, 0)
                    })
                signals.append({
                    'symbol': symbol,
                    'type': 'open_short',
                    'score': scores.get(symbol, 0)
                })
        
        # 骞虫帀涓嶅湪鍋氱┖鍒楄〃涓殑绌轰粨
        for symbol in current_short:
            if symbol not in short_symbols:
                signals.append({
                    'symbol': symbol,
                    'type': 'close_short',
                    'score': scores.get(symbol, 0)
                })
        
        return signals
    
    def _run_cross_sectional_strategy_loop(
        self,
        strategy_id: int,
        strategy: Dict[str, Any],
        trading_config: Dict[str, Any],
        indicator_config: Dict[str, Any],
        ai_model_config: Dict[str, Any],
        execution_mode: str,
        notification_config: Dict[str, Any],
        strategy_name: str,
        market_category: str,
        market_type: str,
        leverage: float,
        initial_capital: float,
        indicator_code: str,
        indicator_id: Optional[int]
    ):
        """
        鎴潰绛栫暐鎵ц寰幆
        """
        logger.info(f"Starting cross-sectional strategy loop for strategy {strategy_id}")
        
        symbol_list = trading_config.get('symbol_list', [])
        if not symbol_list:
            logger.error(f"Strategy {strategy_id} has no symbol_list for cross-sectional strategy")
            return
        
        timeframe = trading_config.get('timeframe', '1H')
        rebalance_frequency = trading_config.get('rebalance_frequency', 'daily')
        tick_interval_sec = int(trading_config.get('decide_interval', 300))
        
        last_tick_time = 0
        last_rebalance_time = 0
        
        while True:
            try:
                # 妫€鏌ョ瓥鐣ョ姸鎬?
                if not self._is_strategy_running(strategy_id):
                    logger.info(f"Cross-sectional strategy {strategy_id} stopped")
                    break
                
                current_time = time.time()
                
                # Sleep until next tick
                if last_tick_time > 0:
                    sleep_sec = (last_tick_time + tick_interval_sec) - current_time
                    if sleep_sec > 0:
                        time.sleep(min(sleep_sec, 1.0))
                        continue
                last_tick_time = current_time
                
                # 妫€鏌ユ槸鍚﹂渶瑕佽皟浠?
                if not self._should_rebalance(strategy_id, rebalance_frequency):
                    continue
                
                logger.info(f"Cross-sectional strategy {strategy_id} rebalancing...")
                
                # 鎵ц鎴潰鎸囨爣
                result = self._execute_cross_sectional_indicator(
                    indicator_code, symbol_list, trading_config, market_category, timeframe
                )
                
                if not result:
                    logger.warning(f"Cross-sectional indicator returned no result")
                    continue
                
                # 鐢熸垚淇″彿
                signals = self._generate_cross_sectional_signals(
                    strategy_id, result['rankings'], result['scores'], trading_config
                )
                
                if not signals:
                    logger.info(f"No rebalancing needed for strategy {strategy_id}")
                    self._update_last_rebalance(strategy_id)
                    continue
                
                logger.info(f"Generated {len(signals)} signals for cross-sectional strategy {strategy_id}")
                
                # 鎵归噺鎵ц浜ゆ槗
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=min(10, len(signals))) as executor:
                    futures = {}
                    for signal in signals:
                        future = executor.submit(
                            self._execute_signal,
                            strategy_id=strategy_id,
                            strategy_name=strategy_name,
                            exchange=None,  # Signal mode
                            symbol=signal['symbol'],
                            current_price=0.0,  # Will be fetched in _execute_signal
                            signal_type=signal['type'],
                            position_size=None,
                            current_positions=[],
                            trade_direction='both',
                            leverage=leverage,
                            initial_capital=initial_capital,
                            market_type=market_type,
                            market_category=market_category,
                            margin_mode='cross',
                            stop_loss_price=None,
                            take_profit_price=None,
                            execution_mode=execution_mode,
                            notification_config=notification_config,
                            trading_config=trading_config,
                            ai_model_config=ai_model_config,
                            signal_ts=int(current_time)
                        )
                        futures[future] = signal
                    
                    # 绛夊緟鎵€鏈変氦鏄撳畬鎴?
                    for future in as_completed(futures):
                        signal = futures[future]
                        try:
                            result = future.result(timeout=30)
                            if result:
                                logger.info(f"Successfully executed signal: {signal['symbol']} {signal['type']}")
                        except Exception as e:
                            logger.error(f"Failed to execute signal {signal['symbol']} {signal['type']}: {e}")
                
                # 鏇存柊璋冧粨鏃堕棿
                self._update_last_rebalance(strategy_id)
                last_rebalance_time = current_time
                
            except Exception as e:
                logger.error(f"Cross-sectional strategy loop error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(5)  # Wait before retrying
