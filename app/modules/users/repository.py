from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import Medicion, Usuario


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str):
        return self.db.scalar(select(Usuario).where(Usuario.correo == email.lower()))

    def create(self, **values):
        user = Usuario(**values)
        self.db.add(user)
        self.db.flush()
        return user

    def measurement(self, user, fecha, peso):
        item = Medicion(usuario_id=user.id, fecha=fecha, peso_kg=peso, talla_m=user.talla_m)
        self.db.add(item)
        self.db.flush()
        return item
