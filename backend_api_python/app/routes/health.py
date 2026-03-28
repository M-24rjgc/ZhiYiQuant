from datetime import datetime

from flask import Blueprint, jsonify
from app.config.settings import Config

health_bp = Blueprint("health", __name__)


@health_bp.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "智弈量化桌面引擎",
        "version": Config.VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    })


@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@health_bp.route("/api/health", methods=["GET"])
def api_health_check():
    return health_check()
