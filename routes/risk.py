import os
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import Survey, SurveyQuestion, SurveyResponse, User

risk_bp = Blueprint("risk", __name__, url_prefix="/risk")

_ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "900"))


def _get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY") or ""
    if not secret:
        secret = "dev-secret-change-in-prod"
    return secret


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_get_secret_key(), salt="access")


def _get_user_from_request() -> Tuple[Optional[User], Optional[str]]:
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


def _question_by_id(survey: Survey) -> Dict[str, SurveyQuestion]:
    mapping: Dict[str, SurveyQuestion] = {}
    for q in survey.questions:
        mapping[str(q.id)] = q
    return mapping


def _normalize_answer(value: Any, question: Optional[SurveyQuestion]) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, bool):
        return 1.0 if value else 0.0

    if isinstance(value, (int, float)):
        v = float(value)
        if v < 0:
            v = 0.0
        if v > 10:
            v = 10.0
        return v / 10.0

    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return None
        try:
            v = float(s)
            if v < 0:
                v = 0.0
            if v > 10:
                v = 10.0
            return v / 10.0
        except Exception:
            pass

        if question and question.tipo == "seleccion" and question.opciones_json:
            try:
                import json as _json

                opciones = _json.loads(question.opciones_json) or []
                if isinstance(opciones, list) and len(opciones) > 1:
                    try:
                        idx = [str(o) for o in opciones].index(s)
                        return idx / (len(opciones) - 1)
                    except Exception:
                        return None
            except Exception:
                return None

    return None


def _compute_risk_level(score_0_to_1: float) -> str:
    if score_0_to_1 < 0.25:
        return "bajo"
    if score_0_to_1 < 0.5:
        return "medio"
    if score_0_to_1 < 0.75:
        return "alto"
    return "critico"


def _recommendations(level: str) -> List[str]:
    if level == "bajo":
        return ["Mantener seguimiento preventivo", "Reforzar hábitos de estudio y bienestar"]
    if level == "medio":
        return ["Realizar acompañamiento académico", "Revisar factores personales y carga de estudio"]
    if level == "alto":
        return ["Activar plan de intervención", "Acompañamiento psicosocial y académico prioritario"]
    return ["Atención inmediata", "Ruta de acompañamiento integral y seguimiento cercano"]


def _response_to_report(survey: Survey, response: SurveyResponse) -> Dict[str, Any]:
    qmap = _question_by_id(survey)
    answers: Dict[str, Any] = response.to_dict().get("respuestas") or {}

    values: List[float] = []
    for qid, ans in answers.items():
        q = qmap.get(str(qid))
        if q and q.tipo == "texto":
            continue
        v = _normalize_answer(ans, q)
        if v is not None:
            values.append(v)

    score = sum(values) / len(values) if values else 0.0
    level = _compute_risk_level(score)
    return {
        "id": response.id,
        "titulo": f"Reporte: {survey.titulo}",
        "descripcion": f"Análisis derivado de respuestas reales (score={score:.2f})",
        "nivel": level,
        "recomendaciones": _recommendations(level),
        "fechaAnalisis": response.fecha_respuesta,
    }


def _auth_or_401():
    user, err = _get_user_from_request()
    if not user:
        msg = "Autorización requerida" if err == "AUTH_REQUIRED" else "Token inválido"
        if err == "TOKEN_EXPIRED":
            msg = "Token expirado"
        return None, (jsonify({"success": False, "mensaje": msg, "code": err}), 401)
    return user, None


@risk_bp.route("/reports", methods=["GET"])
def reports():
    _, unauthorized = _auth_or_401()
    if unauthorized:
        return unauthorized

    filtro = (request.args.get("filtro") or "").strip().lower()
    surveys = Survey.query.order_by(Survey.fecha_creacion.desc()).all()

    all_reports: List[Dict[str, Any]] = []
    for survey in surveys:
        responses = (
            SurveyResponse.query.filter_by(encuesta_id=survey.id)
            .order_by(SurveyResponse.fecha_respuesta.desc())
            .all()
        )
        for resp in responses:
            all_reports.append(_response_to_report(survey, resp))

    if filtro in {"bajo", "medio", "alto", "critico"}:
        all_reports = [r for r in all_reports if r.get("nivel") == filtro]

    all_reports.sort(key=lambda r: r.get("fechaAnalisis") or "", reverse=True)
    return jsonify(all_reports), 200


@risk_bp.route("/analysis", methods=["GET"])
def analysis():
    return reports()

