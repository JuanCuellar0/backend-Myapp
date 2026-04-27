from flask import Blueprint, jsonify, request

from models import db, User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


def _get_user_from_request():
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token.startswith("token-"):
        return None
    user_id = token.replace("token-", "", 1)
    return User.query.get(user_id)


@users_bp.route("/profile", methods=["GET"])
def get_profile():
    user = _get_user_from_request()
    if not user:
        return jsonify({"success": False, "mensaje": "Token inválido"}), 401
    return jsonify(user.to_public_dict()), 200


@users_bp.route("/profile", methods=["PUT"])
def update_profile():
    user = _get_user_from_request()
    if not user:
        return jsonify({"success": False, "mensaje": "Token inválido"}), 401

    data = request.get_json(silent=True) or {}
    nombre = data.get("nombre")
    if isinstance(nombre, str) and nombre.strip():
        user.nombre = nombre.strip()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al actualizar perfil"}), 500

    return jsonify(user.to_public_dict()), 200
