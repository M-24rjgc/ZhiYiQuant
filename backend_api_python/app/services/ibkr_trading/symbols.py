"""
Symbol Mapping and Conversion

Converts ZhiYiQuant system symbols to IB contract format.
"""

from typing import Tuple, Optional


def normalize_symbol(symbol: str, market_type: str) -> Tuple[str, str, str]:
    """
    Convert system symbol to IB contract parameters.
    
    Args:
        symbol: Symbol code in the system
        market_type: Market type (USStock, HShare)
        
    Returns:
        (ib_symbol, exchange, currency)
    """
    symbol = (symbol or "").strip().upper()
    market_type = (market_type or "").strip()
    
    if market_type == "USStock":
        # US stocks: AAPL, TSLA, GOOGL
        # Use SMART routing for best execution
        return symbol, "SMART", "USD"
    
    elif market_type == "HShare":
        # Hong Kong stock formats:
        # - 0700.HK -> 700
        # - 00700 -> 700
        # - 700 -> 700
        ib_symbol = symbol
        
        # Remove .HK suffix
        if ib_symbol.endswith(".HK"):
            ib_symbol = ib_symbol[:-3]
        
        # Remove leading zeros
        ib_symbol = ib_symbol.lstrip("0") or "0"
        
        return ib_symbol, "SEHK", "HKD"
    
    else:
        # Default to US stock
        return symbol, "SMART", "USD"


def parse_symbol(symbol: str) -> Tuple[str, Optional[str]]:
    """
    Parse symbol and auto-detect market type.
    
    Args:
        symbol: Symbol code
        
    Returns:
        (clean_symbol, market_type)
    """
    symbol = (symbol or "").strip().upper()
    
    # HK stock: ends with .HK or all digits
    if symbol.endswith(".HK"):
        return symbol, "HShare"
    
    # All digits (likely HK stock code)
    clean = symbol.lstrip("0")
    if clean.isdigit() and len(clean) <= 5:
        return symbol, "HShare"
    
    # Default to US stock
    return symbol, "USStock"


def format_display_symbol(ib_symbol: str, exchange: str) -> str:
    """
    Convert IB contract format back to display format.
    
    Args:
        ib_symbol: IB symbol
        exchange: Exchange code
        
    Returns:
        Display symbol
    """
    if exchange == "SEHK":
        # HK stock: pad to 4 digits, add .HK
        padded = ib_symbol.zfill(4)
        return f"{padded}.HK"
    return ib_symbol
