"""
Backend API para Edu-Retention
Separado del frontend para mejor escalabilidad
"""
import os
import json
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from config import get_config
from models import Notification, RiskReport, User, db
from routes import decode_token, get_bearer_token

# Cargar variables de entorno
load_dotenv()


def create_app():
    """Application factory con configuración por entorno"""
    app = Flask(__name__)
    
    # Cargar configuración según FLASK_ENV
    config = get_config()
    app.config.from_object(config)
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Configurar CORS de forma segura
    cors_origins = [o.strip() for o in app.config['CORS_ORIGINS'] if o.strip()]
    CORS(
        app,
        origins=cors_origins,
        allow_headers=['Content-Type', 'Authorization'],
        supports_credentials=True,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    )
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    # Registrar blueprints
    register_routes(app)
    
    # Health check
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'healthy',
            'environment': os.getenv('FLASK_ENV', 'development')
        })

    @app.route("/", methods=["GET"])
    def index():
        return (
            jsonify(
                {
                    "service": "Edu-Retention Backend",
                    "status": "ok",
                    "endpoints": {
                        "health": "/health",
                        "auth": {
                            "register": "/api/auth/register",
                            "login": "/api/auth/login",
                            "logout": "/api/auth/logout",
                            "recover_password": "/api/auth/recover-password",
                        },
                        "users": {"profile_get": "/api/users/profile", "profile_put": "/api/users/profile"},
                        "surveys": "/api/surveys",
                        "contacts": "/api/contacts",
                    },
                }
            ),
            200,
        )

    def _require_access_payload():
        auth_header = request.headers.get("Authorization") or ""
        token = get_bearer_token(auth_header)
        if not token:
            return None
        return decode_token(token, expected_type="access")

    def _maybe_seed_risk_reports():
        if RiskReport.query.count() > 0:
            return
        reports = [
            RiskReport(
                titulo="Estudiantes en riesgo nivel medio",
                descripcion="Total estudiantes = 3",
                nivel="medio",
                recomendaciones_json=json.dumps(
                    [
                        "Implementar programa de capacitación",
                        "Mejorar acceso a recursos académicos",
                        "Realizar seguimiento socioeconómico",
                    ]
                ),
            ),
            RiskReport(
                titulo="Estudiantes en riesgo nivel bajo",
                descripcion="Total estudiantes = 4",
                nivel="bajo",
                recomendaciones_json=json.dumps(
                    [
                        "Mantener acompañamiento preventivo",
                        "Reforzar comunicación con bienestar",
                    ]
                ),
            ),
            RiskReport(
                titulo="Estudiantes en riesgo nivel alto",
                descripcion="Total estudiantes = 1",
                nivel="alto",
                recomendaciones_json=json.dumps(
                    [
                        "Activar plan de acompañamiento académico",
                        "Ofrecer apoyo financiero/transporte",
                    ]
                ),
            ),
            RiskReport(
                titulo="Estudiantes en riesgo nivel crítico",
                descripcion="Total estudiantes = 1",
                nivel="critico",
                recomendaciones_json=json.dumps(
                    [
                        "Implementar apoyo psicológico prioritario",
                        "Realizar seguimiento personalizado",
                        "Coordinar red de apoyo familiar",
                    ]
                ),
            ),
        ]
        db.session.add_all(reports)
        db.session.commit()

    @app.route("/risk/reports", methods=["GET"])
    def risk_reports():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        _maybe_seed_risk_reports()
        filtro = (request.args.get("filtro") or "").strip().lower()
        query = RiskReport.query
        if filtro:
            query = query.filter(RiskReport.nivel == filtro)
        reports = query.order_by(RiskReport.fecha_analisis.desc()).all()
        return jsonify([r.to_dict() for r in reports]), 200

    @app.route("/risk/analysis", methods=["GET"])
    def risk_analysis():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        _maybe_seed_risk_reports()
        reports = RiskReport.query.order_by(RiskReport.fecha_analisis.desc()).all()
        return jsonify([r.to_dict() for r in reports]), 200

    def _maybe_seed_notifications(user_id: str):
        existing = Notification.query.filter_by(usuario_id=user_id).count()
        if existing > 0:
            return
        notifs = [
            Notification(
                usuario_id=user_id,
                titulo="Nueva encuesta disponible",
                mensaje="Se ha publicado una nueva encuesta para completar.",
                tipo="info",
                leida=False,
            ),
            Notification(
                usuario_id=user_id,
                titulo="Reporte generado",
                mensaje="Tu reporte de análisis está listo para revisión.",
                tipo="exito",
                leida=True,
            ),
        ]
        db.session.add_all(notifs)
        db.session.commit()

    @app.route("/notifications", methods=["GET"])
    def list_notifications():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        user_id = str(payload.get("sub") or "").strip()
        if not user_id:
            return jsonify({"success": False, "mensaje": "Token inválido"}), 401
        _maybe_seed_notifications(user_id)
        notifs = (
            Notification.query.filter((Notification.usuario_id == user_id) | (Notification.usuario_id.is_(None)))
            .order_by(Notification.fecha_creacion.desc())
            .all()
        )
        return jsonify([n.to_dict() for n in notifs]), 200

    @app.route("/notifications/<notification_id>/read", methods=["POST"])
    def mark_notification_read(notification_id: str):
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        user_id = str(payload.get("sub") or "").strip()
        notif = Notification.query.get(notification_id)
        if not notif:
            return jsonify({"success": False, "mensaje": "Notificación no encontrada"}), 404
        if notif.usuario_id is not None and notif.usuario_id != user_id:
            return jsonify({"success": False, "mensaje": "No autorizado"}), 403
        notif.leida = True
        db.session.commit()
        return jsonify({"success": True, "mensaje": "Notificación marcada como leída"}), 200

    _PERMISSIONS = [
        {"id": "1", "nombre": "responder_encuestas", "descripcion": "Puede responder encuestas"},
        {"id": "2", "nombre": "ver_resultados", "descripcion": "Puede ver resultados de encuestas"},
        {"id": "3", "nombre": "crear_encuestas", "descripcion": "Puede crear nuevas encuestas"},
        {"id": "4", "nombre": "ver_reportes", "descripcion": "Puede ver reportes de análisis"},
        {"id": "5", "nombre": "gestionar_usuarios", "descripcion": "Puede gestionar usuarios"},
    ]

    def _require_admin(payload: dict):
        rol = str(payload.get("rol") or "").strip().lower()
        return rol == "admin"

    @app.route("/permissions", methods=["GET"])
    def list_permissions():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        return jsonify(_PERMISSIONS), 200

    @app.route("/permissions/assign", methods=["POST"])
    def assign_permission():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        if not _require_admin(payload):
            return jsonify({"success": False, "mensaje": "No autorizado"}), 403
        body = request.get_json(silent=True) or {}
        user_id = str(body.get("usuarioId") or body.get("usuario_id") or "").strip()
        permiso_id = str(body.get("permisoId") or body.get("permiso_id") or "").strip()
        permiso_nombre = str(body.get("permisoNombre") or body.get("permiso") or "").strip()
        if not user_id or (not permiso_id and not permiso_nombre):
            return jsonify({"success": False, "mensaje": "Datos inválidos"}), 400
        permission = None
        if permiso_id:
            permission = next((p for p in _PERMISSIONS if p["id"] == permiso_id), None)
        if not permission and permiso_nombre:
            permission = next((p for p in _PERMISSIONS if p["nombre"] == permiso_nombre), None)
        if not permission:
            return jsonify({"success": False, "mensaje": "Permiso no encontrado"}), 404
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "mensaje": "Usuario no encontrado"}), 404
        permisos = json.loads(user.permisos_json or "[]")
        if not any(p.get("id") == permission["id"] for p in permisos):
            permisos.append(permission)
            user.permisos_json = json.dumps(permisos)
            db.session.commit()
        return jsonify({"success": True, "mensaje": "Permiso asignado", "usuario": user.to_public_dict()}), 200

    @app.route("/permissions/revoke", methods=["POST"])
    def revoke_permission():
        payload = _require_access_payload()
        if not payload:
            return jsonify({"success": False, "mensaje": "Token requerido"}), 401
        if not _require_admin(payload):
            return jsonify({"success": False, "mensaje": "No autorizado"}), 403
        body = request.get_json(silent=True) or {}
        user_id = str(body.get("usuarioId") or body.get("usuario_id") or "").strip()
        permiso_id = str(body.get("permisoId") or body.get("permiso_id") or "").strip()
        if not user_id or not permiso_id:
            return jsonify({"success": False, "mensaje": "Datos inválidos"}), 400
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "mensaje": "Usuario no encontrado"}), 404
        permisos = json.loads(user.permisos_json or "[]")
        permisos = [p for p in permisos if p.get("id") != permiso_id]
        user.permisos_json = json.dumps(permisos)
        db.session.commit()
        return jsonify({"success": True, "mensaje": "Permiso revocado", "usuario": user.to_public_dict()}), 200

    @app.route("/openapi.json", methods=["GET"])
    def openapi():
        return jsonify(
            {
                "openapi": "3.0.3",
                "info": {
                    "title": "Edu-Retention Backend API",
                    "version": "1.0.0",
                },
                "servers": [{"url": "/"}],
                "components": {
                    "securitySchemes": {
                        "bearerAuth": {
                            "type": "http",
                            "scheme": "bearer",
                            "bearerFormat": "JWT",
                        }
                    }
                },
                "paths": {
                    "/health": {
                        "get": {
                            "summary": "Health check",
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {"application/json": {"schema": {"type": "object"}}},
                                }
                            },
                        }
                    },
                    "/api/surveys": {
                        "get": {
                            "summary": "Listar encuestas",
                            "responses": {
                                "200": {
                                    "description": "Lista de encuestas",
                                    "content": {"application/json": {"schema": {"type": "array"}}},
                                }
                            },
                        },
                        "post": {
                            "summary": "Crear encuesta",
                            "security": [{"bearerAuth": []}],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "titulo": {"type": "string"},
                                                "descripcion": {"type": "string"},
                                                "estado": {"type": "string"},
                                                "preguntas": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "pregunta": {"type": "string"},
                                                            "tipo": {"type": "string"},
                                                            "requerida": {"type": "boolean"},
                                                            "opciones": {"type": "array", "items": {"type": "string"}},
                                                        },
                                                        "required": ["pregunta", "tipo"],
                                                    },
                                                },
                                            },
                                            "required": ["titulo", "descripcion", "preguntas"],
                                        }
                                    }
                                },
                            },
                            "responses": {
                                "201": {
                                    "description": "Encuesta creada",
                                    "content": {"application/json": {"schema": {"type": "object"}}},
                                }
                            },
                        },
                    },
                    "/api/surveys/{survey_id}": {
                        "get": {
                            "summary": "Obtener encuesta por ID",
                            "parameters": [
                                {
                                    "name": "survey_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Encuesta",
                                    "content": {"application/json": {"schema": {"type": "object"}}},
                                },
                                "404": {"description": "No encontrada"},
                            },
                        },
                        "put": {
                            "summary": "Actualizar encuesta",
                            "parameters": [
                                {
                                    "name": "survey_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "requestBody": {
                                "required": False,
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "responses": {
                                "200": {"description": "Actualizada"},
                                "404": {"description": "No encontrada"},
                            },
                        },
                        "delete": {
                            "summary": "Eliminar encuesta",
                            "parameters": [
                                {
                                    "name": "survey_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "responses": {"200": {"description": "Eliminada"}, "404": {"description": "No encontrada"}},
                        },
                    },
                    "/api/surveys/{survey_id}/response": {
                        "post": {
                            "summary": "Enviar respuestas a encuesta",
                            "security": [{"bearerAuth": []}],
                            "parameters": [
                                {
                                    "name": "survey_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"respuestas": {"type": "object"}},
                                            "required": ["respuestas"],
                                        }
                                    }
                                },
                            },
                            "responses": {
                                "201": {"description": "Respuesta guardada"},
                                "404": {"description": "Encuesta no encontrada"},
                            },
                        }
                    },
                    "/api/surveys/{survey_id}/responses": {
                        "get": {
                            "summary": "Listar respuestas de una encuesta",
                            "parameters": [
                                {
                                    "name": "survey_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "responses": {"200": {"description": "Lista de respuestas", "content": {"application/json": {"schema": {"type": "array"}}}}},
                        }
                    },
                    "/api/contacts": {
                        "get": {
                            "summary": "Listar contactos (usuarios)",
                            "responses": {"200": {"description": "Lista de usuarios", "content": {"application/json": {"schema": {"type": "array"}}}}},
                        }
                    },
                    "/api/contacts/search": {
                        "get": {
                            "summary": "Buscar contactos por nombre/email",
                            "parameters": [
                                {"name": "term", "in": "query", "required": False, "schema": {"type": "string"}}
                            ],
                            "responses": {"200": {"description": "Resultados", "content": {"application/json": {"schema": {"type": "array"}}}}},
                        }
                    },
                    "/api/auth/register": {
                        "post": {
                            "summary": "Registrar usuario",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "nombre": {"type": "string"},
                                                "email": {"type": "string"},
                                                "contraseña": {"type": "string"},
                                            },
                                            "required": ["nombre", "email", "contraseña"],
                                        }
                                    }
                                },
                            },
                            "responses": {
                                "201": {"description": "Usuario creado"},
                                "400": {"description": "Datos inválidos"},
                                "409": {"description": "Email ya existe"},
                            },
                        }
                    },
                    "/api/auth/login": {
                        "post": {
                            "summary": "Iniciar sesión",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"email": {"type": "string"}, "contraseña": {"type": "string"}},
                                            "required": ["email", "contraseña"],
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "OK"}, "401": {"description": "Credenciales inválidas"}},
                        }
                    },
                    "/api/auth/refresh": {
                        "post": {
                            "summary": "Refrescar token de acceso",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"refreshToken": {"type": "string"}},
                                            "required": ["refreshToken"],
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "OK"}, "401": {"description": "Refresh inválido"}},
                        }
                    },
                    "/api/users/profile": {
                        "get": {
                            "summary": "Obtener perfil del usuario",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        },
                        "put": {
                            "summary": "Actualizar perfil del usuario",
                            "security": [{"bearerAuth": []}],
                            "requestBody": {
                                "required": False,
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            },
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        },
                    },
                    "/risk/analysis": {
                        "get": {
                            "summary": "Obtener análisis de riesgos",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/risk/reports": {
                        "get": {
                            "summary": "Obtener reportes de riesgo",
                            "security": [{"bearerAuth": []}],
                            "parameters": [
                                {"name": "filtro", "in": "query", "required": False, "schema": {"type": "string"}}
                            ],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/notifications": {
                        "get": {
                            "summary": "Listar notificaciones del usuario",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/notifications/{notification_id}/read": {
                        "post": {
                            "summary": "Marcar notificación como leída",
                            "security": [{"bearerAuth": []}],
                            "parameters": [
                                {
                                    "name": "notification_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/permissions": {
                        "get": {
                            "summary": "Listar permisos disponibles",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/permissions/assign": {
                        "post": {
                            "summary": "Asignar permiso a usuario (admin)",
                            "security": [{"bearerAuth": []}],
                            "requestBody": {
                                "required": True,
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            },
                            "responses": {
                                "200": {"description": "OK"},
                                "401": {"description": "No autorizado"},
                                "403": {"description": "Prohibido"},
                            },
                        }
                    },
                    "/permissions/revoke": {
                        "post": {
                            "summary": "Revocar permiso de usuario (admin)",
                            "security": [{"bearerAuth": []}],
                            "requestBody": {
                                "required": True,
                                "content": {"application/json": {"schema": {"type": "object"}}},
                            },
                            "responses": {
                                "200": {"description": "OK"},
                                "401": {"description": "No autorizado"},
                                "403": {"description": "Prohibido"},
                            },
                        }
                    },
                },
            }
        )

    @app.route("/docs", methods=["GET"])
    def docs():
        html = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
      });
    </script>
  </body>
</html>
""".strip()
        return Response(html, mimetype="text/html")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


def register_routes(app):
    """Registrar blueprints de rutas"""
    from routes.auth import auth_bp
    from routes.contacts import contacts_bp
    from routes.surveys import surveys_bp
    from routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(contacts_bp)


if __name__ == '__main__':
    app = create_app()
    # En desarrollo, usar host='0.0.0.0' para permitir conexiones remotas
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
