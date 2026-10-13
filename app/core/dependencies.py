from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.modules.users.models import Usuario

DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    denied = HTTPException(
        401, "Sesión inválida o vencida.", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise denied
    try:
        user_id = decode_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise denied from None
    user = db.get(Usuario, user_id)
    if user is None:
        raise denied
    if not user.activo:
        raise HTTPException(403, "Tu cuenta está inactiva.")
    return user


CurrentUser = Annotated[Usuario, Depends(current_user)]


def admin_user(user: CurrentUser):
    if user.rol != "admin":
        raise HTTPException(403, "Se requiere permiso de administrador.")
    return user


AdminUser = Annotated[Usuario, Depends(admin_user)]
