from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
import re

from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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

    return (
        jsonify(
            {
                "success": True,
                "mensaje": "Sesión iniciada correctamente",
                "usuario": usuario.to_public_dict(),
                "token": f"token-{usuario.id}",
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

    nuevo_usuario = User(
        nombre=nombre,
        email=email,
        password_hash=generate_password_hash(contraseña),
        rol="user",
    )

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al registrar usuario"}), 500

    return (
        jsonify(
            {
                "success": True,
                "mensaje": "Usuario registrado correctamente",
                "usuario": nuevo_usuario.to_public_dict(),
                "token": f"token-{nuevo_usuario.id}",
            }
        ),
        201,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"success": True, "mensaje": "Sesión cerrada correctamente"}), 200


@auth_bp.route("/recover-password", methods=["POST"])
def recover_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"success": False, "mensaje": "Email es requerido"}), 400

    return jsonify({"success": True, "mensaje": "Si el email existe, se enviará un correo de recuperación"}), 200
