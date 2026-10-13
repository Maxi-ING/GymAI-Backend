# Despliegue con Supabase Render y Vercel

El código está preparado para estos servicios. El repositorio por sí solo no crea proyectos ni acredita un despliegue. Las pruebas de integración usan PostgreSQL en GitHub Actions; no son evidencia de una conexión a tu Supabase.

## 1 Crear PostgreSQL en Supabase

Crea un proyecto y conserva la contraseña de PostgreSQL. No usamos Supabase Auth: el login, las cuentas y los permisos pertenecen a FastAPI.

En Connect copia la conexión **Session pooler**, puerto 5432, adecuada para una API persistente cuando necesita IPv4. Convierte el prefijo en postgresql+psycopg y añade sslmode=require. Usa el host y usuario exactos que muestre tu proyecto; no copies los de otro proyecto.

La contraseña debe estar codificada como componente de URL si contiene caracteres como @, /, # o %. No publiques la URL, ni la pegues en el chat o en capturas.

La aplicación crea ocho tablas en el esquema **gym_app**. Mantenlo fuera de Exposed schemas de la Data API de Supabase; no concedas acceso a anon ni authenticated. No se usa la clave anon ni service_role en el frontend. Puedes seleccionar gym_app en el panel/SQL Editor para consultar las tablas.

## 2 Preparar las tablas y el primer administrador

Desde una copia local del repositorio configura .env con la URL cloud y un JWT_SECRET propio. Instala las dependencias e inicia el entorno virtual según el README. Ejecuta:

```bash
alembic upgrade head
python -m app.cli seed-catalog
python -m app.cli create-admin --nombre "Max Admin" --correo "htmaximo3904@gmail.com"
```

El último comando solicita y confirma la contraseña sin mostrarla. No hay credenciales administrativas predeterminadas. Repetir seed-catalog no duplica ejercicios; create-admin no cambia contraseñas ni eleva cuentas existentes.

El correo del administrador acordado es htmaximo3904@gmail.com. La contraseña elegida se introduce en privado; no forma parte del repositorio ni del frontend. Para una preparación sin interacción también puedes definir ADMIN_NOMBRE, ADMIN_CORREO y ADMIN_CLAVE en variables de entorno, o en un archivo local .env.admin excluido de Git, y ejecutar:

```bash
python -m app.cli create-admin --from-env
```

En Render configura esas variables como secretos antes de ejecutar el comando desde su consola. No las necesitas en Vercel. La configuración valida los datos antes de iniciar la transacción, oculta la contraseña en su representación y aplica el mismo hash Argon2 del registro. Este comando crea la cuenta únicamente en la base indicada por DATABASE_URL; preparar los valores no crea una cuenta en Supabase. Si ya existe ese administrador, conserva su contraseña. Una cuenta de usuario con el mismo correo requiere revisión administrativa; el comando no cambia su rol automáticamente.

Los correos se validan por formato (parte local, @ y dominio), con un máximo de 254 caracteres y normalización a minúsculas. No se consulta DNS, no se envía un enlace de verificación y no se exige que el buzón exista. La misma regla se aplica al registro, login y edición por usuario o administrador.

Las migraciones deben ejecutarse antes de publicar la API. No se ejecutan automáticamente al iniciar cada servidor. Alembic conserva su versión en gym_app.alembic_version. Revisa toda migración antes de aplicarla; no ejecutes downgrade en una base con datos reales sin una estrategia de respaldo.

Para producción se recomienda una conexión de migración con permisos de esquema y un usuario de ejecución limitado a las tablas de gym_app. Si se separan, aplica migraciones con la cuenta de administración y configura en Render la URL de la cuenta de ejecución. Conserva los permisos de secuencias para INSERT. El servidor no necesita exponer PostgreSQL al navegador.

## 3 Publicar FastAPI en Render

Conecta GymAI-Backend y utiliza render.yaml como Blueprint, o crea un Web Service con:

- Rama: main.
- Runtime: Python 3.12.
- Build: pip install -r requirements.txt.
- Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1.
- Health check: /health.

Configura DATABASE_URL con la conexión de Supabase y TLS; JWT_SECRET aleatorio de 32 caracteres como mínimo; ENVIRONMENT=production; CORS_ORIGINS como arreglo JSON de orígenes exactos HTTPS, por ejemplo ["https://tu-proyecto.vercel.app"].

La configuración rechaza secretos de ejemplo. Puedes generar uno localmente con python -c "import secrets; print(secrets.token_urlsafe(48))". Si cambias el secreto, los tokens anteriores dejan de servir.

La API usa un pool de 5 conexiones y hasta 2 adicionales por proceso. El límite de autenticación es de 12 solicitudes por minuto/IP/proceso. Una expansión a varias réplicas requiere coordinar ese límite y el presupuesto de conexiones; no se ha realizado una prueba de carga.

## 4 Conectar Vercel

En el proyecto del frontend configura VITE_API_URL con la URL HTTPS de Render, sin barra final, y vuelve a desplegarlo. React consume la API y no accede directamente a la BD. Configuración de tema y animaciones permanece en el navegador.

Agrega en CORS solo los dominios que realmente deben usar la API. Un dominio de Preview diferente requiere su propio origen autorizado; no uses un comodín general para todos los proyectos de Vercel.

## 5 Verificar

Consulta /health: debe responder status y database con ok. /docs ofrece Swagger con HTTP Bearer; usa POST /auth/login con JSON y pega access_token en Authorize.

Desde Vercel registra una cuenta, completa perfil, guarda una sesión y recarga para verificar persistencia. Consulta progreso e Inicio. Con menos de cuatro semanas se informa historial insuficiente. El historial didáctico de la demo no se copia a usuarios reales.

Verifica también el acceso administrativo, desactivación de cuentas y ejercicios, y bloqueo de usuarios sin permisos. No compartas tokens ni contraseñas en evidencias.

## Referencias

- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT
- https://render.com/docs/deploy-fastapi
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
