from flask import Blueprint, jsonify, request
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import db, User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


_ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "900"))


def _get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY") or ""
    if not secret:
        secret = "dev-secret-change-in-prod"
    return secret


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_get_secret_key(), salt="access")


def _get_user_from_request():
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None, "AUTH_REQUIRED"
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = _serializer().loads(token, max_age=_ACCESS_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        return None, "TOKEN_EXPIRED"
    except BadSignature:
        return None, "TOKEN_INVALID"

    if not isinstance(payload, dict) or payload.get("typ") != "access":
        return None, "TOKEN_INVALID"
    user_id = payload.get("sub")
    if not user_id:
        return None, "TOKEN_INVALID"
    return User.query.get(str(user_id)), None


@users_bp.route("/profile", methods=["GET"])
def get_profile():
    user, err = _get_user_from_request()
    if not user:
        status = 401
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), status
    return jsonify(user.to_public_dict()), 200


@users_bp.route("/profile", methods=["PUT"])
def update_profile():
    user, err = _get_user_from_request()
    if not user:
        status = 401
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), status

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
