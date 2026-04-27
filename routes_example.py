"""
Ejemplo de rutas de autenticación
Crear archivo: backend/routes/auth.py
"""

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User
from datetime import datetime, timezone

# Crear blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# ============================================================================
# LOGIN
# ============================================================================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login del usuario
    
    Request:
    {
        "email": "user@example.com",
        "contraseña": "password123"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Sesión iniciada correctamente",
        "usuario": {...},
        "token": "jwt-token-aqui"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('contraseña'):
            return jsonify({
                'success': False,
                'mensaje': 'Email y contraseña son requeridos'
            }), 400
        
        # Buscar usuario
        usuario = User.query.filter_by(email=data['email']).first()
        
        if not usuario or not check_password_hash(usuario.password_hash, data['contraseña']):
            return jsonify({
                'success': False,
                'mensaje': 'Email o contraseña incorrectos'
            }), 401
        
        # Aquí iría generación de JWT token
        # Por ahora, retornar datos del usuario
        
        return jsonify({
            'success': True,
            'mensaje': 'Sesión iniciada correctamente',
            'usuario': usuario.to_public_dict(),
            'token': f'token-{usuario.id}'  # Cambiar por JWT real
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


# ============================================================================
# REGISTRO
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registro de nuevo usuario
    
    Request:
    {
        "nombre": "Juan Perez",
        "email": "juan@example.com",
        "contraseña": "password123"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Usuario registrado correctamente",
        "usuario": {...},
        "token": "jwt-token-aqui"
    }
    """
    try:
        data = request.get_json()
        
        # Validaciones
        if not data or not all(k in data for k in ['nombre', 'email', 'contraseña']):
            return jsonify({
                'success': False,
                'mensaje': 'Nombre, email y contraseña son requeridos'
            }), 400
        
        # Verificar si email ya existe
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'mensaje': 'El email ya está registrado'
            }), 409
        
        # Crear nuevo usuario
        nuevo_usuario = User(
            nombre=data['nombre'],
            email=data['email'],
            password_hash=generate_password_hash(data['contraseña']),
            rol='user',  # Por defecto, rol de usuario
            fecha_registro=_utc_now_iso()
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Usuario registrado correctamente',
            'usuario': nuevo_usuario.to_public_dict(),
            'token': f'token-{nuevo_usuario.id}'  # Cambiar por JWT real
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


# ============================================================================
# LOGOUT
# ============================================================================

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout del usuario
    El cliente debería eliminar el token local
    """
    return jsonify({
        'success': True,
        'mensaje': 'Sesión cerrada correctamente'
    }), 200


# ============================================================================
# RECUPERAR CONTRASEÑA
# ============================================================================

@auth_bp.route('/recover-password', methods=['POST'])
def recover_password():
    """
    Solicitar recuperación de contraseña
    
    Request:
    {
        "email": "user@example.com"
    }
    
    Response:
    {
        "success": true,
        "mensaje": "Email de recuperación enviado"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({
                'success': False,
                'mensaje': 'Email es requerido'
            }), 400
        
        usuario = User.query.filter_by(email=data['email']).first()
        
        if not usuario:
            # No revelar si el email existe o no (seguridad)
            return jsonify({
                'success': True,
                'mensaje': 'Si el email existe, se enviará un correo de recuperación'
            }), 200
        
        # Aquí iría lógica para enviar email
        # Ejemplo: send_recovery_email(usuario.email, token)
        
        return jsonify({
            'success': True,
            'mensaje': 'Email de recuperación enviado'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'mensaje': f'Error: {str(e)}'
        }), 500


# ============================================================================
# VERIFICAR TOKEN
# ============================================================================

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Verificar si un token es válido
    
    Headers:
    {
        "Authorization": "Bearer token-aqui"
    }
    """
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'mensaje': 'Token no proporcionado'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Aquí iría validación de JWT
        # usuario_id = jwt.decode(token, SECRET_KEY)
        # usuario = User.query.get(usuario_id)
        
        return jsonify({
            'success': True,
            'mensaje': 'Token válido'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'mensaje': f'Token inválido: {str(e)}'
        }), 401
