"""Crear las ocho tablas del dominio en un esquema privado."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS gym_app")
    op.execute(
        "CREATE TABLE gym_app.ejercicios (\n\tid SERIAL NOT NULL, \n\tnombre VARCHAR(80) NOT NULL, \n\tnombre_normalizado VARCHAR(80) NOT NULL, \n\tunidad VARCHAR(5) DEFAULT 'kg' NOT NULL, \n\tactivo BOOLEAN DEFAULT 'true' NOT NULL, \n\tCONSTRAINT pk_ejercicios PRIMARY KEY (id), \n\tCONSTRAINT ck_ejercicios_unidad CHECK (unidad = 'kg'), \n\tCONSTRAINT uq_ejercicios_nombre_normalizado UNIQUE (nombre_normalizado)\n)"
    )
    op.execute(
        "CREATE TABLE gym_app.usuarios (\n\tid SERIAL NOT NULL, \n\tnombre VARCHAR(100) NOT NULL, \n\tcorreo VARCHAR(254) NOT NULL, \n\tclave_hash TEXT NOT NULL, \n\trol VARCHAR(10) DEFAULT 'usuario' NOT NULL, \n\tactivo BOOLEAN DEFAULT 'true' NOT NULL, \n\tedad INTEGER, \n\ttalla_m NUMERIC(3, 2), \n\tobjetivo VARCHAR(60), \n\tperfil_completo BOOLEAN DEFAULT 'false' NOT NULL, \n\tcreado TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_usuarios PRIMARY KEY (id), \n\tCONSTRAINT ck_usuarios_rol CHECK (rol IN ('admin','usuario')), \n\tCONSTRAINT ck_usuarios_edad CHECK (edad IS NULL OR edad BETWEEN 18 AND 120), \n\tCONSTRAINT ck_usuarios_talla CHECK (talla_m IS NULL OR talla_m BETWEEN 0.50 AND 2.50), \n\tCONSTRAINT ck_usuarios_perfil CHECK (NOT perfil_completo OR (edad IS NOT NULL AND talla_m IS NOT NULL AND objetivo IS NOT NULL)), \n\tCONSTRAINT uq_usuarios_correo UNIQUE (correo)\n)"
    )
    op.execute(
        "CREATE TABLE gym_app.auditoria (\n\tid SERIAL NOT NULL, \n\tactor_id INTEGER NOT NULL, \n\taccion VARCHAR(60) NOT NULL, \n\trecurso VARCHAR(60) NOT NULL, \n\trecurso_id INTEGER NOT NULL, \n\tfecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tdetalle JSONB NOT NULL, \n\tCONSTRAINT pk_auditoria PRIMARY KEY (id), \n\tCONSTRAINT fk_auditoria_actor_id_usuarios FOREIGN KEY(actor_id) REFERENCES gym_app.usuarios (id)\n)"
    )
    op.execute(
        "CREATE TABLE gym_app.mediciones (\n\tid SERIAL NOT NULL, \n\tusuario_id INTEGER NOT NULL, \n\tfecha DATE NOT NULL, \n\tpeso_kg NUMERIC(4, 1) NOT NULL, \n\ttalla_m NUMERIC(3, 2) NOT NULL, \n\tCONSTRAINT pk_mediciones PRIMARY KEY (id), \n\tCONSTRAINT ck_mediciones_peso CHECK (peso_kg BETWEEN 20 AND 400), \n\tCONSTRAINT ck_mediciones_talla CHECK (talla_m BETWEEN 0.50 AND 2.50), \n\tCONSTRAINT ck_mediciones_fecha CHECK (fecha >= DATE '2000-01-01'), \n\tCONSTRAINT fk_mediciones_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES gym_app.usuarios (id)\n)"
    )
    op.execute("CREATE INDEX ix_mediciones_usuario_fecha ON gym_app.mediciones (usuario_id, fecha)")
    op.execute(
        "CREATE TABLE gym_app.metas (\n\tid SERIAL NOT NULL, \n\tusuario_id INTEGER NOT NULL, \n\tejercicio_id INTEGER NOT NULL, \n\tcarga_objetivo_kg NUMERIC(4, 1) NOT NULL, \n\tCONSTRAINT pk_metas PRIMARY KEY (id), \n\tCONSTRAINT ck_metas_carga CHECK (carga_objetivo_kg > 0 AND carga_objetivo_kg <= 600), \n\tCONSTRAINT fk_metas_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES gym_app.usuarios (id), \n\tCONSTRAINT fk_metas_ejercicio_id_ejercicios FOREIGN KEY(ejercicio_id) REFERENCES gym_app.ejercicios (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_metas_usuario_ejercicio ON gym_app.metas (usuario_id, ejercicio_id)"
    )
    op.execute(
        "CREATE TABLE gym_app.sesiones (\n\tid SERIAL NOT NULL, \n\tusuario_id INTEGER NOT NULL, \n\tfecha DATE NOT NULL, \n\tCONSTRAINT pk_sesiones PRIMARY KEY (id), \n\tCONSTRAINT ck_sesiones_fecha CHECK (fecha >= DATE '2000-01-01'), \n\tCONSTRAINT fk_sesiones_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES gym_app.usuarios (id)\n)"
    )
    op.execute("CREATE INDEX ix_sesiones_usuario_fecha ON gym_app.sesiones (usuario_id, fecha)")
    op.execute(
        "CREATE TABLE gym_app.analisis (\n\tid SERIAL NOT NULL, \n\tusuario_id INTEGER NOT NULL, \n\tejercicio_id INTEGER NOT NULL, \n\tmeta_id INTEGER, \n\tfecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tresultado JSONB NOT NULL, \n\tCONSTRAINT pk_analisis PRIMARY KEY (id), \n\tCONSTRAINT fk_analisis_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES gym_app.usuarios (id), \n\tCONSTRAINT fk_analisis_ejercicio_id_ejercicios FOREIGN KEY(ejercicio_id) REFERENCES gym_app.ejercicios (id), \n\tCONSTRAINT fk_analisis_meta_id_metas FOREIGN KEY(meta_id) REFERENCES gym_app.metas (id) ON DELETE SET NULL\n)"
    )
    op.execute("CREATE INDEX ix_analisis_usuario_fecha ON gym_app.analisis (usuario_id, fecha)")
    op.execute(
        "CREATE TABLE gym_app.registros (\n\tid SERIAL NOT NULL, \n\tsesion_id INTEGER NOT NULL, \n\tejercicio_id INTEGER NOT NULL, \n\tseries INTEGER NOT NULL, \n\trepeticiones INTEGER NOT NULL, \n\tcarga_kg NUMERIC(4, 1) NOT NULL, \n\tCONSTRAINT pk_registros PRIMARY KEY (id), \n\tCONSTRAINT ck_registros_series CHECK (series BETWEEN 1 AND 20), \n\tCONSTRAINT ck_registros_repeticiones CHECK (repeticiones BETWEEN 1 AND 100), \n\tCONSTRAINT ck_registros_carga CHECK (carga_kg BETWEEN 0 AND 600), \n\tCONSTRAINT fk_registros_sesion_id_sesiones FOREIGN KEY(sesion_id) REFERENCES gym_app.sesiones (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_registros_ejercicio_id_ejercicios FOREIGN KEY(ejercicio_id) REFERENCES gym_app.ejercicios (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_registros_sesion_ejercicio ON gym_app.registros (sesion_id, ejercicio_id)"
    )


def downgrade():
    op.drop_table("registros", schema="gym_app")
    op.drop_table("analisis", schema="gym_app")
    op.drop_table("sesiones", schema="gym_app")
    op.drop_table("metas", schema="gym_app")
    op.drop_table("mediciones", schema="gym_app")
    op.drop_table("auditoria", schema="gym_app")
    op.drop_table("usuarios", schema="gym_app")
    op.drop_table("ejercicios", schema="gym_app")
