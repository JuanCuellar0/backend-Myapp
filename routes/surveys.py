import json
import os

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import Survey, SurveyQuestion, SurveyResponse, User, db

surveys_bp = Blueprint("surveys", __name__, url_prefix="/api/surveys")

_ALLOWED_QUESTION_TYPES = {"texto", "seleccion", "numerica", "si_no"}
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


def _ensure_default_user() -> User:
    user = User.query.first()
    if user:
        return user

    user = User(
        nombre="Usuario Demo",
        email="demo@example.com",
        password_hash=generate_password_hash("demo-demo"),
        rol="user",
        permisos_json="[]",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _normalize_questions(preguntas):
    if not isinstance(preguntas, list):
        return None

    normalized = []
    for idx, q in enumerate(preguntas):
        if not isinstance(q, dict):
            return None
        pregunta = (q.get("pregunta") or "").strip()
        tipo = (q.get("tipo") or "").strip()
        requerida = bool(q.get("requerida", True))
        opciones = q.get("opciones")

        if not pregunta or tipo not in _ALLOWED_QUESTION_TYPES:
            return None

        if tipo == "seleccion":
            if not isinstance(opciones, list) or len(opciones) < 2:
                return None
            opciones = [str(o).strip() for o in opciones if str(o).strip()]
            if len(opciones) < 2:
                return None
        else:
            opciones = None

        normalized.append(
            {
                "orden": idx,
                "pregunta": pregunta,
                "tipo": tipo,
                "requerida": requerida,
                "opciones_json": json.dumps(opciones) if opciones is not None else None,
            }
        )

    if len(normalized) == 0:
        return None
    return normalized


def _maybe_seed_surveys():
    auto_seed = (os.getenv("AUTO_SEED_SURVEYS") or "").strip().lower() in {"1", "true", "yes", "on"}
    is_dev = os.getenv("FLASK_ENV", "development").lower() == "development"
    if not (auto_seed or is_dev):
        return

    if Survey.query.count() > 0:
        return

    demo_user = _ensure_default_user()

    encuestas = [
        {
            "titulo": "Instrumento de caracterización de estudiantes",
            "descripcion": "Formulario dividido por secciones para caracterizar al estudiante y variables de contexto.",
            "preguntas": [
                {"pregunta": "Datos personales::Tipo de documento", "tipo": "seleccion", "opciones": ["Cédula de ciudadanía", "Tarjeta de identidad", "Cédula de extranjería", "Pasaporte"], "requerida": True},
                {"pregunta": "Datos personales::Número de documento", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Fecha de expedición (AAAA-MM-DD)", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Lugar de expedición", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Primer nombre", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Segundo nombre", "tipo": "texto", "requerida": False},
                {"pregunta": "Datos personales::Primer apellido", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Segundo apellido", "tipo": "texto", "requerida": False},
                {"pregunta": "Datos personales::Estado civil", "tipo": "seleccion", "opciones": ["Soltero(a)", "Unión libre", "Casado(a)", "Separado(a)", "Viudo(a)"], "requerida": True},
                {"pregunta": "Datos personales::País", "tipo": "seleccion", "opciones": ["Colombia", "Otro"], "requerida": True},
                {"pregunta": "Datos personales::Departamento", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Ciudad/Municipio", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Barrio/Vereda", "tipo": "texto", "requerida": False},
                {"pregunta": "Datos personales::Dirección de residencia", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Teléfono de contacto", "tipo": "texto", "requerida": True},
                {"pregunta": "Datos personales::Correo electrónico", "tipo": "texto", "requerida": True},
                {"pregunta": "Información socioeconómica::Estrato socioeconómico", "tipo": "seleccion", "opciones": ["1", "2", "3", "4", "5", "6"], "requerida": True},
                {"pregunta": "Información socioeconómica::Acceso a internet y dispositivos para estudiar", "tipo": "seleccion", "opciones": ["Internet estable y computador propio", "Solo celular", "Internet compartido", "Sin acceso estable"], "requerida": True},
                {"pregunta": "Información socioeconómica::Grupo Sisbén (si aplica)", "tipo": "seleccion", "opciones": ["A", "B", "C", "D", "No aplica"], "requerida": True},
                {"pregunta": "Caracterización del aspirante::Tipo sanguíneo", "tipo": "seleccion", "opciones": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "No sabe"], "requerida": True},
                {"pregunta": "Caracterización del aspirante::EPS (si aplica)", "tipo": "texto", "requerida": False},
                {"pregunta": "Caracterización del aspirante::¿Tiene discapacidad?", "tipo": "si_no", "requerida": True},
                {"pregunta": "Caracterización del aspirante::Tipo de discapacidad (si aplica)", "tipo": "texto", "requerida": False},
                {"pregunta": "Caracterización del aspirante::Pertenencia a grupo/vulnerabilidad", "tipo": "seleccion", "opciones": ["Ninguna", "Víctima del conflicto", "Población rural", "Madre/Padre cabeza de hogar", "Comunidad indígena", "Comunidad negra/afrodescendiente", "LGBTIQ+", "Otra"], "requerida": True},
                {"pregunta": "Caracterización del aspirante::Orientación sexual", "tipo": "seleccion", "opciones": ["Heterosexual", "Homosexual", "Bisexual", "Pansexual", "Asexual", "Prefiere no decir"], "requerida": True},
                {"pregunta": "Caracterización del aspirante::Edad", "tipo": "numerica", "requerida": True},
                {"pregunta": "Caracterización del aspirante::Género", "tipo": "seleccion", "opciones": ["Femenino", "Masculino", "No binario", "Prefiere no decir"], "requerida": True},
            ],
        },
        {
            "titulo": "Evaluación de Riesgos Ocupacionales",
            "descripcion": "Encuesta para identificar riesgos en el ambiente laboral",
            "preguntas": [
                {"pregunta": "¿Ha sufrido algún accidente en el trabajo?", "tipo": "si_no", "requerida": True},
                {
                    "pregunta": "¿Cuál es su nivel de satisfacción laboral?",
                    "tipo": "seleccion",
                    "opciones": ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"],
                    "requerida": True,
                },
                {
                    "pregunta": "Describa los riesgos identificados en su área:",
                    "tipo": "texto",
                    "requerida": False,
                },
            ],
        },
        {
            "titulo": "Satisfacción del Servicio",
            "descripcion": "Evaluación de la calidad del servicio prestado",
            "preguntas": [{"pregunta": "¿Qué tan satisfecho está con el servicio?", "tipo": "numerica", "requerida": True}],
        },
    ]

    for encuesta in encuestas:
        survey = Survey(
            titulo=encuesta["titulo"],
            descripcion=encuesta["descripcion"],
            estado="activa",
            creado_por=demo_user.id,
        )
        db.session.add(survey)
        db.session.flush()
        for idx, q in enumerate(encuesta["preguntas"]):
            question = SurveyQuestion(
                survey_id=survey.id,
                orden=idx,
                pregunta=q["pregunta"],
                tipo=q["tipo"],
                requerida=bool(q.get("requerida", True)),
                opciones_json=json.dumps(q.get("opciones")) if q.get("opciones") is not None else None,
            )
            db.session.add(question)

    db.session.commit()


@surveys_bp.route("", methods=["GET"])
@surveys_bp.route("/", methods=["GET"])
def list_surveys():
    _maybe_seed_surveys()
    surveys = Survey.query.order_by(Survey.fecha_creacion.desc()).all()
    return jsonify([s.to_dict(include_questions=True) for s in surveys]), 200


@surveys_bp.route("", methods=["POST"])
@surveys_bp.route("/", methods=["POST"])
def create_survey():
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), 401

    data = request.get_json(silent=True) or {}
    titulo = data.get("titulo")
    descripcion = data.get("descripcion")
    preguntas = data.get("preguntas")

    titulo = (titulo or "").strip()
    descripcion = (descripcion or "").strip()
    normalized_questions = _normalize_questions(preguntas)

    if not titulo or not descripcion or normalized_questions is None:
        return jsonify({"success": False, "mensaje": "Datos inválidos"}), 400

    survey = Survey(titulo=titulo, descripcion=descripcion, estado=data.get("estado") or "activa", creado_por=user.id)
    db.session.add(survey)
    db.session.flush()

    for q in normalized_questions:
        question = SurveyQuestion(
            survey_id=survey.id,
            orden=q["orden"],
            pregunta=q["pregunta"],
            tipo=q["tipo"],
            requerida=bool(q["requerida"]),
            opciones_json=q["opciones_json"],
        )
        db.session.add(question)

    db.session.commit()
    return jsonify(survey.to_dict(include_questions=True)), 201


@surveys_bp.route("/<survey_id>", methods=["GET"])
def get_survey(survey_id: str):
    survey = Survey.query.get(survey_id)
    if not survey:
        return jsonify({"success": False, "mensaje": "Encuesta no encontrada"}), 404
    return jsonify(survey.to_dict(include_questions=True)), 200


@surveys_bp.route("/<survey_id>", methods=["PUT"])
def update_survey(survey_id: str):
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), 401

    survey = Survey.query.get(survey_id)
    if not survey:
        return jsonify({"success": False, "mensaje": "Encuesta no encontrada"}), 404

    data = request.get_json(silent=True) or {}
    titulo = data.get("titulo")
    descripcion = data.get("descripcion")
    estado = data.get("estado")
    preguntas = data.get("preguntas")

    if titulo is not None:
        titulo = str(titulo).strip()
        if not titulo:
            return jsonify({"success": False, "mensaje": "Título inválido"}), 400
        survey.titulo = titulo

    if descripcion is not None:
        descripcion = str(descripcion).strip()
        if not descripcion:
            return jsonify({"success": False, "mensaje": "Descripción inválida"}), 400
        survey.descripcion = descripcion

    if estado is not None:
        estado = str(estado).strip()
        if estado not in {"activa", "inactiva", "cerrada"}:
            return jsonify({"success": False, "mensaje": "Estado inválido"}), 400
        survey.estado = estado

    if preguntas is not None:
        normalized_questions = _normalize_questions(preguntas)
        if normalized_questions is None:
            return jsonify({"success": False, "mensaje": "Preguntas inválidas"}), 400

        SurveyQuestion.query.filter_by(survey_id=survey.id).delete(synchronize_session=False)
        db.session.flush()
        for q in normalized_questions:
            db.session.add(
                SurveyQuestion(
                    survey_id=survey.id,
                    orden=q["orden"],
                    pregunta=q["pregunta"],
                    tipo=q["tipo"],
                    requerida=bool(q["requerida"]),
                    opciones_json=q["opciones_json"],
                )
            )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al actualizar encuesta"}), 500

    return jsonify(survey.to_dict(include_questions=True)), 200


@surveys_bp.route("/<survey_id>", methods=["DELETE"])
def delete_survey(survey_id: str):
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), 401

    survey = Survey.query.get(survey_id)
    if not survey:
        return jsonify({"success": False, "mensaje": "Encuesta no encontrada"}), 404

    try:
        SurveyResponse.query.filter_by(encuesta_id=survey.id).delete(synchronize_session=False)
        SurveyQuestion.query.filter_by(survey_id=survey.id).delete(synchronize_session=False)
        db.session.delete(survey)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al eliminar encuesta"}), 500

    return jsonify({"success": True, "mensaje": "Encuesta eliminada"}), 200


@surveys_bp.route("/<survey_id>/response", methods=["POST"])
def submit_response(survey_id: str):
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), 401

    survey = Survey.query.get(survey_id)
    if not survey:
        return jsonify({"success": False, "mensaje": "Encuesta no encontrada"}), 404

    data = request.get_json(silent=True) or {}
    respuestas = data.get("respuestas")
    if not isinstance(respuestas, dict):
        return jsonify({"success": False, "mensaje": "Respuestas inválidas"}), 400

    response = SurveyResponse(
        encuesta_id=survey.id,
        usuario_id=user.id,
        respuestas_json=json.dumps(respuestas),
    )
    db.session.add(response)
    db.session.commit()
    return jsonify(response.to_dict()), 201


@surveys_bp.route("/<survey_id>/responses", methods=["GET"])
def list_responses(survey_id: str):
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return jsonify({"success": False, "mensaje": msg, "code": err}), 401

    survey = Survey.query.get(survey_id)
    if not survey:
        return jsonify({"success": False, "mensaje": "Encuesta no encontrada"}), 404

    responses = SurveyResponse.query.filter_by(encuesta_id=survey.id).order_by(SurveyResponse.fecha_respuesta.desc()).all()
    return jsonify([r.to_dict() for r in responses]), 200
