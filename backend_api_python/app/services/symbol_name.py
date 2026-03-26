"""
Symbol/company name resolver for local-only mode.

Goal:
- When a symbol is not present in our seed list, try to resolve a human-readable name
  from public data sources, then persist it into watchlist records.

Notes:
- For A shares we prefer akshare when available (requested).
- For H shares we use Tencent quote API (no key required).
- For US stocks we use Finnhub (if configured) or yfinance.
- For Crypto/Forex/Futures we provide best-effort fallbacks.
"""

from __future__ import annotations

from typing import Optional

import re
import os

import requests

from app.utils.logger import get_logger
from app.data.market_symbols_seed import get_symbol_name as seed_get_symbol_name

logger = get_logger(__name__)

try:
    import akshare as ak  # type: ignore
    HAS_AKSHARE = True
except Exception:
    ak = None
    HAS_AKSHARE = False


def _normalize_symbol_for_market(market: str, symbol: str) -> str:
    m = (market or '').strip()
    s = (symbol or '').strip().upper()
    if not m or not s:
        return s

    if m == 'AShare' and s.isdigit():
        return s.zfill(6)
    if m == 'HShare' and s.isdigit():
        return s.zfill(5)

    return s


def _tencent_quote_code(market: str, symbol: str) -> Optional[str]:
    """
    Convert symbol to Tencent quote code, e.g.
    - AShare: sh600000 / sz000001 / bj430047
    - HShare: hk00700
    """
    m = (market or '').strip()
    s = _normalize_symbol_for_market(m, symbol)
    if not s:
        return None

    if m == 'AShare':
        if s.startswith('6'):
            return f"sh{s}"
        if s.startswith('0') or s.startswith('3'):
            return f"sz{s}"
        if s.startswith('4') or s.startswith('8'):
            return f"bj{s}"
        return None

    if m == 'HShare':
        if s.isdigit():
            return f"hk{s}"
        # allow already prefixed
        if s.startswith('HK') and s[2:].isdigit():
            return f"hk{s[2:]}"
        if s.startswith('HK') and len(s) > 2:
            return f"hk{s[2:]}"
        return f"hk{s}"

    return None


def _resolve_name_from_tencent(market: str, symbol: str) -> Optional[str]:
    """
    Tencent quote endpoint: http://qt.gtimg.cn/q=sz000858
    Returns:
      v_sz000858="51~五 粮 液~000858~...";  -> name is the 2nd field split by '~'
    """
    code = _tencent_quote_code(market, symbol)
    if not code:
        return None

    try:
        url = f"http://qt.gtimg.cn/q={code}"
        resp = requests.get(url, timeout=5)
        # Tencent often responds in GBK for Chinese names
        resp.encoding = 'gbk'
        text = resp.text or ''

        # Extract quoted payload
        m = re.search(r'="([^"]*)"', text)
        payload = m.group(1) if m else ''
        if not payload:
            return None

        parts = payload.split('~')
        if len(parts) < 2:
            return None

        name = (parts[1] or '').strip().replace(' ', '')
        return name if name else None
    except Exception as e:
        logger.debug(f"Tencent name resolve failed: {market} {symbol}: {e}")
        return None


def _resolve_name_from_akshare_ashare(symbol: str) -> Optional[str]:
    """
    Resolve A-share name via akshare (no API key required).
    """
    if not HAS_AKSHARE or ak is None:
        return None
    try:
        # Prefer per-symbol endpoint (avoids fetching the whole market list).
        if hasattr(ak, "stock_individual_info_em"):
            df = ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty and 'item' in df.columns and 'value' in df.columns:
                info = {str(r['item']).strip(): r['value'] for _, r in df.iterrows()}
                name = str(info.get('股票简称') or info.get('证券简称') or '').strip()
                return name if name else None

        # Fallback: spot list (may be slow / large)
        if hasattr(ak, "stock_zh_a_spot_em"):
            df2 = ak.stock_zh_a_spot_em()
            if df2 is not None and not df2.empty:
                row = df2[df2['代码'] == symbol].iloc[0]
                name = str(row.get('名称') or '').strip()
                return name if name else None
    except Exception as e:
        logger.debug(f"akshare name resolve failed (AShare {symbol}): {e}")
        return None
    return None

def _resolve_name_from_yfinance(symbol: str) -> Optional[str]:
    """
    Best-effort company name via yfinance.
    """
    def _try_one(sym: str) -> Optional[str]:
        import yfinance as yf
        t = yf.Ticker(sym)
        info = getattr(t, "info", None)
        if not isinstance(info, dict) or not info:
            return None
        name = (info.get('longName') or info.get('shortName') or '').strip()
        return name if name else None
    try:
        # yfinance uses '-' for some tickers (e.g. BRK-B) while users may input 'BRK.B'
        out = _try_one(symbol)
        if out:
            return out
        if '.' in symbol:
            out = _try_one(symbol.replace('.', '-'))
            if out:
                return out
        return None
    except Exception as e:
        logger.debug(f"yfinance name resolve failed: {symbol}: {e}")
        return None


def _resolve_name_from_finnhub(symbol: str) -> Optional[str]:
    """
    Finnhub company profile (requires FINNHUB_API_KEY).
    https://finnhub.io/docs/api/company-profile2
    """
    try:
        api_key = (os.getenv('FINNHUB_API_KEY') or '').strip()
        if not api_key:
            return None
        url = "https://finnhub.io/api/v1/stock/profile2"
        resp = requests.get(url, params={"symbol": symbol, "token": api_key}, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json() if resp.text else {}
        if not isinstance(data, dict) or not data:
            return None
        name = (data.get("name") or data.get("ticker") or '').strip()
        return name if name else None
    except Exception as e:
        logger.debug(f"Finnhub name resolve failed: {symbol}: {e}")
        return None


def resolve_symbol_name(market: str, symbol: str) -> Optional[str]:
    """
    Resolve a display name for a symbol.
    Priority:
    1) Seed mapping (fast, offline)
    2) Market-specific public sources
    3) Reasonable fallback (None)
    """
    m = (market or '').strip()
    s = _normalize_symbol_for_market(m, symbol)
    if not m or not s:
        return None

    # 1) Seed
    seed = seed_get_symbol_name(m, s)
    if seed:
        return seed

    # 2) Market-specific
    if m == 'AShare':
        # Requested: use akshare for A shares, do not depend on Tencent by default.
        return _resolve_name_from_akshare_ashare(s)

    if m == 'HShare':
        return _resolve_name_from_tencent(m, s)

    if m == 'USStock':
        # Prefer Finnhub if configured (more stable for company name),
        # otherwise fall back to yfinance.
        return _resolve_name_from_finnhub(s) or _resolve_name_from_yfinance(s)

    # Crypto: at least return base ticker-like display (not a "company", but better than empty)
    if m == 'Crypto':
        if '/' in s:
            base = s.split('/')[0].strip()
            return base if base else None
        return s

    # Forex: keep as-is (e.g. EURUSD) – you can later replace with a nicer mapping if needed.
    if m == 'Forex':
        return s

    # Futures: keep as-is
    if m == 'Futures':
        return s

    return None


