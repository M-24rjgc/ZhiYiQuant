"""
Exchange credentials vault (local-only).

Local deployment notes:
- No encryption/decryption is used.
- Credentials are stored as plaintext JSON in DB (encrypted_config column kept for compatibility).
"""

import time
import traceback
import json
from flask import Blueprint, request, jsonify, g

from app.utils.db import get_db_connection
from app.utils.logger import get_logger
from app.utils.auth import login_required

logger = get_logger(__name__)

credentials_bp = Blueprint('credentials', __name__)


def _api_key_hint(api_key: str) -> str:
    if not api_key:
        return ''
    s = str(api_key)
    if len(s) <= 8:
        return s[:2] + '***'
    return f"{s[:4]}...{s[-4:]}"


@credentials_bp.route('/list', methods=['GET'])
@login_required
def list_credentials():
    """List all credentials for the current user."""
    try:
        user_id = g.user_id

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, name, exchange_id, api_key_hint, created_at, updated_at
                FROM qd_exchange_credentials
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,)
            )
            rows = cur.fetchall() or []
            cur.close()

        return jsonify({'code': 1, 'msg': 'success', 'data': {'items': rows}})
    except Exception as e:
        logger.error(f"list_credentials failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': {'items': []}}), 500


@credentials_bp.route('/create', methods=['POST'])
@login_required
def create_credential():
    """Create a new credential for the current user."""
    try:
        user_id = g.user_id
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        exchange_id = (data.get('exchange_id') or '').strip()
        api_key = (data.get('api_key') or '').strip()
        secret_key = (data.get('secret_key') or '').strip()
        passphrase = (data.get('passphrase') or '').strip()

        if not exchange_id:
            return jsonify({'code': 0, 'msg': 'Missing exchange_id', 'data': None}), 400
        if not api_key or not secret_key:
            return jsonify({'code': 0, 'msg': 'Missing api_key/secret_key', 'data': None}), 400

        plaintext_config = json.dumps({
            'exchange_id': exchange_id,
            'api_key': api_key,
            'secret_key': secret_key,
            'passphrase': passphrase
        }, ensure_ascii=False)

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO qd_exchange_credentials (user_id, name, exchange_id, api_key_hint, encrypted_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, NOW(), NOW())
                """,
                (user_id, name, exchange_id, _api_key_hint(api_key), plaintext_config)
            )
            new_id = cur.lastrowid
            db.commit()
            cur.close()

        return jsonify({'code': 1, 'msg': 'success', 'data': {'id': new_id}})
    except Exception as e:
        logger.error(f"create_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@credentials_bp.route('/delete', methods=['DELETE'])
@login_required
def delete_credential():
    """Delete a credential for the current user."""
    try:
        user_id = g.user_id
        cred_id = request.args.get('id', type=int)
        if not cred_id:
            return jsonify({'code': 0, 'msg': 'Missing id', 'data': None}), 400

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "DELETE FROM qd_exchange_credentials WHERE id = ? AND user_id = ?",
                (cred_id, user_id)
            )
            db.commit()
            cur.close()

        return jsonify({'code': 1, 'msg': 'success', 'data': None})
    except Exception as e:
        logger.error(f"delete_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@credentials_bp.route('/get', methods=['GET'])
@login_required
def get_credential():
    """
    Return decrypted credential for form auto-fill.
    """
    try:
        user_id = g.user_id
        cred_id = request.args.get('id', type=int)
        if not cred_id:
            return jsonify({'code': 0, 'msg': 'Missing id', 'data': None}), 400

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, name, exchange_id, encrypted_config, api_key_hint, created_at, updated_at
                FROM qd_exchange_credentials
                WHERE id = ? AND user_id = ?
                """,
                (cred_id, user_id)
            )
            row = cur.fetchone()
            cur.close()

        if not row:
            return jsonify({'code': 0, 'msg': 'Not found', 'data': None}), 404

        decrypted = {}
        raw = row.get('encrypted_config') or ''
        if isinstance(raw, str) and raw.strip():
            try:
                decrypted = json.loads(raw)
            except Exception:
                decrypted = {}
        # Ensure exchange_id is present
        decrypted['exchange_id'] = row.get('exchange_id') or decrypted.get('exchange_id')

        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'id': row.get('id'),
                'name': row.get('name'),
                'exchange_id': row.get('exchange_id'),
                'api_key_hint': row.get('api_key_hint'),
                'config': decrypted
            }
        })
    except Exception as e:
        logger.error(f"get_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


