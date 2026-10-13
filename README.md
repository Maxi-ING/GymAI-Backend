# FitAnalytics AI Backend

API de PowerGym compatible con [Gym-Frontend](https://github.com/Maxi-ING/Gym-Frontend). FastAPI organiza los casos de uso en módulos; SQLAlchemy consulta PostgreSQL y Alembic versiona el esquema. El destino acordado es **API en Render y PostgreSQL en Supabase**, con React en Vercel.

Implementa cuentas, roles, perfil, mediciones, catálogo, sesiones, progreso, metas, regresión lineal y administración. Inicio muestra el último análisis guardado; no entrena el modelo al abrir la página. Los días verdes del calendario se obtienen del historial de sesiones.

## Iniciar en tu computadora

Instala Python 3.12. Docker es opcional si ya tienes PostgreSQL o usarás una conexión cloud de desarrollo. No necesitas DBeaver.

Windows PowerShell:

```powershell
git clone https://github.com/Maxi-ING/GymAI-Backend.git
cd GymAI-Backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita .env: genera un JWT_SECRET propio. DATABASE_URL debe apuntar a PostgreSQL, nunca SQLite. El ejemplo usa solo una contraseña local de desarrollo.

Para iniciar PostgreSQL local:

```bash
docker compose up -d
```

Luego crea tablas y datos iniciales:

```bash
alembic upgrade head
python -m app.cli seed-catalog
python -m app.cli create-admin --nombre "Max Admin" --correo "htmaximo3904@gmail.com"
uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs y http://localhost:8000/health. El registro recibe JSON y no inicia sesión automáticamente. Login devuelve access_token; Authorize acepta ese token Bearer.

El frontend utiliza VITE_API_URL=http://localhost:8000. CORS admite por defecto localhost:5173 y localhost:4173.

## Estructura y POO

| Ubicación | Responsabilidad |
|---|---|
| app/main.py | API, errores JSON, CORS y disponibilidad |
| app/core | Configuración, transacciones, validación, permisos y objetos del dominio |
| app/modules/users | Cuentas y mediciones |
| app/modules/records | Ejercicios y sesiones |
| app/modules/dashboard | Progreso, rendimiento e Inicio |
| app/modules/predictions | Metas y análisis guardados |
| app/modules/admin | Gestión del gimnasio y auditoría |
| app/ml | Preparación semanal y predictor |
| migrations | Esquema versionado |
| tests | Reglas, integración PostgreSQL y frontend real |

RegistroEjercicio encapsula el cálculo de volumen; SesionEntrenamiento compone registros y calcula el total. MedicionCorporal calcula IMC. PredictorCarga es un contrato abstracto; PredictorLineal lo implementa. PredictionService acepta un colaborador de ese contrato, y la prueba lo sustituye por un predictor falso.

Los routers delegan a servicios; los repositorios encapsulan consultas. La dependencia de BD confirma la transacción antes de enviar una respuesta de éxito. Si falla una fila, la sesión completa se revierte.

## Datos y reglas

El esquema privado gym_app contiene usuarios, mediciones, ejercicios, sesiones, registros, metas, analisis y auditoria, además de la tabla de versión de Alembic. Correo único normalizado, claves foráneas, restricciones e índices.

Las mediciones conservan la talla utilizada para calcular su IMC histórico. El estado de una meta se calcula desde el historial actual: borrar una sesión puede cambiarlo. El análisis guardado es una instantánea histórica y no se recalcula al editar el historial.

Los correos requieren formato válido, sin comprobar DNS ni la existencia del buzón. La validación y normalización a minúsculas son compartidas por registro, login y edición.

Las cuentas públicas siempre son usuario. Cada operación consulta el rol y estado actuales; los permisos no dependen de un rol antiguo en el JWT. La protección del último admin usa un bloqueo transaccional PostgreSQL. Desactivar ejercicios conserva registros y metas.

El [contrato API](docs/api-contract.md) describe las rutas y formatos del frontend. Las tablas se crean por migraciones; no hay create_all al iniciar el servidor ni contraseñas administrativas de ejemplo.

## Modelo

POST /analisis agrupa carga máxima por intervalos semanales desde el primer registro y conserva huecos. Con cuatro semanas distintas ajusta LinearRegression al historial de esa cuenta y ejercicio. Devuelve tendencia, siguiente carga estimada y, con meta pendiente, tiempo aproximado. No necesita model.joblib.

Los estados son historial_insuficiente, meta_alcanzada, sin_tendencia_positiva y estimado. La proyección visual se limita a doce semanas; la estimación hasta la meta puede ser mayor. No es una prescripción de carga ni existe evidencia de precisión con usuarios reales. Las recomendaciones por reglas se identifican como tales.

## Pruebas

```bash
python -m pip install -r requirements-dev.txt
ruff check app migrations tests scripts
ruff format --check app migrations tests scripts
pytest -q
```

Sin TEST_DATABASE_URL se ejecutan las pruebas unitarias y se omiten las de integración. Para ejecutar todas utiliza una **base de pruebas cuyo nombre termine en _test**, aplica migraciones sobre ella y configura TEST_DATABASE_URL. Las pruebas borran únicamente las tablas del esquema gym_app de esa base.

GitHub Actions crea PostgreSQL 16, ejecuta todas las pruebas, verifica Alembic, revierte y reaplica las migraciones y prueba el frontend real en escritorio y móvil. El frontend está fijado al commit 10b028030b02d8e8505423baf3d8ba9348e2b310; actualizarlo requiere revisar el contrato.

Incluye aislamiento de cuentas, roles revocados, sesiones atómicas, catálogo inactivo, análisis guardado, correos duplicados y dos cambios de rol simultáneos. Las pruebas de navegador no interceptan las respuestas del backend.

## Despliegue y estado

Sigue [Supabase, Render y Vercel](docs/despliegue.md). render.yaml y Dockerfile preparan la publicación; no significan que exista un servicio desplegado.

Quedan por configurar los proyectos cloud, las credenciales, el origen de Vercel y el primer administrador real. Las pruebas CI utilizan PostgreSQL temporal, no tu proyecto Supabase. No se ha medido capacidad de usuarios concurrentes ni se ofrece un sistema de pagos, rutinas o entrenador.

Los commits son atómicos en español, con sufijos feat/test/docs según su propósito. Las funcionalidades se integran por PR a dev y después a main.
