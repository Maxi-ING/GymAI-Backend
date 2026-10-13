from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException
from sqlalchemy import func, select

from app.cli import create_admin
from app.core.database import SessionFactory
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import AdminUpdate
from app.modules.admin.service import AdminService
from app.modules.users.models import Usuario
from app.modules.users.schemas import Registration


def test_two_concurrent_demotions_cannot_remove_last_admin(client, admin):
    with SessionFactory.begin() as db:
        second = create_admin(
            db,
            Registration(nombre="Second Admin", correo="second@example.com", clave="password-123"),
        )
        second_id = second.id
        first_id = db.scalar(select(Usuario.id).where(Usuario.correo == "admin@example.com"))
    barrier = Barrier(2)

    def demote(actor_id, target_id):
        with SessionFactory() as db:
            actor = db.get(Usuario, actor_id)
            barrier.wait(timeout=10)
            try:
                AdminService(AdminRepository(db)).update_user(
                    actor, target_id, AdminUpdate(rol="usuario")
                )
                db.commit()
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(demote, first_id, second_id)
        b = pool.submit(demote, second_id, first_id)
        results = [a.result(timeout=20), b.result(timeout=20)]
    assert sorted(results) == [200, 409]
    with SessionFactory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Usuario)
                .where(Usuario.rol == "admin", Usuario.activo.is_(True))
            )
            == 1
        )
