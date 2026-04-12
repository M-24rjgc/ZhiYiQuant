"""
市场数据采集服务 - AI分析专用

设计理念：
1. 数据为王 - 先把数据获取做好、做稳定
2. 统一数据源 - 完全复用 DataSourceFactory 和 kline_service
3. 复用全球金融板块 - 宏观数据、情绪数据复用 global_market.py 的缓存
4. 快速稳定 - 不依赖慢速外部服务（如Jina Reader）

数据源映射：
- 价格/K线: DataSourceFactory (已验证，与K线模块、自选列表一致)
- 宏观数据: 复用 global_market.py (VIX, DXY, TNX, Fear&Greed等，带缓存)
- 新闻: Finnhub API (结构化数据，无需深度阅读)
- 基本面: Finnhub (美股) / akshare (A股) / 固定描述 (加密)
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

try:
    import yfinance as yf
except ImportError:
    yf = None

from app.data_sources import DataSourceFactory
from app.services.kline import KlineService
from app.utils.logger import get_logger
from app.config import APIKeys

logger = get_logger(__name__)


class MarketDataCollector:
    """
    市场数据采集器
    
    职责：为AI分析提供完整、准确、及时的市场数据
    
    数据层次：
    1. 核心数据 (必须成功): 价格、K线
    2. 分析数据 (增强): 技术指标、基本面
    3. 宏观数据 (可选): 复用 global_market.py (VIX, DXY, TNX, Fear&Greed等)
    4. 情绪数据 (可选): 新闻、市场情绪
    """
    
    def __init__(self):
        self.kline_service = KlineService()
        self._finnhub_client = None
        self._ak = None
        self._init_clients()
    
    def _init_clients(self):
        """初始化外部API客户端"""
        # Finnhub
        finnhub_key = APIKeys.FINNHUB_API_KEY
        if finnhub_key:
            try:
                import finnhub
                self._finnhub_client = finnhub.Client(api_key=finnhub_key)
            except Exception as e:
                logger.warning(f"Finnhub client init failed: {e}")
        
        # akshare
        try:
            import akshare as ak
            self._ak = ak
        except ImportError:
            logger.info("akshare not installed, A-share data will be limited")
    
    def collect_all(
        self,
        market: str,
        symbol: str,
        timeframe: str = "1D",
        include_macro: bool = True,
        include_news: bool = True,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        采集所有市场数据
        
        Args:
            market: 市场类型 (USStock, Crypto, AShare, HShare, Forex, Futures)
            symbol: 标的代码
            timeframe: K线周期
            include_macro: 是否包含宏观数据
            include_news: 是否包含新闻
            timeout: 总超时时间(秒)
            
        Returns:
            完整的市场数据字典
        """
        start_time = time.time()
        
        data = {
            "market": market,
            "symbol": symbol,
            "timeframe": timeframe,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # 核心数据
            "price": None,
            "kline": None,
            "indicators": {},
            # 基本面
            "fundamental": {},
            "company": {},
            # 宏观
            "macro": {},
            # 情绪
            "news": [],
            "sentiment": {},
            # 元数据
            "_meta": {
                "success_items": [],
                "failed_items": [],
                "duration_ms": 0
            }
        }
        
        # === 阶段1: 核心数据 (并行获取) ===
        # NOTE: 不使用 with 上下文，避免 as_completed 超时后被隐式 wait 卡住
        executor = ThreadPoolExecutor(max_workers=4)
        core_futures = {
            executor.submit(self._get_price, market, symbol): "price",
            executor.submit(self._get_kline, market, symbol, timeframe, 60): "kline",
        }

        # 如果需要基本面，也并行获取
        if market in ('USStock', 'AShare', 'HShare'):
            core_futures[executor.submit(self._get_fundamental, market, symbol)] = "fundamental"
            core_futures[executor.submit(self._get_company, market, symbol)] = "company"
        elif market == 'Crypto':
            # 加密货币的"基本面"是固定描述
            core_futures[executor.submit(self._get_crypto_info, symbol)] = "fundamental"

        try:
            for future in as_completed(core_futures, timeout=15):
                key = core_futures[future]
                try:
                    result = future.result(timeout=3)
                    if result:
                        data[key] = result
                        data["_meta"]["success_items"].append(key)
                    else:
                        data["_meta"]["failed_items"].append(key)
                except Exception as e:
                    logger.warning(f"Core data fetch failed ({key}): {e}")
                    data["_meta"]["failed_items"].append(key)
        except TimeoutError:
            logger.warning(f"Core data fetch timed out for {market}:{symbol}")
        finally:
            for future in core_futures:
                if not future.done():
                    future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
        
        # 计算技术指标 (本地计算，不需要外部API)
        if data.get("kline"):
            data["indicators"] = self._calculate_indicators(data["kline"])
            data["_meta"]["success_items"].append("indicators")
        
        # === 阶段2: 宏观数据 (如果需要) ===
        if include_macro:
            try:
                data["macro"] = self._get_macro_data(market, timeout=10)
                if data["macro"]:
                    data["_meta"]["success_items"].append("macro")
            except Exception as e:
                logger.warning(f"Macro data fetch failed: {e}")
                data["_meta"]["failed_items"].append("macro")
        
        # === 阶段3: 新闻/情绪 (如果需要) ===
        if include_news:
            try:
                # 获取公司名称以改善搜索
                company_name = None
                if data.get("company"):
                    company_name = data["company"].get("name")
                
                news_result = self._get_news(market, symbol, company_name, timeout=8)
                data["news"] = news_result.get("news", [])
                data["sentiment"] = news_result.get("sentiment", {})
                
                if data["news"]:
                    data["_meta"]["success_items"].append("news")
            except Exception as e:
                logger.warning(f"News fetch failed: {e}")
                data["_meta"]["failed_items"].append("news")
        
        # 记录总耗时
        data["_meta"]["duration_ms"] = int((time.time() - start_time) * 1000)
        logger.info(f"Market data collection completed for {market}:{symbol} in {data['_meta']['duration_ms']}ms")
        logger.info(f"  Success: {data['_meta']['success_items']}")
        logger.info(f"  Failed: {data['_meta']['failed_items']}")
        
        return data
    
    # ==================== 核心数据获取 ====================
    
    def _get_price(self, market: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时价格 - 使用 kline_service (与自选列表一致)
        """
        try:
            price_data = self.kline_service.get_realtime_price(market, symbol, force_refresh=True)
            if price_data and price_data.get('price', 0) > 0:
                # 安全转换为 float，处理 None 值
                def safe_float(val, default=0.0):
                    if val is None:
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default
                
                price = safe_float(price_data.get('price'))
                return {
                    "price": price,
                    "change": safe_float(price_data.get('change')),
                    "changePercent": safe_float(price_data.get('changePercent')),
                    "high": safe_float(price_data.get('high'), price),
                    "low": safe_float(price_data.get('low'), price),
                    "open": safe_float(price_data.get('open'), price),
                    "previousClose": safe_float(price_data.get('previousClose'), price),
                    "source": price_data.get('source', 'unknown')
                }
        except Exception as e:
            logger.warning(f"Price fetch failed for {market}:{symbol}: {e}")
        
        # 如果 kline_service 失败，尝试从 K 线最后一根获取价格
        try:
            klines = DataSourceFactory.get_kline(market, symbol, "1D", 2)
            if klines and len(klines) > 0:
                latest = klines[-1]
                price = float(latest.get('close', 0))
                if price > 0:
                    prev_close = float(klines[-2].get('close', price)) if len(klines) > 1 else price
                    change = price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                    
                    logger.info(f"Price fetched from K-line fallback for {market}:{symbol}: ${price}")
                    return {
                        "price": price,
                        "change": round(change, 6),
                        "changePercent": round(change_pct, 2),
                        "high": float(latest.get('high', price)),
                        "low": float(latest.get('low', price)),
                        "open": float(latest.get('open', price)),
                        "previousClose": prev_close,
                        "source": "kline_fallback"
                    }
        except Exception as e:
            logger.warning(f"K-line fallback price fetch also failed for {market}:{symbol}: {e}")
        
        return None
    
    def _get_kline(
        self, market: str, symbol: str, timeframe: str, limit: int = 60
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取K线数据 - 使用 DataSourceFactory (与K线模块一致)
        """
        try:
            klines = DataSourceFactory.get_kline(market, symbol, timeframe, limit)
            if klines and len(klines) > 0:
                return klines
        except Exception as e:
            logger.warning(f"Kline fetch failed for {market}:{symbol}: {e}")
        return None
    
    def _calculate_indicators(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算技术指标 (本地计算，无外部依赖)
        
        返回格式符合前端 FastAnalysisReport.vue 的期望：
        {
            rsi: { value, signal },
            macd: { signal, trend },
            moving_averages: { ma5, ma10, ma20, trend },
            levels: { support, resistance },
            volatility: { level, pct }
        }
        """
        if not klines or len(klines) < 5:
            return {}
        
        try:
            closes = [float(k.get('close', 0)) for k in klines]
            highs = [float(k.get('high', 0)) for k in klines]
            lows = [float(k.get('low', 0)) for k in klines]
            volumes = [float(k.get('volume', 0)) for k in klines]
            
            if not closes:
                return {}
            
            current_price = closes[-1]
            indicators = {}
            
            # ========== RSI ==========
            if len(closes) >= 15:
                rsi_value = self._calc_rsi(closes, 14)
                if rsi_value < 30:
                    rsi_signal = "oversold"
                elif rsi_value > 70:
                    rsi_signal = "overbought"
                else:
                    rsi_signal = "neutral"
                indicators['rsi'] = {
                    'value': round(rsi_value, 2),
                    'signal': rsi_signal,
                }
            
            # ========== MACD ==========
            if len(closes) >= 26:
                macd_raw = self._calc_macd(closes)
                macd_val = macd_raw.get('MACD', 0)
                macd_sig = macd_raw.get('MACD_signal', 0)
                macd_hist = macd_raw.get('MACD_histogram', 0)
                
                if macd_val > macd_sig and macd_hist > 0:
                    macd_signal = "bullish"
                    macd_trend = "golden_cross" if macd_hist > 0 else "bullish"
                elif macd_val < macd_sig and macd_hist < 0:
                    macd_signal = "bearish"
                    macd_trend = "death_cross" if macd_hist < 0 else "bearish"
                else:
                    macd_signal = "neutral"
                    macd_trend = "consolidating"
                
                indicators['macd'] = {
                    'value': round(macd_val, 6),
                    'signal_line': round(macd_sig, 6),
                    'histogram': round(macd_hist, 6),
                    'signal': macd_signal,
                    'trend': macd_trend,
                }
            
            # ========== 移动平均线 ==========
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else current_price
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current_price
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
            
            if current_price > ma5 > ma10 > ma20:
                ma_trend = "strong_uptrend"
            elif current_price > ma20:
                ma_trend = "uptrend"
            elif current_price < ma5 < ma10 < ma20:
                ma_trend = "strong_downtrend"
            elif current_price < ma20:
                ma_trend = "downtrend"
            else:
                ma_trend = "sideways"
            
            indicators['moving_averages'] = {
                'ma5': round(ma5, 6),
                'ma10': round(ma10, 6),
                'ma20': round(ma20, 6),
                'trend': ma_trend,
            }
            
            # ========== 支撑/阻力位 (多种方法综合) ==========
            # 方法1: 枢轴点 (Pivot Points) - 使用前一日数据
            if len(klines) >= 2:
                prev_high = float(klines[-2].get('high', highs[-2]) if len(highs) >= 2 else current_price * 1.02)
                prev_low = float(klines[-2].get('low', lows[-2]) if len(lows) >= 2 else current_price * 0.98)
                prev_close = float(klines[-2].get('close', closes[-2]) if len(closes) >= 2 else current_price)
                
                pivot = (prev_high + prev_low + prev_close) / 3
                r1 = 2 * pivot - prev_low  # 阻力位1
                s1 = 2 * pivot - prev_high  # 支撑位1
                r2 = pivot + (prev_high - prev_low)  # 阻力位2
                s2 = pivot - (prev_high - prev_low)  # 支撑位2
            else:
                pivot = current_price
                r1 = r2 = current_price * 1.02
                s1 = s2 = current_price * 0.98
            
            # 方法2: 近期高低点
            recent_highs = highs[-20:] if len(highs) >= 20 else highs
            recent_lows = lows[-20:] if len(lows) >= 20 else lows
            swing_high = max(recent_highs) if recent_highs else current_price * 1.05
            swing_low = min(recent_lows) if recent_lows else current_price * 0.95
            
            # 方法3: 布林带中轨上下 (如果有)
            bb_upper = indicators.get('bollinger', {}).get('upper', swing_high)
            bb_lower = indicators.get('bollinger', {}).get('lower', swing_low)
            
            # 综合取值: 取多种方法的平均/加权
            resistance = round((r1 + swing_high + bb_upper) / 3, 6) if bb_upper else round((r1 + swing_high) / 2, 6)
            support = round((s1 + swing_low + bb_lower) / 3, 6) if bb_lower else round((s1 + swing_low) / 2, 6)
            
            indicators['levels'] = {
                'support': support,
                'resistance': resistance,
                'pivot': round(pivot, 6),
                's1': round(s1, 6),
                'r1': round(r1, 6),
                's2': round(s2, 6),
                'r2': round(r2, 6),
                'swing_high': round(swing_high, 6),
                'swing_low': round(swing_low, 6),
                'method': 'pivot_swing_bb_avg'  # 标注计算方法
            }
            
            # ========== ATR 和波动率 ==========
            atr = 0
            if len(klines) >= 14:
                # 真实波动幅度 ATR (True Range)
                true_ranges = []
                for i in range(-14, 0):
                    h = float(klines[i].get('high', 0))
                    l = float(klines[i].get('low', 0))
                    prev_c = float(klines[i-1].get('close', 0)) if i > -14 else h
                    if h > 0 and l > 0:
                        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                        true_ranges.append(tr)
                
                atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0
                volatility_pct = (atr / current_price * 100) if current_price > 0 else 0
                
                if volatility_pct > 5:
                    volatility_level = "high"
                elif volatility_pct > 2:
                    volatility_level = "medium"
                else:
                    volatility_level = "low"
            else:
                volatility_level = "unknown"
                volatility_pct = 0
            
            indicators['volatility'] = {
                'level': volatility_level,
                'pct': round(volatility_pct, 2),
                'atr': round(atr, 6),  # 添加 ATR 绝对值
            }
            
            # ========== 止盈止损建议 (基于 ATR 和支撑/阻力) ==========
            # 止损: 基于 2x ATR 或支撑位，取更保守的
            atr_stop_loss = current_price - (2 * atr) if atr > 0 else current_price * 0.95
            support_stop = indicators['levels']['support']
            suggested_stop_loss = max(atr_stop_loss, support_stop * 0.99)  # 略低于支撑位
            
            # 止盈: 基于 3x ATR 或阻力位，考虑风险回报比
            atr_take_profit = current_price + (3 * atr) if atr > 0 else current_price * 1.05
            resistance_tp = indicators['levels']['resistance']
            suggested_take_profit = min(atr_take_profit, resistance_tp * 1.01)  # 略高于阻力位
            
            # 风险回报比
            risk = current_price - suggested_stop_loss
            reward = suggested_take_profit - current_price
            risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
            
            indicators['trading_levels'] = {
                'suggested_stop_loss': round(suggested_stop_loss, 6),
                'suggested_take_profit': round(suggested_take_profit, 6),
                'risk_reward_ratio': risk_reward_ratio,
                'atr_multiplier_sl': 2.0,  # 止损使用 2x ATR
                'atr_multiplier_tp': 3.0,  # 止盈使用 3x ATR
                'method': 'atr_support_resistance'
            }
            
            # ========== 布林带 (附加) ==========
            if len(closes) >= 20:
                bb_data = self._calc_bollinger(closes, 20, 2)
                indicators['bollinger'] = bb_data
            
            # ========== 成交量 (附加) ==========
            if len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                indicators['volume_ratio'] = round(volumes[-1] / avg_vol, 2) if avg_vol > 0 else 1.0
            
            # ========== 价格位置 (附加) ==========
            if len(closes) >= 20:
                high_20 = max(highs[-20:])
                low_20 = min(lows[-20:])
                if high_20 > low_20:
                    indicators['price_position'] = round((current_price - low_20) / (high_20 - low_20) * 100, 1)
                else:
                    indicators['price_position'] = 50.0
            
            # ========== 整体趋势 (附加) ==========
            indicators['trend'] = ma_trend
            indicators['current_price'] = round(current_price, 6)
            
            return indicators
            
        except Exception as e:
            logger.warning(f"Indicator calculation failed: {e}")
            return {}
    
    def _calc_rsi(self, closes: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def _calc_macd(self, closes: List[float]) -> Dict[str, float]:
        """计算MACD"""
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_values = [data[0]]
            for i in range(1, len(data)):
                ema_values.append((data[i] - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values
        
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        
        macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
        signal_line = ema(macd_line, 9)
        histogram = [macd_line[i] - signal_line[i] for i in range(len(closes))]
        
        return {
            'MACD': round(macd_line[-1], 4),
            'MACD_signal': round(signal_line[-1], 4),
            'MACD_histogram': round(histogram[-1], 4)
        }
    
    def _calc_bollinger(self, closes: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """计算布林带"""
        if len(closes) < period:
            return {}
        
        recent = closes[-period:]
        middle = sum(recent) / period
        
        variance = sum((x - middle) ** 2 for x in recent) / period
        std = variance ** 0.5
        
        return {
            'BB_upper': round(middle + std_dev * std, 4),
            'BB_middle': round(middle, 4),
            'BB_lower': round(middle - std_dev * std, 4),
            'BB_width': round((std_dev * std * 2) / middle * 100, 2) if middle > 0 else 0
        }
    
    # ==================== 基本面数据 ====================
    
    def _get_fundamental(self, market: str, symbol: str) -> Optional[Dict[str, Any]]:
        """获取基本面数据"""
        try:
            if market == 'USStock':
                return self._get_us_fundamental(symbol)
            elif market == 'AShare':
                return self._get_ashare_fundamental(symbol)
            elif market == 'HShare':
                return self._get_hshare_fundamental(symbol)
        except Exception as e:
            logger.warning(f"Fundamental data fetch failed for {market}:{symbol}: {e}")
        return None
    
    def _get_us_fundamental(self, symbol: str) -> Optional[Dict[str, Any]]:
        """美股基本面 - Finnhub + yfinance"""
        result = {}
        
        # Finnhub
        if self._finnhub_client:
            try:
                metrics = self._finnhub_client.company_basic_financials(symbol, 'all')
                if metrics and metrics.get('metric'):
                    m = metrics['metric']
                    result.update({
                        'pe_ratio': m.get('peBasicExclExtraTTM'),
                        'pb_ratio': m.get('pbQuarterly'),
                        'ps_ratio': m.get('psTTM'),
                        'market_cap': m.get('marketCapitalization'),
                        'dividend_yield': m.get('dividendYieldIndicatedAnnual'),
                        'beta': m.get('beta'),
                        '52w_high': m.get('52WeekHigh'),
                        '52w_low': m.get('52WeekLow'),
                        'roe': m.get('roeTTM'),
                        'eps': m.get('epsBasicExclExtraItemsTTM'),
                        'revenue_growth': m.get('revenueGrowthTTMYoy'),
                    })
            except Exception as e:
                logger.debug(f"Finnhub fundamental failed for {symbol}: {e}")
        
        # yfinance 补充
        if not result and yf is not None:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                result.update({
                    'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                    'pb_ratio': info.get('priceToBook'),
                    'market_cap': info.get('marketCap'),
                    'dividend_yield': info.get('dividendYield'),
                    'beta': info.get('beta'),
                    '52w_high': info.get('fiftyTwoWeekHigh'),
                    '52w_low': info.get('fiftyTwoWeekLow'),
                    'roe': info.get('returnOnEquity'),
                    'eps': info.get('trailingEps'),
                })
            except Exception as e:
                logger.debug(f"yfinance fundamental failed for {symbol}: {e}")
        
        return result if result else None
    
    def _get_ashare_fundamental(self, symbol: str) -> Optional[Dict[str, Any]]:
        """A股基本面 - akshare"""
        if not self._ak:
            return None
        
        try:
            # 个股指标
            df = self._ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                result = {}
                for _, row in df.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    if '市盈率' in item:
                        result['pe_ratio'] = value
                    elif '市净率' in item:
                        result['pb_ratio'] = value
                    elif '总市值' in item:
                        result['market_cap'] = value
                    elif 'ROE' in item or '净资产收益率' in item:
                        result['roe'] = value
                    elif '每股收益' in item:
                        result['eps'] = value
                return result if result else None
        except Exception as e:
            logger.debug(f"akshare fundamental failed for {symbol}: {e}")
        
        return None
    
    def _get_hshare_fundamental(self, symbol: str) -> Optional[Dict[str, Any]]:
        """港股基本面 - yfinance"""
        if yf is None:
            return None
        try:
            # 港股在yfinance的格式: 0700.HK, 9988.HK
            yf_symbol = f"{symbol}.HK"
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}
            
            return {
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'market_cap': info.get('marketCap'),
                'dividend_yield': info.get('dividendYield'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
            }
        except Exception as e:
            logger.debug(f"yfinance HShare fundamental failed for {symbol}: {e}")
        
        return None
    
    def _get_crypto_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """加密货币信息 (固定描述为主)"""
        # 常见加密货币的描述
        crypto_info = {
            'BTC': {
                'name': 'Bitcoin',
                'description': '比特币，数字黄金，市值第一的加密货币，作为价值存储和避险资产',
                'category': 'Store of Value',
            },
            'ETH': {
                'name': 'Ethereum',
                'description': '以太坊，智能合约平台，DeFi和NFT生态的基础设施',
                'category': 'Smart Contract Platform',
            },
            'BNB': {
                'name': 'Binance Coin',
                'description': '币安币，全球最大交易所的平台代币',
                'category': 'Exchange Token',
            },
            'SOL': {
                'name': 'Solana',
                'description': '高性能公链，主打高TPS和低Gas费',
                'category': 'Smart Contract Platform',
            },
            'XRP': {
                'name': 'Ripple',
                'description': '瑞波币，专注跨境支付解决方案',
                'category': 'Payment',
            },
            'DOGE': {
                'name': 'Dogecoin',
                'description': '狗狗币，Meme币代表，市场关注度高',
                'category': 'Meme',
            },
        }
        
        # 提取基础代币名
        base = symbol.split('/')[0] if '/' in symbol else symbol
        base = base.upper()
        
        if base in crypto_info:
            return crypto_info[base]
        
        return {
            'name': base,
            'description': f'{base} 是一种加密货币',
            'category': 'Unknown',
        }
    
    def _get_company(self, market: str, symbol: str) -> Optional[Dict[str, Any]]:
        """获取公司信息"""
        try:
            if market == 'USStock' and self._finnhub_client:
                profile = self._finnhub_client.company_profile2(symbol=symbol)
                if profile:
                    return {
                        'name': profile.get('name'),
                        'industry': profile.get('finnhubIndustry'),
                        'country': profile.get('country'),
                        'exchange': profile.get('exchange'),
                        'ipo_date': profile.get('ipo'),
                        'market_cap': profile.get('marketCapitalization'),
                        'website': profile.get('weburl'),
                    }
            
            elif market == 'AShare' and self._ak:
                df = self._ak.stock_individual_info_em(symbol=symbol)
                if df is not None and not df.empty:
                    result = {}
                    for _, row in df.iterrows():
                        item = row.get('item', '')
                        value = row.get('value', '')
                        if '名称' in item or '简称' in item:
                            result['name'] = value
                        elif '行业' in item:
                            result['industry'] = value
                    return result if result else None
                    
        except Exception as e:
            logger.debug(f"Company info fetch failed for {market}:{symbol}: {e}")
        
        return None
    
    # ==================== 宏观数据 (复用全球金融板块) ====================
    
    def _get_macro_data(self, market: str, timeout: int = 10) -> Dict[str, Any]:
        """
        获取宏观经济数据 - 复用 global_market.py 的函数和缓存
        
        优势：
        1. 数据与全球金融页面一致
        2. 复用30秒/5分钟缓存，降低API调用
        3. 已有完整的数据解读和级别判断
        """
        try:
            # 复用 global_market.py 的市场情绪数据 (有5分钟缓存)
            from app.routes.global_market import (
                _fetch_vix, _fetch_dollar_index, _fetch_yield_curve,
                _fetch_fear_greed_index,
                _get_cached, _set_cached
            )
            
            result = {}
            
            # 1) 尝试从缓存获取 (global_market 的缓存, 6小时有效)
            MACRO_CACHE_TTL = 21600  # 6 hours
            cached_sentiment = _get_cached("market_sentiment", MACRO_CACHE_TTL)
            if cached_sentiment:
                logger.info("Using cached sentiment data from global_market (6h cache)")
                # 转换格式
                if cached_sentiment.get('vix'):
                    vix = cached_sentiment['vix']
                    result['VIX'] = {
                        'name': 'VIX恐慌指数',
                        'description': vix.get('interpretation', ''),
                        'price': vix.get('value', 0),
                        'change': vix.get('change', 0),
                        'changePercent': vix.get('change', 0),
                        'level': vix.get('level', 'unknown'),
                    }
                
                if cached_sentiment.get('dxy'):
                    dxy = cached_sentiment['dxy']
                    result['DXY'] = {
                        'name': '美元指数',
                        'description': dxy.get('interpretation', ''),
                        'price': dxy.get('value', 0),
                        'change': dxy.get('change', 0),
                        'changePercent': dxy.get('change', 0),
                        'level': dxy.get('level', 'unknown'),
                    }
                
                if cached_sentiment.get('yield_curve'):
                    yc = cached_sentiment['yield_curve']
                    result['TNX'] = {
                        'name': '美债10年收益率',
                        'description': yc.get('interpretation', ''),
                        'price': yc.get('yield_10y', 0),
                        'change': yc.get('change', 0),
                        'changePercent': 0,
                        'spread': yc.get('spread', 0),
                        'level': yc.get('level', 'unknown'),
                    }
                
                if cached_sentiment.get('fear_greed'):
                    fg = cached_sentiment['fear_greed']
                    result['FEAR_GREED'] = {
                        'name': '恐惧贪婪指数',
                        'description': fg.get('classification', 'Neutral'),
                        'price': fg.get('value', 50),
                        'change': 0,
                        'changePercent': 0,
                    }
                
                if result:
                    return result
            
            # 2) 如果没有缓存，快速并行获取关键指标
            logger.info("Fetching macro data from global_market functions")
            
            executor = ThreadPoolExecutor(max_workers=4)
            futures = {
                executor.submit(_fetch_vix): "VIX",
                executor.submit(_fetch_dollar_index): "DXY",
                executor.submit(_fetch_yield_curve): "TNX",
                executor.submit(_fetch_fear_greed_index): "FEAR_GREED",
            }

            try:
                for future in as_completed(futures, timeout=timeout):
                    key = futures[future]
                    try:
                        data = future.result(timeout=5)
                        if data:
                            # 转换为统一格式
                            if key == 'VIX':
                                result[key] = {
                                    'name': 'VIX恐慌指数',
                                    'description': data.get('interpretation', ''),
                                    'price': data.get('value', 0),
                                    'change': data.get('change', 0),
                                    'changePercent': data.get('change', 0),
                                    'level': data.get('level', 'unknown'),
                                }
                            elif key == 'DXY':
                                result[key] = {
                                    'name': '美元指数',
                                    'description': data.get('interpretation', ''),
                                    'price': data.get('value', 0),
                                    'change': data.get('change', 0),
                                    'changePercent': data.get('change', 0),
                                    'level': data.get('level', 'unknown'),
                                }
                            elif key == 'TNX':
                                result[key] = {
                                    'name': '美债10年收益率',
                                    'description': data.get('interpretation', ''),
                                    'price': data.get('yield_10y', 0),
                                    'change': data.get('change', 0),
                                    'changePercent': 0,
                                    'spread': data.get('spread', 0),
                                    'level': data.get('level', 'unknown'),
                                }
                            elif key == 'FEAR_GREED':
                                result[key] = {
                                    'name': '恐惧贪婪指数',
                                    'description': data.get('classification', 'Neutral'),
                                    'price': data.get('value', 50),
                                    'change': 0,
                                    'changePercent': 0,
                                }
                    except Exception as e:
                        logger.debug(f"Macro indicator {key} fetch failed: {e}")
            except TimeoutError:
                logger.warning("Macro data fetch timed out")
            finally:
                for future in futures:
                    if not future.done():
                        future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
            
            # 注：黄金等大宗商品数据不再作为宏观指标获取
            # 原因：1) 如果分析的是黄金，价格已在 _get_price 中获取
            #       2) 减少 API 调用，提高稳定性
            pass
            
            return result
            
        except ImportError as e:
            logger.warning(f"Could not import from global_market: {e}")
            return {}
        except Exception as e:
            logger.error(f"_get_macro_data failed: {e}")
            return {}
    
    # ==================== 新闻/情绪数据 ====================
    
    def _get_news(
        self, market: str, symbol: str, company_name: Optional[str] = None, timeout: int = 8
    ) -> Dict[str, Any]:
        """
        获取新闻和情绪数据
        
        策略（按优先级）：
        1. 结构化API (Finnhub) - 美股首选
        2. akshare 多源 - A股首选（东方财富/新浪/同花顺/雪球）
        3. 搜索引擎 (Bocha/Tavily) - 补充搜索
        4. 情绪分析 - Finnhub 社交媒体情绪
        """
        news_list = []
        sentiment = {}
        
        # === 1) Finnhub 新闻 (美股首选) ===
        if self._finnhub_client:
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                
                raw_news = []
                
                if market == 'USStock':
                    raw_news = self._finnhub_client.company_news(symbol, _from=start_date, to=end_date)
                elif market == 'Crypto':
                    # 加密货币通用新闻
                    raw_news = self._finnhub_client.general_news('crypto', min_id=0)
                elif market not in ('AShare', 'HShare'):
                    # 其他市场通用新闻
                    raw_news = self._finnhub_client.general_news('general', min_id=0)
                
                if raw_news:
                    for item in raw_news[:10]:
                        if not item.get('headline'):
                            continue
                        news_list.append({
                            "datetime": datetime.fromtimestamp(item.get('datetime', 0)).strftime('%Y-%m-%d %H:%M'),
                            "headline": item.get('headline', ''),
                            "summary": item.get('summary', '')[:300] if item.get('summary') else '',
                            "source": item.get('source', 'Finnhub'),
                            "url": item.get('url', ''),
                            "sentiment": item.get('sentiment', 'neutral'),
                        })
                    logger.info(f"Finnhub 新闻获取成功: {len(news_list)} 条")
            except Exception as e:
                logger.debug(f"Finnhub news fetch failed: {e}")
        
        # === 2) Finnhub 情绪分数 (美股社交媒体情绪) ===
        if self._finnhub_client and market == 'USStock':
            try:
                social = self._finnhub_client.stock_social_sentiment(symbol)
                if social:
                    sentiment['reddit'] = social.get('reddit', {})
                    sentiment['twitter'] = social.get('twitter', {})
            except Exception as e:
                logger.debug(f"Finnhub sentiment fetch failed: {e}")
        
        # === 3) A股多源新闻 (akshare) ===
        if market == 'AShare' and self._ak:
            ashare_news = self._get_ashare_news_multi_source(symbol)
            news_list.extend(ashare_news)
        
        # === 4) 港股新闻 (akshare) ===
        if market == 'HShare' and self._ak:
            hshare_news = self._get_hshare_news(symbol)
            news_list.extend(hshare_news)
        
        # === 5) 搜索引擎补充 (如果新闻太少) ===
        if len(news_list) < 5:
            search_executor = ThreadPoolExecutor(max_workers=1)
            search_future = search_executor.submit(self._get_news_from_search, market, symbol, company_name)
            try:
                # 搜索是可选增强项，严格限制等待时间，避免拖慢主流程
                search_news = search_future.result(timeout=max(1, min(timeout, 4)))
                news_list.extend(search_news)
            except TimeoutError:
                logger.warning(f"Search news timed out for {market}:{symbol}, skip optional news")
            except Exception as e:
                logger.debug(f"Search news fetch failed: {e}")
            finally:
                if not search_future.done():
                    search_future.cancel()
                search_executor.shutdown(wait=False, cancel_futures=True)
        
        # 去重（按标题）
        seen_titles = set()
        unique_news = []
        for item in news_list:
            title = item.get('headline', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(item)
        
        # 按时间排序
        unique_news.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        
        return {
            "news": unique_news[:15],  # 最多15条
            "sentiment": sentiment,
        }
    
    def _get_ashare_news_multi_source(self, symbol: str) -> List[Dict[str, Any]]:
        """
        A股多源新闻获取
        
        来源（按优先级）：
        1. 东方财富个股新闻 (stock_news_em)
        2. 新浪财经滚动新闻 (stock_news_sina)
        3. 同花顺个股新闻 (stock_news_ths)
        4. 雪球热帖 (stock_xuqiu)
        """
        news_list = []
        
        # 1) 东方财富个股新闻
        try:
            df = self._ak.stock_news_em(symbol=symbol)
            if df is not None and not df.empty:
                for _, row in df.head(8).iterrows():
                    news_list.append({
                        "datetime": str(row.get('发布时间', ''))[:16],
                        "headline": row.get('新闻标题', ''),
                        "summary": row.get('新闻内容', '')[:200] if row.get('新闻内容') else '',
                        "source": "东方财富",
                        "url": row.get('新闻链接', ''),
                        "sentiment": 'neutral',
                    })
                logger.debug(f"东方财富新闻: {len(df)} 条")
        except Exception as e:
            logger.debug(f"东方财富新闻获取失败: {e}")
        
        # 2) 新浪财经个股新闻
        try:
            # 注意：akshare 的新浪新闻接口可能需要股票名称而非代码
            df = self._ak.stock_news_sina(symbol=symbol)
            if df is not None and not df.empty:
                for _, row in df.head(5).iterrows():
                    title = row.get('title', '') or row.get('新闻标题', '')
                    if title and title not in [n.get('headline') for n in news_list]:
                        news_list.append({
                            "datetime": str(row.get('time', row.get('发布时间', '')))[:16],
                            "headline": title,
                            "summary": row.get('content', row.get('新闻内容', ''))[:200] if row.get('content') or row.get('新闻内容') else '',
                            "source": "新浪财经",
                            "url": row.get('url', row.get('新闻链接', '')),
                            "sentiment": 'neutral',
                        })
                logger.debug(f"新浪财经新闻: {len(df)} 条")
        except Exception as e:
            logger.debug(f"新浪财经新闻获取失败: {e}")
        
        # 3) 同花顺个股新闻
        try:
            df = self._ak.stock_news_ths(symbol=symbol)
            if df is not None and not df.empty:
                for _, row in df.head(5).iterrows():
                    title = row.get('标题', '') or row.get('title', '')
                    if title and title not in [n.get('headline') for n in news_list]:
                        news_list.append({
                            "datetime": str(row.get('发布时间', row.get('time', '')))[:16],
                            "headline": title,
                            "summary": row.get('内容', row.get('content', ''))[:200] if row.get('内容') or row.get('content') else '',
                            "source": "同花顺",
                            "url": row.get('链接', row.get('url', '')),
                            "sentiment": 'neutral',
                        })
                logger.debug(f"同花顺新闻: {len(df)} 条")
        except Exception as e:
            logger.debug(f"同花顺新闻获取失败: {e}")
        
        # 4) 雪球热门讨论
        try:
            df = self._ak.stock_xuqiu(symbol=symbol)
            if df is not None and not df.empty:
                for _, row in df.head(3).iterrows():
                    title = row.get('标题', '') or row.get('title', '')
                    if title and title not in [n.get('headline') for n in news_list]:
                        news_list.append({
                            "datetime": str(row.get('发布时间', row.get('time', '')))[:16],
                            "headline": title,
                            "summary": row.get('内容摘要', row.get('content', ''))[:200] if row.get('内容摘要') or row.get('content') else '',
                            "source": "雪球",
                            "url": row.get('链接', row.get('url', '')),
                            "sentiment": 'neutral',
                        })
                logger.debug(f"雪球热帖: {len(df)} 条")
        except Exception as e:
            logger.debug(f"雪球热帖获取失败: {e}")
        
        return news_list
    
    def _get_hshare_news(self, symbol: str) -> List[Dict[str, Any]]:
        """
        港股新闻获取

        注意：akshare 的 stock_hk_spot_em 是全市场快照，单次调用较重，
        不适合放在 AI 分析请求链路中（会显著拉长响应时间）。
        港股新闻优先由搜索引擎补充（已设置严格超时）。
        """
        return []
    
    def _get_news_from_search(
        self, market: str, symbol: str, company_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        从搜索引擎获取新闻
        
        使用增强的搜索服务 (Bocha/Tavily/SerpAPI)
        """
        news_list = []
        
        try:
            from app.services.search import get_search_service
            search_service = get_search_service()
            
            if not search_service.is_available:
                return news_list
            
            # 构建搜索名称
            search_name = company_name or symbol
            
            # 搜索股票新闻
            response = search_service.search_stock_news(
                stock_code=symbol,
                stock_name=search_name,
                market=market,
                max_results=5
            )
            
            if response.success and response.results:
                for result in response.results:
                    news_list.append({
                        "datetime": result.published_date or datetime.now().strftime('%Y-%m-%d'),
                        "headline": result.title,
                        "summary": result.snippet[:200] if result.snippet else '',
                        "source": f"搜索:{result.source}",
                        "url": result.url,
                        "sentiment": result.sentiment,
                    })
                logger.info(f"搜索引擎新闻补充: {len(news_list)} 条 (来源: {response.provider})")
        except Exception as e:
            logger.debug(f"搜索引擎新闻获取失败: {e}")
        
        return news_list


# 全局实例
_collector: Optional[MarketDataCollector] = None

def get_market_data_collector() -> MarketDataCollector:
    """获取市场数据采集器单例"""
    global _collector
    if _collector is None:
        _collector = MarketDataCollector()
    return _collector
