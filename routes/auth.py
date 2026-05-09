from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
import re
import hashlib
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import RefreshToken, db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "900"))
_REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 30)))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY") or ""
    if not secret:
        secret = "dev-secret-change-in-prod"
    return secret


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_get_secret_key(), salt=salt)


def _hash_token(token: str) -> str:
    digest = hashlib.sha256()
    digest.update(_get_secret_key().encode("utf-8"))
    digest.update(token.encode("utf-8"))
    return digest.hexdigest()


def _is_admin_registration(email: str, admin_code: str | None) -> bool:
    allowlist = os.getenv("ADMIN_EMAILS") or os.getenv("ADMIN_EMAIL_WHITELIST") or ""
    if allowlist.strip():
        emails = {e.strip().lower() for e in allowlist.split(",") if e.strip()}
        if email.strip().lower() in emails:
            return True

    expected_code = (os.getenv("ADMIN_REGISTRATION_CODE") or "").strip()
    if expected_code and admin_code and str(admin_code).strip() == expected_code:
        return True

    return False


def _issue_tokens(user: User):
    access_jti = uuid4().hex
    refresh_jti = uuid4().hex

    access_token = _serializer("access").dumps({"typ": "access", "sub": user.id, "jti": access_jti})
    refresh_token = _serializer("refresh").dumps({"typ": "refresh", "sub": user.id, "jti": refresh_jti})

    refresh_expires_at = _utc_now() + timedelta(seconds=_REFRESH_TOKEN_TTL_SECONDS)
    db.session.add(
        RefreshToken(
            user_id=user.id,
            jti=refresh_jti,
            token_hash=_hash_token(refresh_token),
            revoked=False,
            fecha_expiracion=refresh_expires_at.replace(microsecond=0).isoformat(),
        )
    )
    db.session.commit()

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresIn": _ACCESS_TOKEN_TTL_SECONDS,
        "tokenType": "Bearer",
    }


def _decode_access_token(token: str):
    try:
        payload = _serializer("access").loads(token, max_age=_ACCESS_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        return None, "TOKEN_EXPIRED"
    except BadSignature:
        return None, "TOKEN_INVALID"

    if not isinstance(payload, dict) or payload.get("typ") != "access":
        return None, "TOKEN_INVALID"
    user_id = payload.get("sub")
    if not user_id:
        return None, "TOKEN_INVALID"
    return str(user_id), None


def _decode_refresh_token(token: str):
    try:
        payload = _serializer("refresh").loads(token, max_age=_REFRESH_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        return None, "REFRESH_EXPIRED"
    except BadSignature:
        return None, "REFRESH_INVALID"

    if not isinstance(payload, dict) or payload.get("typ") != "refresh":
        return None, "REFRESH_INVALID"
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        return None, "REFRESH_INVALID"
    return {"user_id": str(user_id), "jti": str(jti)}, None


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    contraseña = data.get("contraseña")

    if not email or not contraseña:
        return jsonify({"success": False, "mensaje": "Email y contraseña son requeridos"}), 400

    usuario = User.query.filter_by(email=email).first()
    if not usuario or not check_password_hash(usuario.password_hash, contraseña):
        return jsonify({"success": False, "mensaje": "Email o contraseña incorrectos"}), 401

    tokens = _issue_tokens(usuario)
    return (
        jsonify(
            {
                "success": True,
                "mensaje": "Sesión iniciada correctamente",
                "usuario": usuario.to_public_dict(),
                "token": tokens["accessToken"],
                "accessToken": tokens["accessToken"],
                "refreshToken": tokens["refreshToken"],
                "expiresIn": tokens["expiresIn"],
                "tokenType": tokens["tokenType"],
            }
        ),
        200,
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    email = (data.get("email") or "").strip().lower()
    contraseña = data.get("contraseña")
    admin_code = data.get("adminCode") or data.get("admin_code")

    if not nombre or not email or not contraseña:
        return jsonify({"success": False, "mensaje": "Nombre, email y contraseña son requeridos"}), 400

    if len(nombre) < 2:
        return jsonify({"success": False, "mensaje": "Nombre inválido"}), 400

    if not _EMAIL_RE.match(email):
        return jsonify({"success": False, "mensaje": "Email inválido"}), 400

    if not isinstance(contraseña, str) or len(contraseña) < 6:
        return jsonify({"success": False, "mensaje": "La contraseña debe tener mínimo 6 caracteres"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "mensaje": "El email ya está registrado"}), 409

    rol = "admin" if _is_admin_registration(email=email, admin_code=admin_code) else "user"
    nuevo_usuario = User(nombre=nombre, email=email, password_hash=generate_password_hash(contraseña), rol=rol)

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al registrar usuario"}), 500

    tokens = _issue_tokens(nuevo_usuario)
    return (
        jsonify(
            {
                "success": True,
                "mensaje": "Usuario registrado correctamente",
                "usuario": nuevo_usuario.to_public_dict(),
                "token": tokens["accessToken"],
                "accessToken": tokens["accessToken"],
                "refreshToken": tokens["refreshToken"],
                "expiresIn": tokens["expiresIn"],
                "tokenType": tokens["tokenType"],
            }
        ),
        201,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refreshToken") or data.get("refresh_token")

    if refresh_token:
        decoded, err = _decode_refresh_token(str(refresh_token))
        if not err and decoded:
            record = RefreshToken.query.filter_by(jti=decoded["jti"], user_id=decoded["user_id"]).first()
            if record:
                record.revoked = True
                db.session.commit()

    auth_header = request.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        access = auth_header.split(" ", 1)[1].strip()
        user_id, err = _decode_access_token(access)
        if not err and user_id:
            RefreshToken.query.filter_by(user_id=user_id, revoked=False).update({"revoked": True})
            db.session.commit()

    return jsonify({"success": True, "mensaje": "Sesión cerrada correctamente"}), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refreshToken") or data.get("refresh_token")
    if not refresh_token:
        return jsonify({"success": False, "mensaje": "refreshToken es requerido", "code": "REFRESH_REQUIRED"}), 400

    decoded, err = _decode_refresh_token(str(refresh_token))
    if err or not decoded:
        return jsonify({"success": False, "mensaje": "Refresh token inválido", "code": err or "REFRESH_INVALID"}), 401

    record = RefreshToken.query.filter_by(jti=decoded["jti"], user_id=decoded["user_id"]).first()
    if not record or record.revoked:
        return jsonify({"success": False, "mensaje": "Refresh token revocado", "code": "REFRESH_REVOKED"}), 401

    if record.token_hash != _hash_token(str(refresh_token)):
        record.revoked = True
        db.session.commit()
        return jsonify({"success": False, "mensaje": "Refresh token inválido", "code": "REFRESH_INVALID"}), 401

    user = User.query.get(decoded["user_id"])
    if not user:
        record.revoked = True
        db.session.commit()
        return jsonify({"success": False, "mensaje": "Usuario no encontrado", "code": "USER_NOT_FOUND"}), 404

    record.revoked = True
    db.session.commit()

    tokens = _issue_tokens(user)
    return (
        jsonify(
            {
                "success": True,
                "mensaje": "Token refrescado",
                "token": tokens["accessToken"],
                "accessToken": tokens["accessToken"],
                "refreshToken": tokens["refreshToken"],
                "expiresIn": tokens["expiresIn"],
                "tokenType": tokens["tokenType"],
            }
        ),
        200,
    )


@auth_bp.route("/recover-password", methods=["POST"])
def recover_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "mensaje": "Email es requerido"}), 400

    return jsonify({"success": True, "mensaje": "Si el email existe, se enviará un correo de recuperación"}), 200
