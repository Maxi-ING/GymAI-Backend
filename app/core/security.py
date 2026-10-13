from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash("dummy-password-never-used-for-authentication")


def hash_password(value: str):
    return passwords.hash(value)


def verify_password(value: str, stored: str):
    try:
        return passwords.verify(value, stored)
    except (ValueError, TypeError):
        return False


def issue_token(user_id: int):
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.token_minutes),
            "iss": "fitanalytics-api",
            "aud": "fitanalytics-web",
            "jti": str(uuid4()),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(value: str):
    claims = jwt.decode(
        value,
        get_settings().jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        issuer="fitanalytics-api",
        audience="fitanalytics-web",
        options={"require": ["sub", "exp", "iat", "iss", "aud", "jti"]},
    )
    if not isinstance(claims["sub"], str) or not claims["sub"].isdigit() or int(claims["sub"]) < 1:
        raise jwt.InvalidTokenError("Invalid subject")
    return int(claims["sub"])
