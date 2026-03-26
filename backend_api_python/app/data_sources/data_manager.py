# -*- coding: utf-8 -*-
"""
===================================
A股数据源管理器 (Data Manager)
===================================

参考 daily_stock_analysis 项目的 DataFetcherManager 实现
统一管理多个A股数据源，实现自动故障切换

数据源优先级：
1. 东方财富 (Eastmoney) - 数据最全，首选
2. 腾讯财经 (Tencent) - 稳定可靠
3. 新浪财经 (Sina) - 轻量级
4. Akshare - 功能丰富，但容易被封
5. yfinance - 国际数据源，兜底
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests

from app.data_sources.circuit_breaker import (
    CircuitBreaker,
    get_ashare_circuit_breaker,
    get_realtime_circuit_breaker
)
from app.data_sources.cache_manager import (
    DataCache,
    get_realtime_cache,
    get_kline_cache,
    generate_kline_cache_key
)
from app.data_sources.rate_limiter import (
    RateLimiter,
    get_eastmoney_limiter,
    get_tencent_limiter,
    get_akshare_limiter,
    get_request_headers,
    retry_with_backoff
)
from app.utils.logger import get_logger
from app.utils.http import get_retry_session

logger = get_logger(__name__)


# ============================================
# 数据源常量
# ============================================

class DataSource:
    """数据源标识"""
    EASTMONEY = "eastmoney"
    TENCENT = "tencent"
    SINA = "sina"
    AKSHARE = "akshare"
    YFINANCE = "yfinance"


# 数据源优先级（数字越小优先级越高）
DATA_SOURCE_PRIORITY = {
    DataSource.EASTMONEY: 0,
    DataSource.TENCENT: 1,
    DataSource.SINA: 2,
    DataSource.AKSHARE: 3,
    DataSource.YFINANCE: 4,
}


# ============================================
# A股数据管理器
# ============================================

class AShareDataManager:
    """
    A股数据源管理器
    
    功能：
    1. 多数据源自动切换（按优先级）
    2. 熔断器保护
    3. 数据缓存
    4. 防封禁策略
    """
    
    # 东方财富 K 线周期映射
    EM_PERIOD_MAP = {
        '1m': '1',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1H': '60',
        '4H': '240',
        '1D': '101',
        '1W': '102',
    }
    
    def __init__(self):
        # 熔断器
        self._circuit_breaker = get_ashare_circuit_breaker()
        self._realtime_cb = get_realtime_circuit_breaker()
        
        # 缓存
        self._realtime_cache = get_realtime_cache()
        self._kline_cache = get_kline_cache()
        
        # 限流器
        self._em_limiter = get_eastmoney_limiter()
        self._tencent_limiter = get_tencent_limiter()
        self._akshare_limiter = get_akshare_limiter()
        
        # Akshare 可用性检查
        self._has_akshare = self._check_akshare()
    
    def _check_akshare(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare
            return True
        except ImportError:
            logger.debug("akshare 未安装，相关功能已禁用")
            return False
    
    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None,
        use_cache: bool = True
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        获取K线数据（自动切换数据源）
        
        Args:
            symbol: 股票代码
            timeframe: 时间周期
            limit: 数据条数
            before_time: 获取此时间之前的数据
            use_cache: 是否使用缓存
            
        Returns:
            (K线数据列表, 成功的数据源名称)
        """
        # 检查缓存
        if use_cache:
            cache_key = generate_kline_cache_key(symbol, timeframe, limit, before_time)
            cached = self._kline_cache.get(cache_key)
            if cached:
                logger.debug(f"[缓存命中] K线数据 {symbol}:{timeframe}")
                return cached, "cache"
        
        errors = []
        
        # 按优先级尝试各个数据源
        sources = [
            (DataSource.EASTMONEY, self._fetch_eastmoney_kline),
            (DataSource.TENCENT, self._fetch_tencent_kline),
            (DataSource.AKSHARE, self._fetch_akshare_kline),
            (DataSource.YFINANCE, self._fetch_yfinance_kline),
        ]
        
        for source_name, fetch_func in sources:
            # 检查熔断器
            if not self._circuit_breaker.is_available(source_name):
                logger.debug(f"[熔断] {source_name} 处于熔断状态，跳过")
                continue
            
            # 跳过不可用的 akshare
            if source_name == DataSource.AKSHARE and not self._has_akshare:
                continue
            
            try:
                logger.debug(f"[数据源] 尝试 {source_name} 获取 {symbol}")
                klines = fetch_func(symbol, timeframe, limit, before_time)
                
                if klines:
                    self._circuit_breaker.record_success(source_name)
                    
                    # 更新缓存
                    if use_cache:
                        cache_key = generate_kline_cache_key(symbol, timeframe, limit, before_time)
                        self._kline_cache.set(cache_key, klines)
                    
                    logger.info(f"[数据源] {source_name} 成功获取 {symbol} {len(klines)} 条数据")
                    return klines, source_name
                    
            except Exception as e:
                error_msg = f"{source_name}: {str(e)}"
                errors.append(error_msg)
                self._circuit_breaker.record_failure(source_name, str(e))
                logger.warning(f"[数据源] {error_msg}")
        
        # 所有数据源都失败
        logger.error(f"[数据源] 所有数据源获取 {symbol} 失败: {errors}")
        return [], ""
    
    def _fetch_eastmoney_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """使用东方财富获取K线数据"""
        klines = []
        
        period = self.EM_PERIOD_MAP.get(timeframe)
        if not period:
            raise ValueError(f"Eastmoney 不支持时间周期: {timeframe}")
        
        # 限流
        self._em_limiter.wait()
        
        # 确定市场代码
        if symbol.startswith('6'):
            secid = f"1.{symbol}"  # 上海
        else:
            secid = f"0.{symbol}"  # 深圳
        
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57',
            'klt': period,
            'fqt': '1',  # 前复权
            'end': '20500101',
            'lmt': limit,
        }
        
        headers = get_request_headers(referer='https://quote.eastmoney.com/')
        
        session = get_retry_session()
        response = session.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            raise ConnectionError(f"HTTP {response.status_code}")
        
        data = response.json()
        
        if data.get('data') and data['data'].get('klines'):
            for line in data['data']['klines']:
                try:
                    parts = line.split(',')
                    if len(parts) >= 6:
                        time_str = parts[0]
                        if ' ' in time_str:
                            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                        else:
                            dt = datetime.strptime(time_str, '%Y-%m-%d')
                        
                        klines.append({
                            'time': int(dt.timestamp()),
                            'open': round(float(parts[1]), 4),
                            'high': round(float(parts[3]), 4),
                            'low': round(float(parts[4]), 4),
                            'close': round(float(parts[2]), 4),
                            'volume': round(float(parts[5]), 2)
                        })
                except (ValueError, IndexError):
                    continue
        
        # 过滤和排序
        klines.sort(key=lambda x: x['time'])
        if before_time:
            klines = [k for k in klines if k['time'] < before_time]
        if len(klines) > limit:
            klines = klines[-limit:]
        
        return klines
    
    def _fetch_tencent_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """使用腾讯财经获取K线数据"""
        # 腾讯周期映射
        period_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1H': 60, '1D': 'day', '1W': 'week'
        }
        
        period = period_map.get(timeframe)
        if period is None:
            raise ValueError(f"腾讯财经不支持时间周期: {timeframe}")
        
        # 转换代码格式
        if symbol.startswith('6'):
            tencent_symbol = f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            tencent_symbol = f"sz{symbol}"
        else:
            tencent_symbol = f"bj{symbol}"
        
        # 限流
        self._tencent_limiter.wait()
        
        # 构建URL
        if isinstance(period, int):
            url = f"http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={tencent_symbol},m{period},,{limit}"
        else:
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_symbol},{period},,,{limit},qfq"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            raise ConnectionError(f"HTTP {response.status_code}")
        
        data = response.json()
        klines = []
        
        if data.get('code') == 0 and 'data' in data:
            stock_data = data['data'].get(tencent_symbol)
            if stock_data:
                if isinstance(period, int):
                    candles = stock_data.get(f'm{period}', [])
                else:
                    candles = stock_data.get('qfqday', stock_data.get('day', []))
                
                for candle in candles:
                    if len(candle) >= 5:
                        try:
                            time_str = str(candle[0])
                            if len(time_str) == 12:
                                dt = datetime.strptime(time_str, '%Y%m%d%H%M')
                            elif len(time_str) == 10:
                                dt = datetime.strptime(time_str, '%Y-%m-%d')
                            else:
                                continue
                            
                            klines.append({
                                'time': int(dt.timestamp()),
                                'open': round(float(candle[1]), 4),
                                'high': round(float(candle[3]), 4),
                                'low': round(float(candle[4]), 4),
                                'close': round(float(candle[2]), 4),
                                'volume': round(float(candle[5]), 2) if len(candle) > 5 else 0
                            })
                        except (ValueError, IndexError):
                            continue
        
        # 过滤和排序
        klines.sort(key=lambda x: x['time'])
        if before_time:
            klines = [k for k in klines if k['time'] < before_time]
        if len(klines) > limit:
            klines = klines[-limit:]
        
        return klines
    
    def _fetch_akshare_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """使用 Akshare 获取K线数据"""
        if not self._has_akshare:
            raise RuntimeError("akshare 未安装")
        
        import akshare as ak
        from datetime import timedelta
        
        # Akshare 只支持日线/周线
        period_map = {'1D': 'daily', '1W': 'weekly'}
        period = period_map.get(timeframe)
        if not period:
            raise ValueError(f"Akshare 不支持时间周期: {timeframe}")
        
        # 限流
        self._akshare_limiter.wait()
        
        # 计算日期范围
        if before_time:
            end_date = datetime.fromtimestamp(before_time).strftime('%Y%m%d')
        else:
            end_date = datetime.now().strftime('%Y%m%d')
        
        days = limit * 2 if timeframe == '1D' else limit * 10
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        klines = []
        if df is not None and not df.empty:
            df = df.tail(limit)
            for _, row in df.iterrows():
                ts = int(datetime.strptime(str(row['日期']), '%Y-%m-%d').timestamp())
                klines.append({
                    'time': ts,
                    'open': round(float(row['开盘']), 4),
                    'high': round(float(row['最高']), 4),
                    'low': round(float(row['最低']), 4),
                    'close': round(float(row['收盘']), 4),
                    'volume': round(float(row['成交量']), 2)
                })
        
        return klines
    
    def _fetch_yfinance_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """使用 yfinance 获取K线数据（兜底）"""
        import yfinance as yf
        
        # 转换为 Yahoo 格式
        if symbol.startswith('6'):
            yahoo_symbol = f"{symbol}.SS"
        elif symbol.startswith('0') or symbol.startswith('3'):
            yahoo_symbol = f"{symbol}.SZ"
        else:
            yahoo_symbol = f"{symbol}.SS"
        
        # 周期映射
        period_map = {
            '1D': ('1d', f'{limit}d'),
            '1W': ('1wk', f'{limit * 7}d'),
            '1H': ('1h', f'{limit}d'),
        }
        
        interval, period = period_map.get(timeframe, ('1d', f'{limit}d'))
        
        ticker = yf.Ticker(yahoo_symbol)
        df = ticker.history(period=period, interval=interval)
        
        klines = []
        if df is not None and not df.empty:
            df = df.tail(limit)
            for idx, row in df.iterrows():
                ts = int(idx.timestamp())
                klines.append({
                    'time': ts,
                    'open': round(float(row['Open']), 4),
                    'high': round(float(row['High']), 4),
                    'low': round(float(row['Low']), 4),
                    'close': round(float(row['Close']), 4),
                    'volume': round(float(row['Volume']), 2)
                })
        
        return klines
    
    def get_realtime_quote(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> Tuple[Dict[str, Any], str]:
        """
        获取实时报价（自动切换数据源）
        
        Args:
            symbol: 股票代码
            use_cache: 是否使用缓存
            
        Returns:
            (报价数据字典, 成功的数据源名称)
        """
        # 检查缓存
        if use_cache:
            cached = self._realtime_cache.get(f"quote:{symbol}")
            if cached:
                return cached, "cache"
        
        errors = []
        
        # 按优先级尝试各个数据源
        sources = [
            (DataSource.EASTMONEY, self._fetch_eastmoney_quote),
            (DataSource.TENCENT, self._fetch_tencent_quote),
            (DataSource.AKSHARE, self._fetch_akshare_quote),
        ]
        
        for source_name, fetch_func in sources:
            if not self._realtime_cb.is_available(source_name):
                continue
            
            if source_name == DataSource.AKSHARE and not self._has_akshare:
                continue
            
            try:
                quote = fetch_func(symbol)
                if quote and quote.get('last', 0) > 0:
                    self._realtime_cb.record_success(source_name)
                    
                    # 更新缓存
                    if use_cache:
                        self._realtime_cache.set(f"quote:{symbol}", quote, ttl=60.0)
                    
                    return quote, source_name
                    
            except Exception as e:
                errors.append(f"{source_name}: {str(e)}")
                self._realtime_cb.record_failure(source_name, str(e))
        
        logger.warning(f"[实时报价] 所有数据源获取 {symbol} 失败")
        return {'last': 0, 'symbol': symbol}, ""
    
    def _fetch_eastmoney_quote(self, symbol: str) -> Dict[str, Any]:
        """使用东方财富获取实时报价"""
        if symbol.startswith('6'):
            secid = f"1.{symbol}"
        else:
            secid = f"0.{symbol}"
        
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170',
        }
        
        self._em_limiter.wait()
        
        session = get_retry_session()
        response = session.get(url, params=params, headers=get_request_headers(), timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and data.get('data'):
                d = data['data']
                last_price = d.get('f43', 0)
                if last_price and last_price > 0:
                    divisor = 100 if last_price > 1000 else 1
                    return {
                        'last': last_price / divisor,
                        'high': d.get('f44', 0) / divisor,
                        'low': d.get('f45', 0) / divisor,
                        'open': d.get('f46', 0) / divisor,
                        'previousClose': d.get('f60', 0) / divisor,
                        'change': d.get('f169', 0) / divisor,
                        'changePercent': d.get('f170', 0) / 100
                    }
        
        return {}
    
    def _fetch_tencent_quote(self, symbol: str) -> Dict[str, Any]:
        """使用腾讯财经获取实时报价"""
        if symbol.startswith('6'):
            tencent_symbol = f"sh{symbol}"
        else:
            tencent_symbol = f"sz{symbol}"
        
        url = f"http://qt.gtimg.cn/q={tencent_symbol}"
        
        self._tencent_limiter.wait()
        
        response = requests.get(url, timeout=10)
        content = response.content.decode('gbk', errors='ignore')
        
        if '="' in content:
            data_str = content.split('="')[1].strip('";\n')
            if data_str:
                parts = data_str.split('~')
                if len(parts) > 32:
                    return {
                        'last': float(parts[3]) if parts[3] else 0,
                        'change': float(parts[31]) if parts[31] else 0,
                        'changePercent': float(parts[32]) if parts[32] else 0,
                        'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                        'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                        'open': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                        'previousClose': float(parts[4]) if parts[4] else 0
                    }
        
        return {}
    
    def _fetch_akshare_quote(self, symbol: str) -> Dict[str, Any]:
        """使用 Akshare 获取实时报价"""
        if not self._has_akshare:
            return {}
        
        import akshare as ak
        
        self._akshare_limiter.wait()
        
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            row = df[df['代码'] == symbol]
            if not row.empty:
                row = row.iloc[0]
                return {
                    'last': float(row.get('最新价', 0) or 0),
                    'change': float(row.get('涨跌额', 0) or 0),
                    'changePercent': float(row.get('涨跌幅', 0) or 0),
                    'high': float(row.get('最高', 0) or 0),
                    'low': float(row.get('最低', 0) or 0),
                    'open': float(row.get('今开', 0) or 0),
                    'previousClose': float(row.get('昨收', 0) or 0)
                }
        
        return {}
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据管理器状态"""
        return {
            'circuit_breaker': self._circuit_breaker.get_status(),
            'realtime_circuit_breaker': self._realtime_cb.get_status(),
            'realtime_cache_stats': self._realtime_cache.stats(),
            'kline_cache_stats': self._kline_cache.stats(),
            'has_akshare': self._has_akshare,
        }


# ============================================
# 全局实例
# ============================================

_ashare_data_manager: Optional[AShareDataManager] = None


def get_ashare_data_manager() -> AShareDataManager:
    """获取A股数据管理器单例"""
    global _ashare_data_manager
    if _ashare_data_manager is None:
        _ashare_data_manager = AShareDataManager()
    return _ashare_data_manager
