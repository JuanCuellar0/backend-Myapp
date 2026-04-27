from flask import Blueprint, jsonify, request

from models import User

contacts_bp = Blueprint("contacts", __name__, url_prefix="/api/contacts")


@contacts_bp.route("", methods=["GET"])
@contacts_bp.route("/", methods=["GET"])
def list_contacts():
    users = User.query.order_by(User.nombre.asc()).all()
    return jsonify([u.to_public_dict() for u in users]), 200


@contacts_bp.route("/search", methods=["GET"])
def search_contacts():
    term = (request.args.get("term") or "").strip().lower()
    if not term:
        users = User.query.order_by(User.nombre.asc()).all()
        return jsonify([u.to_public_dict() for u in users]), 200

    users = (
        User.query.filter((User.nombre.ilike(f"%{term}%")) | (User.email.ilike(f"%{term}%")))
        .order_by(User.nombre.asc())
        .all()
    )
    return jsonify([u.to_public_dict() for u in users]), 200


@contacts_bp.route("/<user_id>", methods=["GET"])
def get_contact(user_id: str):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "mensaje": "Contacto no encontrado"}), 404
    return jsonify(user.to_public_dict()), 200
