"""
Crypto market data source.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import ccxt
import requests

from app.data_sources.base import BaseDataSource, TIMEFRAME_SECONDS
from app.utils.logger import get_logger
from app.config import CCXTConfig

logger = get_logger(__name__)


class CryptoDataSource(BaseDataSource):
    """Crypto market data source backed by CCXT with Binance REST fallback."""

    name = "Crypto/CCXT"
    TIMEFRAME_MAP = CCXTConfig.TIMEFRAME_MAP

    def __init__(self):
        config = {
            "timeout": CCXTConfig.TIMEOUT,
            "enableRateLimit": CCXTConfig.ENABLE_RATE_LIMIT,
        }
        if CCXTConfig.PROXY:
            config["proxies"] = {
                "http": CCXTConfig.PROXY,
                "https": CCXTConfig.PROXY,
            }

        exchange_id = CCXTConfig.DEFAULT_EXCHANGE
        if not hasattr(ccxt, exchange_id):
            logger.warning(f"CCXT exchange '{exchange_id}' not found, falling back to 'coinbase'")
            exchange_id = "coinbase"

        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(config)

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        sym = self._normalize_pair(symbol)
        if self.exchange_id == "binance":
            fallback = self._fetch_binance_rest_ticker(sym)
            if fallback:
                return fallback
        try:
            return self.exchange.fetch_ticker(sym)
        except Exception as exc:
            logger.warning(f"CCXT ticker failed for {sym}: {exc}; trying direct Binance REST fallback")
            fallback = self._fetch_binance_rest_ticker(sym)
            if fallback:
                return fallback
            raise

    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        klines = []
        try:
            ccxt_timeframe = self.TIMEFRAME_MAP.get(timeframe, "1d")
            symbol_pair = self._normalize_pair(symbol)

            ohlcv = self._fetch_ohlcv(symbol_pair, ccxt_timeframe, limit, before_time, timeframe)
            if not ohlcv:
                logger.warning(f"CCXT returned no K-lines: {symbol_pair}")
                return []

            for candle in ohlcv:
                if len(candle) < 6:
                    continue
                klines.append(
                    self.format_kline(
                        timestamp=int(candle[0] / 1000),
                        open_price=candle[1],
                        high=candle[2],
                        low=candle[3],
                        close=candle[4],
                        volume=candle[5],
                    )
                )

            klines = self.filter_and_limit(klines, limit, before_time)
            self.log_result(symbol, klines, timeframe)
        except Exception as exc:
            logger.error(f"Failed to fetch crypto K-lines {symbol}: {exc}")
        return klines

    def _normalize_pair(self, symbol: str) -> str:
        sym = (symbol or "").strip().upper()
        if ":" in sym:
            sym = sym.split(":", 1)[0]
        if "/" not in sym:
            if sym.endswith("USDT") and len(sym) > 4:
                sym = f"{sym[:-4]}/USDT"
            elif sym.endswith("USD") and len(sym) > 3:
                sym = f"{sym[:-3]}/USD"
            else:
                sym = f"{sym}/USDT"
        return sym

    def _fetch_ohlcv(
        self,
        symbol_pair: str,
        ccxt_timeframe: str,
        limit: int,
        before_time: Optional[int],
        timeframe: str,
    ) -> List:
        try:
            if before_time:
                total_seconds = self.calculate_time_range(timeframe, limit)
                end_time = datetime.fromtimestamp(before_time)
                start_time = end_time - timedelta(seconds=total_seconds)
                since = int(start_time.timestamp() * 1000)
                end_ms = before_time * 1000

                all_ohlcv = []
                batch_limit = 300
                current_since = since

                while current_since < end_ms:
                    batch = self.exchange.fetch_ohlcv(
                        symbol_pair,
                        ccxt_timeframe,
                        since=current_since,
                        limit=batch_limit,
                    )
                    if not batch:
                        break

                    all_ohlcv.extend(batch)
                    last_timestamp = batch[-1][0]
                    if last_timestamp >= end_ms:
                        break

                    timeframe_ms = TIMEFRAME_SECONDS.get(timeframe, 86400) * 1000
                    current_since = last_timestamp + timeframe_ms

                return all_ohlcv

            return self.exchange.fetch_ohlcv(symbol_pair, ccxt_timeframe, limit=limit)
        except Exception as exc:
            logger.warning(f"CCXT fetch_ohlcv failed: {exc}; trying fallback")
            return self._fetch_ohlcv_fallback(symbol_pair, ccxt_timeframe, limit, before_time, timeframe)

    def _fetch_ohlcv_fallback(
        self,
        symbol_pair: str,
        ccxt_timeframe: str,
        limit: int,
        before_time: Optional[int],
        timeframe: str,
    ) -> List:
        try:
            total_seconds = self.calculate_time_range(timeframe, limit)
            if before_time:
                end_time = datetime.fromtimestamp(before_time)
                start_time = end_time - timedelta(seconds=total_seconds)
                since = int(start_time.timestamp() * 1000)
            else:
                since = int((datetime.now() - timedelta(seconds=total_seconds)).timestamp() * 1000)

            return self.exchange.fetch_ohlcv(symbol_pair, ccxt_timeframe, since=since, limit=limit)
        except Exception as exc:
            logger.error(f"CCXT fallback method also failed: {exc}")
            return self._fetch_binance_rest_ohlcv(symbol_pair, ccxt_timeframe, limit, before_time)

    def _to_binance_symbol(self, symbol_pair: str) -> str:
        return self._normalize_pair(symbol_pair).replace("/", "")

    def _fetch_binance_rest_ticker(self, symbol_pair: str) -> Optional[Dict[str, Any]]:
        try:
            symbol = self._to_binance_symbol(symbol_pair)
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": symbol},
                timeout=max(10, int(CCXTConfig.TIMEOUT / 1000)),
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "symbol": symbol_pair,
                "last": float(payload.get("lastPrice") or 0),
                "change": float(payload.get("priceChange") or 0),
                "changePercent": float(payload.get("priceChangePercent") or 0),
                "high": float(payload.get("highPrice") or 0),
                "low": float(payload.get("lowPrice") or 0),
                "open": float(payload.get("openPrice") or 0),
                "previousClose": float(payload.get("prevClosePrice") or 0),
            }
        except Exception as exc:
            logger.error(f"Direct Binance ticker fallback failed for {symbol_pair}: {exc}")
            return None

    def _fetch_binance_rest_ohlcv(
        self,
        symbol_pair: str,
        ccxt_timeframe: str,
        limit: int,
        before_time: Optional[int],
    ) -> List:
        try:
            symbol = self._to_binance_symbol(symbol_pair)
            params: Dict[str, Any] = {
                "symbol": symbol,
                "interval": ccxt_timeframe,
                "limit": max(1, min(int(limit or 100), 1000)),
            }
            if before_time:
                params["endTime"] = int(before_time) * 1000

            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params=params,
                timeout=max(10, int(CCXTConfig.TIMEOUT / 1000)),
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error(f"Direct Binance OHLCV fallback failed for {symbol_pair}: {exc}")
            return []
