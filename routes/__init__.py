import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import jwt


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or ""
    if not secret:
        raise ValueError("JWT secret not configured")
    return secret


def create_access_token(user_id: str, rol: str, expires_in_seconds: int = 900) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "rol": rol,
        "typ": "access",
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def create_refresh_token(user_id: str, rol: str, expires_in_seconds: int = 60 * 60 * 24 * 7) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "rol": rol,
        "typ": "refresh",
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except Exception:
        return None
    if expected_type and payload.get("typ") != expected_type:
        return None
    return payload


def get_bearer_token(auth_header: str) -> Optional[str]:
    if not auth_header:
        return None
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    return token
