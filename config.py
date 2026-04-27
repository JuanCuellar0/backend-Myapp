import os
from datetime import timedelta

class Config:
    """Configuración base"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Si no hay SECRET_KEY en el sistema, usa una por defecto para no romper el inicio
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')
    JSON_SORT_KEYS = False
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Tokens JWT
    JWT_SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

class DevelopmentConfig(Config):
    """Configuración para desarrollo local"""
    DEBUG = True
    TESTING = False
    # CORREGIDO: os.getenv(Nombre_Variable, Valor_Por_Defecto)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    CORS_ORIGINS = ['http://localhost:19006', 'http://localhost:8081', 'http://localhost:5000']

class StagingConfig(Config):
    """Configuración para staging"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')

class ProductionConfig(Config):
    """Configuración para producción (Render/Azure)"""
    DEBUG = False
    TESTING = False
    # Render inyecta DATABASE_URL automáticamente
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Evitamos el raise ValueError para que Render no falle antes de que configures la variable
    # El valor por defecto ya se maneja en la clase Config
    if not os.getenv('SECRET_KEY'):
        print("WARNING: SECRET_KEY not set in production!")

def get_config():
    """Obtener config según FLASK_ENV"""
    # Render suele usar 'production' por defecto
    env = os.getenv('FLASK_ENV', 'production').lower()
    
    configs = {
        'development': DevelopmentConfig,
        'staging': StagingConfig,
        'production': ProductionConfig,
    }
    
    return configs.get(env, ProductionConfig)