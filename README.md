# FitAnalytics AI · Backend

API para gestionar entrenamientos, calcular indicadores de progreso y estimar la evolución de cargas. Desarrollada con **Python, FastAPI, SQLAlchemy, PostgreSQL y scikit-learn**, con programación orientada a objetos y una arquitectura modular.

**[Explorar Swagger](https://gym-ai-backend-2ne5.onrender.com/docs)** · [Aplicación web](https://gym-frontend-beta-eight.vercel.app/) · [Frontend](https://github.com/Maxi-ING/Gym-Frontend)

## Funciones principales

- Cuentas, autenticación JWT, contraseñas con Argon2 y permisos de usuario y administrador.
- Perfil y mediciones corporales con IMC histórico.
- Catálogo de ejercicios y sesiones con detalle de series, repeticiones y cargas.
- Indicadores, rendimiento por ejercicio, metas y análisis guardados.
- Administración y auditoría de cambios, con validaciones y aislamiento de datos entre cuentas.

## Arquitectura y datos

Monolito modular organizado en **rutas → servicios → repositorios**. Los esquemas Pydantic validan entradas y salidas; SQLAlchemy mapea las entidades y Alembic versiona la base de datos.

Los objetos de dominio encapsulan los cálculos de IMC y volumen. El contrato abstracto `PredictorCarga` permite inyectar `PredictorLineal` y sustituirlo en pruebas, aplicando abstracción, herencia, composición y polimorfismo.

PostgreSQL conserva ocho tablas de negocio en el esquema `gym_app`, con claves foráneas, restricciones e índices. Las sesiones se guardan en una transacción: si falla un registro, se revierte la operación completa. Desactivar un ejercicio conserva su historial.

## Modelo predictivo

La regresión lineal compara el **mismo ejercicio y número de repeticiones**, utilizando máximos semanales y al menos cuatro semanas observadas. Evalúa el error con validación temporal y lo compara con repetir la última carga conocida.

Solo publica proyecciones si el historial y el error cumplen las reglas operativas: horizonte de meta de hasta doce semanas y cargas dentro de 0–600 kg. Cuando no puede estimar con suficiente fiabilidad, devuelve el motivo. Los mensajes se generan mediante reglas, sin agentes ni IA generativa. Las estimaciones son orientativas y no garantizan resultados deportivos.

## Ejecutar localmente

Requiere **Python 3.12** y **PostgreSQL**. Docker es opcional para iniciar la base local.

```bash
git clone https://github.com/Maxi-ING/GymAI-Backend.git
cd GymAI-Backend
python -m venv .venv
```

Activa el entorno con `.venv\Scripts\Activate.ps1` en PowerShell o `source .venv/bin/activate` en Linux/macOS. El comando `python` debe corresponder a Python 3.12.

```bash
python -m pip install -r requirements.txt
```

Copia `.env.example` como `.env`. Configura `DATABASE_URL`, un `JWT_SECRET` aleatorio propio de al menos 32 bytes y `CORS_ORIGINS` con el origen del frontend. Para usar PostgreSQL local con los valores del ejemplo:

```bash
docker compose up -d --wait
```

```bash
alembic upgrade head
python -m app.cli seed-catalog
uvicorn app.main:app --reload
```

Abre [Swagger local](http://localhost:8000/docs) o [el estado de conexión](http://localhost:8000/health). Para crear un administrador local:

```bash
python -m app.cli create-admin --nombre "Administrador" --correo "admin@example.com"
```

El comando solicita la contraseña de forma interactiva. El frontend local debe usar `VITE_API_URL=http://localhost:8000`.

## Verificación

```bash
python -m pip install -r requirements-dev.txt
ruff check app migrations tests scripts
ruff format --check app migrations tests scripts
pytest -q
```

Las pruebas de integración requieren `TEST_DATABASE_URL` apuntando a una base separada cuyo nombre termine en `_test`, con las migraciones aplicadas; sus datos se eliminan durante las pruebas. Sin esa variable, se ejecutan las pruebas unitarias y se omiten las de integración.

GitHub Actions verifica reglas, permisos, transacciones, migraciones y recorridos del frontend con la API y PostgreSQL reales en un entorno de pruebas.

## Despliegue y documentación

La API se aloja en **Render**, PostgreSQL en **Supabase** y el frontend en **Vercel**. Solo el backend se conecta directamente con la base de datos.

- [Contrato de la API](docs/api-contract.md).
- [Base de datos y demostración](docs/base-datos.md).
- [Configuración del despliegue](docs/despliegue.md).
- [Consultas de demostración](docs/consultas-demostracion.sql).

El trabajo se integra mediante ramas `feature/*` → `dev` → `main` y commits atómicos en español.
