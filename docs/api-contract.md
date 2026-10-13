# Contrato de integración con FastAPI

Todas las rutas reciben o devuelven JSON. Se usan nombres en español para mantener coherencia con el modelo. Las fechas tienen formato `YYYY-MM-DD`; pesos, cargas y volúmenes son números en kg; talla en metros. Las respuestas numéricas no deben serializarse como cadenas, aunque PostgreSQL use `NUMERIC`.

Este contrato define lo que consume el frontend. La implementación del backend debe validarlo con pruebas reales; las respuestas de navegador usadas en los tests son interceptaciones.

## Autenticación y autorización

| Método y ruta         | Solicitud                                                                     | Respuesta                                                |
| --------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| POST `/auth/register` | `{ "nombre": "Max", "correo": "max@example.com", "clave": "ejemplo-seguro" }` | 201, objeto Usuario                                      |
| POST `/auth/login`    | `{ "correo": "max@example.com", "clave": "ejemplo-seguro" }`                  | 200, `{ "access_token": "...", "token_type": "bearer" }` |
| GET `/me`             | Token                                                                         | 200, Usuario                                             |
| PATCH `/me`           | Perfil descrito abajo                                                         | 200, Usuario actualizado                                 |

El registro no inicia sesión automáticamente. El login recibe JSON; si se usa un formulario OAuth2 de FastAPI se debe adaptar explícitamente el endpoint o el servicio del frontend. Después del login, el frontend consulta `/me` con `Authorization: Bearer <token>`. Todas las demás rutas requieren el token. El backend obtiene el propietario del token y filtra consultas; ningún identificador enviado por la interfaz autoriza el acceso a datos ajenos.

Usuario:

```json
{
  "id": 8,
  "rol": "usuario",
  "activo": true,
  "nombre": "Max",
  "correo": "max@example.com",
  "edad": null,
  "talla_m": null,
  "objetivo": null,
  "perfil_completo": false
}
```

PATCH `/me`:

```json
{ "edad": 20, "talla_m": 1.75, "peso_kg": 80, "objetivo": "Ganar fuerza" }
```

El backend valida y guarda perfil + medición de peso en una transacción, con fecha actual de negocio (America/Lima). Marca `perfil_completo` solo después del guardado. Objetivos aceptados: Ganar fuerza, Ganar masa muscular, Mejorar condición física, Mantener actividad física. El backend aplica las restricciones de edad, talla y peso sin depender de la validación visual.

## Entrenamiento y mediciones

| Método y ruta      | Solicitud                                  | Respuesta                                                              |
| ------------------ | ------------------------------------------ | ---------------------------------------------------------------------- |
| GET `/ejercicios`  | Sin cuerpo                                 | Lista de `{ "id": 1, "nombre": "Press de banca", "unidad": "kg" }`     |
| POST `/sesiones`   | Sesión con registros                       | 201, sesión guardada con ID y volumen                                  |
| GET `/sesiones`    | Sin cuerpo                                 | Lista de sesiones de la cuenta; `[]` si no hay datos                   |
| POST `/mediciones` | `{ "fecha": "2026-10-10", "peso_kg": 80 }` | 201, `{ "id": 4, "fecha": "2026-10-10", "peso_kg": 80, "imc": 26.12 }` |

Sesión de respuesta (para crearla, se omiten `id` y `volumen_kg`):

```json
{
  "id": 9,
  "fecha": "2026-10-10",
  "registros": [{ "ejercicio_id": 1, "series": 3, "repeticiones": 8, "carga_kg": 32 }],
  "volumen_kg": 768
}
```

Una sesión contiene de 1 a 20 registros. Series: enteros de 1 a 20; repeticiones: enteros de 1 a 100. Carga: de 0 a 600 kg, con una decimal como máximo. Meta: de 0,1 a 600 kg, con una decimal como máximo. Edad: 18 a 120; talla: 0,50 a 2,50 m; peso: 20 a 400 kg. Estos límites son validaciones técnicas del proyecto, no recomendaciones de entrenamiento. Las fechas van desde 2000-01-01 hasta la fecha actual de negocio; no pueden ser futuras ni inexistentes. Edad sin decimales; talla con hasta dos decimales y peso con una. Nombres personales: 2–100 caracteres, letras Unicode, espacios, puntos, apóstrofes y guiones; correo hasta 254 y contraseña de registro 8–128 caracteres. Nombre de ejercicio: 2–80 caracteres. El backend valida también estas restricciones.

Cada registro contiene series con la misma carga y repeticiones. Una misma sesión puede contener varias filas del mismo ejercicio. Si falla una fila, el backend revierte toda la sesión. Volumen = suma de series × repeticiones × carga de los registros; IMC = peso / talla². El frontend real representa estos resultados y no repite sus fórmulas.

## Progreso

GET `/progreso?ejercicio_id=1&desde=2026-09-01&hasta=2026-10-10`. Los tres filtros son opcionales; extremos de fecha inclusivos. Rechazar un intervalo invertido. La última medición corresponde al perfil y no se restringe por los filtros del entrenamiento.

```json
{
  "total_sesiones": 1,
  "volumen_total_kg": 768,
  "carga_maxima_kg": 32,
  "ultima_medicion": { "id": 4, "fecha": "2026-10-10", "peso_kg": 80, "imc": 26.12 },
  "puntos": [{ "fecha": "2026-10-10", "carga_kg": 32, "volumen_kg": 768 }]
}
```

Una fila de `puntos` por fecha, ordenada de forma ascendente. Para varios registros en una fecha: carga máxima y volumen sumado. Con ejercicio filtrado, contar sesiones que contienen ese ejercicio y sumar solo sus registros. Sin registros: totales cero, `carga_maxima_kg: null`, `puntos: []`. Sin mediciones: `ultima_medicion: null`. No rellenar fechas ausentes. Las sesiones recientes del dashboard se consultan como historial general, independiente de estos filtros. El calendario de constancia también utiliza GET `/sesiones`: muestra el mes seleccionado de lunes a domingo y marca en verde las fechas con sesiones. Permite consultar meses anteriores y el detalle de cada día. No depende del filtro de ejercicio o fechas del gráfico de evolución. Varias sesiones el mismo día cuentan como un día; fechas sin registros no prueban ausencia de entrenamiento. Este endpoint debe devolver el historial completo de la cuenta para que el cálculo sea correcto; si se pagina en el backend, se necesitará un agregado de días o consultar todas las páginas del período.

## Metas y análisis

GET `/metas`: lista de `{ "id": 2, "ejercicio_id": 1, "carga_objetivo_kg": 50, "estado": "pendiente" }`. Estado: `pendiente` o `alcanzada`.

POST `/metas`: `{ "ejercicio_id": 1, "carga_objetivo_kg": 50 }`; devuelve la meta creada (201). Se admiten varias metas del mismo ejercicio; se selecciona una para analizar.

POST `/analisis`: `{ "ejercicio_id": 1, "meta_id": 2 }`. `meta_id` es opcional: sin meta, analizar tendencia sin estimar semanas hasta el objetivo. Validar que la meta pertenece a la cuenta y al ejercicio seleccionado.

```json
{
  "estado": "estimado",
  "mensaje": "La tendencia estimada es positiva.",
  "semanas_observadas": 8,
  "pendiente_kg_semana": 2,
  "siguiente_carga_kg": 48,
  "semanas_hasta_meta": 2,
  "historial": [
    { "semana": 0, "carga_kg": 32 },
    { "semana": 7, "carga_kg": 46 }
  ],
  "proyeccion": [
    { "semana": 7, "carga_kg": 46 },
    { "semana": 8, "carga_kg": 48 },
    { "semana": 9, "carga_kg": 50 }
  ]
}
```

El historial de este ejemplo está abreviado. `semana` representa intervalos de siete días desde la primera observación, empezando en cero; se conservan los saltos. Agrupar carga máxima semanal por cuenta y ejercicio. Al menos cuatro semanas distintas son necesarias. Entrenar LinearRegression en el backend y controlar datos no finitos.

| Estado                   | Comportamiento                                                           |
| ------------------------ | ------------------------------------------------------------------------ |
| `historial_insuficiente` | Sin proyección; indica cuántas semanas se observaron.                    |
| `meta_alcanzada`         | Informa cumplimiento; sin fecha futura de logro.                         |
| `sin_tendencia_positiva` | Informa tendencia nula o negativa; sin fecha de logro.                   |
| `estimado`               | Devuelve tendencia y proyección. Sin meta, `semanas_hasta_meta` es null. |

Para estados sin estimación: `siguiente_carga_kg` y `semanas_hasta_meta` son null; `proyeccion` es `[]`. `pendiente_kg_semana` puede ser null si no se ajusta el modelo. La interfaz distingue estos estados y no muestra una estimación anterior cuando una nueva solicitud falla.

## Roles y acceso

`rol` es `usuario` o `admin`, y `activo` es booleano. GET/PATCH `/me` deben devolver ambos. Por compatibilidad, una respuesta antigua sin rol se interpreta únicamente como usuario; un rol desconocido se rechaza. Las cuentas inactivas no pueden iniciar sesión ni realizar solicitudes autenticadas. FastAPI consulta el estado y rol actuales para cada operación protegida; no debe depender de permisos almacenados únicamente en un JWT de larga duración.

El registro público siempre crea `usuario`, sin aceptar un rol del cliente. Los endpoints `/admin/*` requieren `admin` en el servidor, con 403 para usuarios autenticados sin permiso. Los identificadores de usuario sirven como filtros administrativos y nunca sustituyen autorización. El administrador no puede desactivar su propia cuenta ni quitar su propio rol; el backend debe impedir además desactivar o degradar al último administrador activo, con una transacción que evite condiciones de carrera. Crear el primer administrador mediante un comando de configuración del backend, nunca desde el registro público.

Usuario: Inicio, Entrenamiento, Análisis IA y Configuración; perfil desde la cuenta. Administrador: resumen global, Usuarios, Entrenamientos, Ejercicios y Configuración; cuenta propia desde el mismo menú. La interfaz administrativa no ejecuta el modelo. El usuario de demostración no accede a operaciones administrativas del adaptador local. Los datos de demostración no acreditan seguridad ni persistencia real.

## Inicio del usuario

GET `/inicio` devuelve el resumen de la cuenta autenticada. No ejecuta ni entrena el modelo. Los totales no usan los filtros del gráfico, que siguen en `/progreso`.

```json
{
  "progreso": {
    "total_sesiones": 1,
    "volumen_total_kg": 768,
    "carga_maxima_kg": 32,
    "ultima_medicion": { "id": 4, "fecha": "2026-10-10", "peso_kg": 80, "imc": 26.12 },
    "puntos": [{ "fecha": "2026-10-10", "carga_kg": 32, "volumen_kg": 768 }]
  },
  "rendimiento": [
    {
      "ejercicio_id": 1,
      "nombre": "Press de banca",
      "sesiones": 1,
      "primera_carga_kg": 32,
      "ultima_carga_kg": 32,
      "mejor_carga_kg": 32,
      "variacion_porcentaje": 0
    }
  ],
  "metas": [
    {
      "id": 2,
      "ejercicio_id": 1,
      "ejercicio_nombre": "Press de banca",
      "carga_objetivo_kg": 50,
      "estado": "pendiente",
      "ultima_carga_kg": 32,
      "avance_porcentaje": 64
    }
  ],
  "ultimo_analisis": null,
  "recomendaciones": [
    {
      "titulo": "Construye un historial consistente",
      "mensaje": "Registra fecha, series, repeticiones y carga de tus sesiones reales.",
      "origen": "regla",
      "accion": "registro"
    }
  ]
}
```

`rendimiento` compara las cargas máximas del mismo ejercicio en la primera y última sesión, ordenadas por fecha e ID. `sesiones` cuenta sesiones distintas del ejercicio. `mejor_carga_kg` es el máximo de todo su historial. Variación = (última − primera) / primera × 100; null si no hay datos o la primera carga es cero. No comparar fuerza entre ejercicios diferentes. El avance de la meta es última carga / objetivo × 100, limitado a 0–100; null si no hay registros. El estado de cumplimiento de la meta se obtiene del historial validado en el backend y puede diferir del avance de la última sesión.

`ultimo_analisis`: null o `{ "ejercicio_nombre": "Press de banca", "fecha": "2026-10-10T15:00:00Z", "resultado": <objeto Prediction> }`. El backend guarda el resultado de POST `/analisis` para poder mostrarlo posteriormente. Es una referencia histórica con fecha, no un recálculo automático. `recomendaciones` es una lista con texto, `origen` (`regla` o `modelo`) y `accion` (`registro`, `perfil` o `analisis`). Las reglas deben basarse en el objetivo y los registros disponibles y declararse como tales. No generar una recomendación del modelo si no existe un análisis guardado.

## Administración

| Método y ruta                  | Solicitud o filtros                                                                                             | Respuesta                                                                                              |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| GET `/admin/resumen`           | Token de administrador                                                                                          | Resumen global                                                                                         |
| GET `/admin/usuarios`          | `q` hasta 100 caracteres; `rol`, `estado` (`activo`/`inactivo`), `pagina` entero ≥1                             | Página de usuarios                                                                                     |
| POST `/admin/usuarios`         | `{ "nombre": "Valeria Torres", "correo": "valeria@example.com", "clave": "temporal-segura", "rol": "usuario" }` | 201, Usuario; activo y perfil pendiente                                                                |
| GET `/admin/usuarios/{id}`     | ID válido                                                                                                       | `{ "usuario": <Usuario>, "progreso": <Progress>, "sesiones": [<TrainingSession>], "metas": [<Goal>] }` |
| PATCH `/admin/usuarios/{id}`   | Campos parciales: `nombre`, `correo`, `rol`, `activo`                                                           | 200, Usuario actualizado                                                                               |
| GET `/admin/sesiones`          | `usuario_id` opcional, `pagina` entero ≥1                                                                       | Página de sesiones administrativas                                                                     |
| DELETE `/admin/sesiones/{id}`  | ID de sesión                                                                                                    | 204, sin cuerpo                                                                                        |
| DELETE `/admin/metas/{id}`     | ID de meta                                                                                                      | 204, sin cuerpo                                                                                        |
| GET `/admin/ejercicios`        | Sin filtros                                                                                                     | Catálogo completo, incluidos inactivos                                                                 |
| POST `/admin/ejercicios`       | `{ "nombre": "Remo con barra", "unidad": "kg" }`                                                                | 201, Ejercicio activo                                                                                  |
| PATCH `/admin/ejercicios/{id}` | `nombre` y/o `activo`                                                                                           | 200, Ejercicio actualizado                                                                             |

Resumen: `{ "total_usuarios": 4, "usuarios_activos": 3, "total_sesiones": 8, "total_ejercicios": 4, "sesiones_recientes": [...] }`. Las cuentas incluyen ambos roles; ejercicios cuenta solo activos. `sesiones_recientes` contiene hasta cinco sesiones, ordenadas por fecha e ID descendentes.

Página: `{ "items": [...], "total": 8, "pagina": 1, "por_pagina": 10 }`. El backend usa 10 filas por página, valida `pagina` y devuelve el total del filtro. Una sesión administrativa añade `usuario_id` y `usuario_nombre` a la sesión normal. El detalle de usuario incluye las diez sesiones más recientes; la revisión paginada completa usa `/admin/sesiones?usuario_id=...`. Las metas se muestran sin ejecutar el análisis. El perfil corporal sigue siendo editable desde la cuenta personal del socio.

Ejercicio administrativo: `{ "id": 1, "nombre": "Press de banca", "unidad": "kg", "activo": true }`. `/ejercicios` devuelve solo los ejercicios habilitados para nuevas sesiones. Desactivar un ejercicio conserva su historial y metas; no debe borrarse mediante cascadas. Rechazar registros nuevos de ejercicios inactivos. Los correos deben ser únicos, sin distinguir mayúsculas. Normalizar nombres de ejercicios para evitar duplicados accidentales; 409 para conflictos. Hashear las contraseñas en el backend y no devolverlas ni registrarlas en logs.

La eliminación de una sesión revierte sus registros en una transacción y actualiza los agregados; conservar trazabilidad de actor, recurso y fecha en el backend. El frontend solicita confirmación antes de borrar sesiones/metas y de cambiar acceso o disponibilidad. Las eliminaciones no tienen una opción de deshacer en esta interfaz.

## Preferencias de interfaz

Tema (`oscuro`, `claro`, `sistema`) y animaciones se guardan en `localStorage`, separados por ID de cuenta y modo API/demo. No requieren nuevos endpoints ni se sincronizan entre dispositivos. No almacenan roles ni secretos. El tema predeterminado es azul noche. La preferencia de reducir movimiento del dispositivo tiene prioridad sobre activar animaciones en la plataforma.

## Errores y despliegue

Errores con `{"detail":"Mensaje comprensible"}` o validación Pydantic `{"detail":[{"loc":["body","campo"],"msg":"...","type":"..."}]}`. Usar 401 para sesión inválida, 403/404 para recursos no autorizados o no disponibles, 409 para conflictos y 422 para datos inválidos. No devolver detalles de SQL ni credenciales.

GET `/health` para comprobar disponibilidad. CORS debe permitir el origen del frontend, los métodos GET/POST/PATCH/DELETE/OPTIONS y los encabezados Authorization/Content-Type. En producción, frontend y API con HTTPS. PostgreSQL no se conecta desde React: únicamente FastAPI maneja SQLAlchemy, transacciones y credenciales.

La distribución usa un espaciado único adaptable; se retiró la preferencia `compacto`. Cualquier valor antiguo guardado para esa propiedad se ignora. Configuración tiene un único acceso en la navegación principal. La demostración de movimiento contiene elementos ilustrativos y no realiza consultas al modelo ni representa métricas reales.
