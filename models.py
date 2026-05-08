"""
Modelos de base de datos
Extraído de app.py para mejor organización
"""
import json
from datetime import datetime, timezone
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utc_now_iso() -> str:
    """Obtener timestamp actual en UTC ISO format"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    nombre = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(32), nullable=False, default="user")
    permisos_json = db.Column(db.Text, nullable=False, default="[]")
    fecha_registro = db.Column(db.String(40), nullable=False, default=_utc_now_iso)

    def to_public_dict(self):
        """Serializar usuario sin datos sensibles"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "email": self.email,
            "rol": self.rol,
            "permisos": json.loads(self.permisos_json or "[]"),
            "fechaRegistro": self.fecha_registro,
        }


class Survey(db.Model):
    __tablename__ = "surveys"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    fecha_creacion = db.Column(db.String(40), nullable=False, default=_utc_now_iso)
    estado = db.Column(db.String(16), nullable=False, default="activa")
    creado_por = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    questions = db.relationship("SurveyQuestion", backref="survey", cascade="all, delete-orphan")

    def to_dict(self, include_questions: bool = True):
        payload = {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "fechaCreacion": self.fecha_creacion,
            "estado": self.estado,
        }
        if include_questions:
            payload["preguntas"] = [q.to_dict() for q in sorted(self.questions, key=lambda x: x.orden)]
        return payload


class SurveyQuestion(db.Model):
    __tablename__ = "survey_questions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    survey_id = db.Column(db.String(36), db.ForeignKey("surveys.id"), nullable=False, index=True)
    orden = db.Column(db.Integer, nullable=False, default=0)
    pregunta = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(16), nullable=False)
    opciones_json = db.Column(db.Text, nullable=True)
    requerida = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("survey_id", "orden", name="uq_survey_question_order"),
    )

    def to_dict(self):
        payload = {
            "id": self.id,
            "pregunta": self.pregunta,
            "tipo": self.tipo,
            "requerida": bool(self.requerida),
        }
        if self.opciones_json:
            payload["opciones"] = json.loads(self.opciones_json)
        return payload


class SurveyResponse(db.Model):
    __tablename__ = "survey_responses"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    encuesta_id = db.Column(db.String(36), db.ForeignKey("surveys.id"), nullable=False, index=True)
    usuario_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    respuestas_json = db.Column(db.Text, nullable=False, default="{}")
    fecha_respuesta = db.Column(db.String(40), nullable=False, default=_utc_now_iso)

    def to_dict(self):
        return {
            "id": self.id,
            "encuestaId": self.encuesta_id,
            "usuarioId": self.usuario_id,
            "respuestas": json.loads(self.respuestas_json or "{}"),
            "fechaRespuesta": self.fecha_respuesta,
        }


class RiskReport(db.Model):
    __tablename__ = "risk_reports"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.String(300), nullable=False)
    nivel = db.Column(db.String(16), nullable=False)
    recomendaciones_json = db.Column(db.Text, nullable=False, default="[]")
    fecha_analisis = db.Column(db.String(40), nullable=False, default=_utc_now_iso)

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "nivel": self.nivel,
            "recomendaciones": json.loads(self.recomendaciones_json or "[]"),
            "fechaAnalisis": self.fecha_analisis,
        }
