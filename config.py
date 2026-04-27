import os
from datetime import timedelta

class Config:
    """Configuración base"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')
    JSON_SORT_KEYS = False
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Tokens JWT
    JWT_SECRET = os.getenv('SECRET_KEY', 'dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)


class DevelopmentConfig(Config):
    """Configuración para desarrollo local"""
    DEBUG = True
    TESTING = False
    # En desarrollo, usar SQLite local
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///app.db'
    )
    # Permitir todas las origins en desarrollo
    CORS_ORIGINS = ['http://localhost:19006', 'http://localhost:8081', 'http://localhost:5000']


class StagingConfig(Config):
    """Configuración para staging (pruebas funcionales)"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    # Origins específicas
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')


class ProductionConfig(Config):
    """Configuración para producción (AZURE)"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    # Origins específicas desde variables de entorno
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    # En producción, validar que hay SECRET_KEY
    if not os.getenv('SECRET_KEY'):
        raise ValueError("SECRET_KEY must be set in production")


def get_config():
    """Obtener config según FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    configs = {
        'development': DevelopmentConfig,
        'staging': StagingConfig,
        'production': ProductionConfig,
    }
    
    return configs.get(env, DevelopmentConfig)
