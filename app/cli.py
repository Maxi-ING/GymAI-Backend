import argparse
from getpass import getpass

from sqlalchemy import select, text

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.modules.admin.repository import ADMIN_LOCK
from app.modules.admin.schemas import ExerciseCreate
from app.modules.records.models import Ejercicio
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import Registration

CATALOG = [
    "Press de banca",
    "Sentadilla",
    "Peso muerto",
    "Remo con barra",
    "Press militar",
    "Curl de bíceps",
]


def seed_catalog(db):
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})
    for name in CATALOG:
        normalized = name.casefold()
        if not db.scalar(select(Ejercicio).where(Ejercicio.nombre_normalizado == normalized)):
            data = ExerciseCreate(nombre=name)
            db.add(Ejercicio(nombre=data.nombre, nombre_normalizado=normalized))
    db.flush()


def create_admin(db, data):
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMIN_LOCK})
    repository = UserRepository(db)
    existing = repository.by_email(data.correo)
    if existing:
        if existing.rol != "admin" or not existing.activo:
            raise ValueError(
                "El correo pertenece a otra cuenta. No se cambia su acceso desde este comando."
            )
        return existing
    return repository.create(
        nombre=data.nombre, correo=data.correo, clave_hash=hash_password(data.clave), rol="admin"
    )


def main():
    parser = argparse.ArgumentParser(description="Preparación inicial de FitAnalytics AI")
    parser.add_argument("command", choices=["seed-catalog", "create-admin"])
    parser.add_argument("--nombre")
    parser.add_argument("--correo")
    args = parser.parse_args()
    with SessionFactory.begin() as db:
        if args.command == "seed-catalog":
            seed_catalog(db)
            print("Catálogo preparado sin duplicar ejercicios.")
        else:
            if not args.nombre or not args.correo:
                parser.error("create-admin requiere --nombre y --correo.")
            password = getpass("Contraseña del administrador: ")
            if password != getpass("Repite la contraseña: "):
                raise ValueError("Las contraseñas no coinciden.")
            create_admin(db, Registration(nombre=args.nombre, correo=args.correo, clave=password))
            print("Administrador preparado. No se modifica la contraseña de una cuenta existente.")


if __name__ == "__main__":
    main()
