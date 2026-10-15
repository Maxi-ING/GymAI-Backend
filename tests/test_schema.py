from sqlalchemy import text

from app.core.database import SessionFactory


def test_private_schema_has_rls_and_no_public_schema_access(client):
    with SessionFactory() as db:
        assert db.scalar(text("SELECT version_num FROM gym_app.alembic_version")) == "0004"
        assert (
            db.scalar(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='gym_app' AND rowsecurity")
            )
            == 8
        )
        assert not db.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_namespace n, LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a WHERE n.nspname='gym_app' AND a.grantee=0 AND a.privilege_type='USAGE')"
            )
        )
        # Toda FK debe estar cubierta por el prefijo de un índice válido.
        missing = db.scalar(
            text("""
            SELECT count(*) FROM pg_constraint c
            WHERE c.connamespace = 'gym_app'::regnamespace AND c.contype = 'f'
            AND NOT EXISTS (
                SELECT 1 FROM pg_index i WHERE i.indrelid=c.conrelid AND i.indisvalid
                AND (SELECT array_agg(k.attnum ORDER BY k.ord)
                     FROM unnest(i.indkey::smallint[]) WITH ORDINALITY k(attnum, ord)
                     WHERE k.ord <= cardinality(c.conkey)) = c.conkey
            )
        """)
        )
        assert missing == 0
