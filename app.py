"""
Backend API para Edu-Retention
Separado del frontend para mejor escalabilidad
"""
import os
from flask import Flask, jsonify
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
