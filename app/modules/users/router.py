from fastapi import APIRouter, Depends

from app.core.dependencies import DB, CurrentUser
from app.core.rate_limit import auth_budget
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    AccountUpdate,
    Credentials,
    MeasurementInput,
    MeasurementOut,
    Registration,
    TokenOut,
    UserOut,
)
from app.modules.users.service import UserService

router = APIRouter(tags=["Cuentas"])


@router.post(
    "/auth/register", response_model=UserOut, status_code=201, dependencies=[Depends(auth_budget)]
)
def register(data: Registration, db: DB):
    return UserService(UserRepository(db)).register(data)


@router.post("/auth/login", response_model=TokenOut, dependencies=[Depends(auth_budget)])
def login(data: Credentials, db: DB):
    return UserService(UserRepository(db)).login(data)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update(data: AccountUpdate, db: DB, user: CurrentUser):
    return UserService(UserRepository(db)).update(user, data)


@router.post("/mediciones", response_model=MeasurementOut, status_code=201)
def measurement(data: MeasurementInput, db: DB, user: CurrentUser):
    return UserService(UserRepository(db)).measurement(user, data)
