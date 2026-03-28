"""
Analysis memory storage for desktop fast analysis.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from app.utils.db import get_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _safe_json_parse(value: Any, default=None):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def _to_iso(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class AnalysisMemory:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS zhiyiquant_analysis_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    market VARCHAR(50) NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    decision VARCHAR(10) NOT NULL,
                    confidence INTEGER DEFAULT 50,
                    price_at_analysis DECIMAL(24, 8),
                    entry_price DECIMAL(24, 8),
                    stop_loss DECIMAL(24, 8),
                    take_profit DECIMAL(24, 8),
                    summary TEXT,
                    reasons TEXT,
                    risks TEXT,
                    scores TEXT,
                    indicators_snapshot TEXT,
                    raw_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated_at TIMESTAMP,
                    actual_outcome VARCHAR(20),
                    actual_return_pct DECIMAL(10, 4),
                    was_correct BOOLEAN,
                    user_feedback VARCHAR(20),
                    feedback_at TIMESTAMP
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_memory_symbol ON zhiyiquant_analysis_memory(market, symbol)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_memory_created ON zhiyiquant_analysis_memory(created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_memory_user ON zhiyiquant_analysis_memory(user_id)")
            db.commit()
            cur.close()

    def store(self, analysis_result: dict[str, Any], user_id: int | None = None) -> int | None:
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    INSERT INTO zhiyiquant_analysis_memory (
                        user_id, market, symbol, decision, confidence,
                        price_at_analysis, entry_price, stop_loss, take_profit,
                        summary, reasons, risks, scores, indicators_snapshot, raw_result
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        analysis_result.get("market"),
                        analysis_result.get("symbol"),
                        analysis_result.get("decision"),
                        analysis_result.get("confidence", 50),
                        (analysis_result.get("market_data") or {}).get("current_price"),
                        (analysis_result.get("trading_plan") or {}).get("entry_price"),
                        (analysis_result.get("trading_plan") or {}).get("stop_loss"),
                        (analysis_result.get("trading_plan") or {}).get("take_profit"),
                        analysis_result.get("summary"),
                        json.dumps(analysis_result.get("reasons", []), ensure_ascii=False),
                        json.dumps(analysis_result.get("risks", []), ensure_ascii=False),
                        json.dumps(analysis_result.get("scores", {}), ensure_ascii=False),
                        json.dumps(analysis_result.get("indicators", {}), ensure_ascii=False),
                        json.dumps(analysis_result, ensure_ascii=False),
                    ),
                )
                db.commit()
                memory_id = cur.lastrowid
                cur.close()
                return memory_id
        except Exception as exc:
            logger.warning(f"Failed to store analysis memory: {exc}")
            return None

    def get_recent(self, market: str, symbol: str, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        try:
            since = (datetime.utcnow() - timedelta(days=max(days, 1))).strftime("%Y-%m-%d %H:%M:%S")
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    SELECT *
                    FROM zhiyiquant_analysis_memory
                    WHERE market = ? AND symbol = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (market, symbol, since, limit),
                )
                rows = cur.fetchall() or []
                cur.close()
                return [self._normalize_row(row) for row in rows]
        except Exception as exc:
            logger.warning(f"Failed to load recent history: {exc}")
            return []

    def get_all_history(self, user_id: int | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                if user_id is None:
                    cur.execute("SELECT COUNT(*) AS total FROM zhiyiquant_analysis_memory")
                    total = (cur.fetchone() or {}).get("total", 0)
                    cur.execute(
                        "SELECT * FROM zhiyiquant_analysis_memory ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        (page_size, offset),
                    )
                else:
                    cur.execute("SELECT COUNT(*) AS total FROM zhiyiquant_analysis_memory WHERE user_id = ?", (user_id,))
                    total = (cur.fetchone() or {}).get("total", 0)
                    cur.execute(
                        "SELECT * FROM zhiyiquant_analysis_memory WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        (user_id, page_size, offset),
                    )
                rows = cur.fetchall() or []
                cur.close()
                return {
                    "items": [self._normalize_row(row) for row in rows],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
        except Exception as exc:
            logger.warning(f"Failed to load analysis history: {exc}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def delete_history(self, memory_id: int, user_id: int | None = None) -> bool:
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                if user_id is None:
                    cur.execute("DELETE FROM zhiyiquant_analysis_memory WHERE id = ?", (memory_id,))
                else:
                    cur.execute("DELETE FROM zhiyiquant_analysis_memory WHERE id = ? AND user_id = ?", (memory_id, user_id))
                db.commit()
                deleted = cur.rowcount > 0
                cur.close()
                return deleted
        except Exception as exc:
            logger.warning(f"Failed to delete analysis history: {exc}")
            return False

    def record_feedback(self, memory_id: int, feedback: str) -> bool:
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    UPDATE zhiyiquant_analysis_memory
                    SET user_feedback = ?, feedback_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (feedback, memory_id),
                )
                db.commit()
                changed = cur.rowcount > 0
                cur.close()
                return changed
        except Exception as exc:
            logger.warning(f"Failed to record feedback: {exc}")
            return False

    def get_similar_patterns(self, market: str, symbol: str, indicators: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    SELECT *
                    FROM zhiyiquant_analysis_memory
                    WHERE market = ? AND symbol = ?
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (market, symbol),
                )
                rows = [self._normalize_row(row) for row in (cur.fetchall() or [])]
                cur.close()
        except Exception as exc:
            logger.warning(f"Failed to load similar patterns: {exc}")
            return []

        current_rsi = (((indicators or {}).get("rsi") or {}).get("value")) or 0
        current_signal = (((indicators or {}).get("macd") or {}).get("signal")) or ""
        current_trend = (((indicators or {}).get("moving_averages") or {}).get("trend")) or ""

        scored = []
        for row in rows:
            snap = row.get("indicators_snapshot") or {}
            rsi_value = (((snap or {}).get("rsi") or {}).get("value")) or 0
            macd_signal = (((snap or {}).get("macd") or {}).get("signal")) or ""
            ma_trend = (((snap or {}).get("moving_averages") or {}).get("trend")) or ""

            score = 0
            score += max(0, 50 - min(abs(float(current_rsi) - float(rsi_value)), 50))
            score += 25 if current_signal == macd_signal else 0
            score += 25 if current_trend == ma_trend else 0

            row["similarity_score"] = round(score, 2)
            scored.append(row)

        scored.sort(key=lambda item: item.get("similarity_score", 0), reverse=True)
        return scored[:limit]

    def get_performance_stats(self, market: str | None = None, symbol: str | None = None, days: int = 30) -> dict[str, Any]:
        try:
            with get_db_connection() as db:
                cur = db.cursor()
                clauses = ["validated_at IS NOT NULL"]
                params: list[Any] = []
                if market:
                    clauses.append("market = ?")
                    params.append(market)
                if symbol:
                    clauses.append("symbol = ?")
                    params.append(symbol)
                since = (datetime.utcnow() - timedelta(days=max(days, 1))).strftime("%Y-%m-%d %H:%M:%S")
                clauses.append("created_at >= ?")
                params.append(since)

                where_sql = " AND ".join(clauses)
                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) AS correct,
                        AVG(actual_return_pct) AS avg_return,
                        SUM(CASE WHEN decision = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
                        SUM(CASE WHEN decision = 'SELL' THEN 1 ELSE 0 END) AS sell_count,
                        SUM(CASE WHEN decision = 'HOLD' THEN 1 ELSE 0 END) AS hold_count,
                        SUM(CASE WHEN user_feedback = 'helpful' THEN 1 ELSE 0 END) AS helpful_count,
                        SUM(CASE WHEN user_feedback IS NOT NULL THEN 1 ELSE 0 END) AS feedback_count
                    FROM zhiyiquant_analysis_memory
                    WHERE {where_sql}
                    """,
                    tuple(params),
                )
                row = cur.fetchone() or {}
                cur.close()
        except Exception as exc:
            logger.warning(f"Failed to load performance stats: {exc}")
            return {"total_analyses": 0, "accuracy_pct": 0, "error": str(exc)}

        total = row.get("total") or 0
        correct = row.get("correct") or 0
        feedback_total = row.get("feedback_count") or 0
        helpful = row.get("helpful_count") or 0
        return {
            "total_analyses": total,
            "accuracy_pct": round((correct / total * 100) if total else 0, 2),
            "avg_return_pct": round(float(row.get("avg_return") or 0), 2),
            "decision_distribution": {
                "buy": row.get("buy_count") or 0,
                "sell": row.get("sell_count") or 0,
                "hold": row.get("hold_count") or 0,
            },
            "user_satisfaction_pct": round((helpful / feedback_total * 100) if feedback_total else 0, 2),
            "period_days": days,
        }

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        normalized["created_at"] = _to_iso(normalized.get("created_at"))
        normalized["validated_at"] = _to_iso(normalized.get("validated_at"))
        normalized["feedback_at"] = _to_iso(normalized.get("feedback_at"))
        normalized["reasons"] = _safe_json_parse(normalized.get("reasons"), [])
        normalized["risks"] = _safe_json_parse(normalized.get("risks"), [])
        normalized["scores"] = _safe_json_parse(normalized.get("scores"), {})
        normalized["indicators_snapshot"] = _safe_json_parse(normalized.get("indicators_snapshot"), {})
        normalized["raw_result"] = _safe_json_parse(normalized.get("raw_result"), {})
        return normalized


_memory_instance: AnalysisMemory | None = None


def get_analysis_memory() -> AnalysisMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AnalysisMemory()
    return _memory_instance


