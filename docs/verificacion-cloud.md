# Verificación de la base cloud

Fecha: 2026-10-13T17:52:10.409078-05:00. Comprobaciones contra la API pública de Render: 29.

| Resultado | Valor |
|---|---:|
| Usuarios | 2 |
| Ejercicios activos | 6 |
| Sesiones ficticias | 8 |
| Registros de detalle | 24 |
| Volumen acumulado | 28 584 kg |
| Siguiente carga estimada | 48 kg |
| Estimación hasta la meta | 2 semanas |

Se verificó acceso administrativo, registro público, perfil, medición, metas, predicción guardada e Inicio. Usuario sin rol administrativo: 403. Visitante sin token: 401. Correo sin formato: 422. Sesión con un ejercicio inexistente: 422 sin aumentar el historial. Administrador al intentar análisis: 403.

El ejemplo de ocho semanas es ficticio y está en Demo Gimnasio. No mide precisión con personas reales, carga concurrente ni rendimiento de producción. La verificación no guarda tokens, hashes ni contraseñas en el repositorio.

CI del PR #11: 44 pruebas Python con PostgreSQL, 4 pruebas del frontend en escritorio/móvil, Ruff, Alembic check y reversión/reaplicación de migraciones. Vercel tiene VITE_API_URL configurado para producción y fue redesplegado.
