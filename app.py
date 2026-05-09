"""
Backend API para Edu-Retention
Separado del frontend para mejor escalabilidad
"""
import os
from flask import Flask, Response, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from config import get_config
from models import db

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
                            "security": [{"bearerAuth": []}],
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
                            "security": [{"bearerAuth": []}],
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
                                                "adminCode": {"type": "string"},
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
                            "summary": "Refrescar access token",
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
                    "/api/auth/recover-password": {
                        "post": {
                            "summary": "Solicitar recuperación de contraseña",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"email": {"type": "string"}},
                                            "required": ["email"],
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "OK"}},
                        }
                    },
                    "/api/auth/reset-password": {
                        "post": {
                            "summary": "Restablecer contraseña con token",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"token": {"type": "string"}, "contraseña": {"type": "string"}},
                                            "required": ["token", "contraseña"],
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "OK"}, "401": {"description": "Token inválido"}},
                        }
                    },
                    "/api/users/profile": {
                        "get": {
                            "summary": "Obtener perfil",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        },
                        "put": {
                            "summary": "Actualizar perfil",
                            "security": [{"bearerAuth": []}],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"nombre": {"type": "string"}},
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        },
                    },
                    "/risk/reports": {
                        "get": {
                            "summary": "Reportes de riesgo (derivados de respuestas)",
                            "security": [{"bearerAuth": []}],
                            "parameters": [
                                {"name": "filtro", "in": "query", "required": False, "schema": {"type": "string"}}
                            ],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
                        }
                    },
                    "/risk/analysis": {
                        "get": {
                            "summary": "Análisis de riesgo (derivado de respuestas)",
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "OK"}, "401": {"description": "No autorizado"}},
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
    from routes.risk import risk_bp
    from routes.surveys import surveys_bp
    from routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(risk_bp)


if __name__ == '__main__':
    app = create_app()
    # En desarrollo, usar host='0.0.0.0' para permitir conexiones remotas
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
