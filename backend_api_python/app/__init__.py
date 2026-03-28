"""
智弈量化 desktop application factory.
"""
from __future__ import annotations

import traceback

from flask import Flask
from flask_cors import CORS

from app.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)
_trading_executor = None
_pending_order_worker = None


def get_trading_executor():
    global _trading_executor
    if _trading_executor is None:
        from app.services.trading_executor import TradingExecutor

        _trading_executor = TradingExecutor()
    return _trading_executor


def get_pending_order_worker():
    global _pending_order_worker
    if _pending_order_worker is None:
        from app.services.pending_order_worker import PendingOrderWorker

        _pending_order_worker = PendingOrderWorker()
    return _pending_order_worker


def start_portfolio_monitor():
    import os

    if os.getenv("ENABLE_PORTFOLIO_MONITOR", "true").lower() != "true":
        return
    if os.getenv("PYTHON_API_DEBUG", "false").lower() == "true" and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    try:
        from app.services.portfolio_monitor import start_monitor_service

        start_monitor_service()
    except Exception as exc:
        logger.error(f"Failed to start portfolio monitor: {exc}")


def start_pending_order_worker():
    import os

    if os.getenv("ENABLE_PENDING_ORDER_WORKER", "true").lower() != "true":
        return
    try:
        get_pending_order_worker().start()
    except Exception as exc:
        logger.error(f"Failed to start pending order worker: {exc}")


def restore_running_strategies():
    import os

    if os.getenv("DISABLE_RESTORE_RUNNING_STRATEGIES", "false").lower() == "true":
        return

    try:
        from app.services.strategy import StrategyService

        strategy_service = StrategyService()
        trading_executor = get_trading_executor()
        running = strategy_service.get_running_strategies_with_type()
        for strategy_info in running or []:
            strategy_id = strategy_info["id"]
            strategy_type = strategy_info.get("strategy_type", "")
            if strategy_type and strategy_type != "IndicatorStrategy":
                continue
            try:
                trading_executor.start_strategy(strategy_id)
            except Exception as exc:
                logger.error(f"Error restoring strategy {strategy_id}: {exc}")
                logger.error(traceback.format_exc())
    except Exception as exc:
        logger.error(f"Failed to restore running strategies: {exc}")
        logger.error(traceback.format_exc())


def create_app(config_name: str = "default"):
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    CORS(app)
    setup_logger()

    try:
        from app.services.user_service import get_user_service
        from app.utils.db import get_db_type, init_database

        logger.info(f"Database type: {get_db_type()}")
        init_database()
        get_user_service().ensure_owner_exists()
    except Exception as exc:
        logger.warning(f"Database initialization note: {exc}")

    from app.routes import register_routes

    register_routes(app)

    with app.app_context():
        start_pending_order_worker()
        start_portfolio_monitor()
        restore_running_strategies()

    return app
