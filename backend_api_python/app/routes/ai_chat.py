"""
AI chat API routes (optional).
Provides a lightweight local placeholder until a dedicated desktop chat flow is added.
"""

from flask import Blueprint, request, jsonify

from app.utils.logger import get_logger

logger = get_logger(__name__)

ai_chat_bp = Blueprint('ai_chat', __name__)


@ai_chat_bp.route('/chat/message', methods=['POST'])
def chat_message():
    """Minimal local chat placeholder."""
    data = request.get_json() or {}
    msg = (data.get('message') or '').strip()
    if not msg:
        return jsonify({'code': 0, 'msg': 'Missing message', 'data': None}), 400
    return jsonify({
        'code': 1,
        'msg': 'success',
        'data': {
            'reply': 'Chat API is not implemented yet in local-only mode.',
            'echo': msg
        }
    })


@ai_chat_bp.route('/chat/history', methods=['GET'])
def get_chat_history():
    """Return empty history for the local placeholder flow."""
    return jsonify({'code': 1, 'msg': 'success', 'data': []})


@ai_chat_bp.route('/chat/history/save', methods=['POST'])
def save_chat_history():
    """No-op save for the local placeholder flow."""
    return jsonify({'code': 1, 'msg': 'success', 'data': None})


