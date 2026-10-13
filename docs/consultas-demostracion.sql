-- Consultas de solo lectura para Supabase SQL Editor.
-- En Table Editor selecciona el esquema gym_app.
-- No se consulta clave_hash ni se exponen credenciales.

-- Versión del esquema.
SELECT version_num FROM gym_app.alembic_version;

-- Las ocho tablas de dominio y la tabla técnica.
SELECT tablename, rowsecurity
FROM pg_tables WHERE schemaname = 'gym_app' ORDER BY tablename;

-- Relaciones y reglas al borrar.
SELECT conname AS relacion, pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE connamespace = 'gym_app'::regnamespace AND contype = 'f'
ORDER BY conname;

-- Cabecera y detalle del entrenamiento ficticio.
SELECT u.nombre, s.id AS sesion_id, s.fecha, e.nombre AS ejercicio,
       r.series, r.repeticiones, r.carga_kg,
       r.series * r.repeticiones * r.carga_kg AS volumen_kg
FROM gym_app.usuarios u
JOIN gym_app.sesiones s ON s.usuario_id = u.id
JOIN gym_app.registros r ON r.sesion_id = s.id
JOIN gym_app.ejercicios e ON e.id = r.ejercicio_id
WHERE u.correo = 'demo.gimnasio@example.com'
ORDER BY s.fecha, s.id, r.id;

-- Resumen del usuario demostrativo: 8 sesiones, 24 filas, 28 584 kg.
SELECT count(DISTINCT s.id) AS sesiones, count(r.id) AS registros,
       sum(r.series * r.repeticiones * r.carga_kg) AS volumen_kg
FROM gym_app.usuarios u
JOIN gym_app.sesiones s ON s.usuario_id = u.id
JOIN gym_app.registros r ON r.sesion_id = s.id
WHERE u.correo = 'demo.gimnasio@example.com';

-- Carga máxima por ejercicio.
SELECT e.nombre, max(r.carga_kg) AS carga_maxima_kg
FROM gym_app.usuarios u
JOIN gym_app.sesiones s ON s.usuario_id = u.id
JOIN gym_app.registros r ON r.sesion_id = s.id
JOIN gym_app.ejercicios e ON e.id = r.ejercicio_id
WHERE u.correo = 'demo.gimnasio@example.com'
GROUP BY e.id, e.nombre ORDER BY e.id;

-- Análisis guardado: un resultado histórico, no recalculado por esta consulta.
SELECT a.fecha, e.nombre, a.resultado
FROM gym_app.analisis a
JOIN gym_app.usuarios u ON u.id = a.usuario_id
JOIN gym_app.ejercicios e ON e.id = a.ejercicio_id
WHERE u.correo = 'demo.gimnasio@example.com'
ORDER BY a.fecha DESC;
