# Backend · Organizador de Eventos Independientes

API del Miniproyecto 1 de Proyecto Integrador I (750018C). Grupo 2, Universidad del Valle,
semestre 2026-2.

El producto permite a un organizador de eventos independiente planificar la logística de sus
eventos, ver qué gestiones son urgentes hoy, reprogramar cuando un proveedor se retrasa y seguir
el avance de la preparación.

## Stack

- Django 5.2 y Django REST Framework
- PostgreSQL en Supabase
- Desplegado en Render
- WhiteNoise para archivos estáticos
- Gunicorn para ejecución en producción

## Requisitos

- Python 3.11 o superior para el entorno del equipo/producción
- La cadena de conexión de la base de datos del equipo. Se pide por el canal oficial, nunca se
  comparte por el repositorio

## Arranque local

```bash
git clone git@github.com:pi1-grupo2/backend.git
cd backend

python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # y llenar los valores
python manage.py migrate
python manage.py runserver

## Verificar que quedó arriba

```bash
curl http://127.0.0.1:8000/api/health/
```

Respuesta esperada:

```json
{
  "estado": "ok",
  "servicio": "api-organizador-eventos",
  "base_de_datos": "ok"
}
```

El endpoint no solo responde, también consulta la base de datos. Si `base_de_datos` dice `error`,
la API está corriendo pero no alcanza Postgres: revisar `DATABASE_URL` en el `.env`.

Sin `DATABASE_URL` el proyecto arranca con SQLite. Sirve para comprobar que todo corre sin tener
credenciales, pero no es el entorno del equipo.

## Variables de entorno

| Variable | Para qué sirve |
| --- | --- |
| `DJANGO_SECRET_KEY` | Clave secreta utilizada por Django para la firma criptográfica. Debe mantenerse privada y configurarse en Render para producción. |
| `DJANGO_DEBUG` | Controla el modo de depuración: `true` en desarrollo local y `false` en producción. |
| `DJANGO_ALLOWED_HOSTS` | Define los dominios autorizados para acceder al backend, incluyendo el dominio de Render. |
| `CORS_ALLOWED_ORIGINS` | Define los orígenes del frontend autorizados para realizar solicitudes a la API, incluyendo Vercel y el entorno local. |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL en Supabase mediante el Session Pooler. |

El archivo `.env` está en `.gitignore` y no se sube nunca. Una credencial que entra al historial de
Git queda visible aunque después se borre del archivo.

## Estructura

backend/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api/
│   ├── migrations/
│   ├── tests/
│   │   ├── settings_qa.py
│   │   └── test_subtareas_qa.py
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── docs/
│   ├── qa/
│   │   ├── ejecutar_sin_migraciones.py
│   │   ├── subtareas_reporte.md
│   │   ├── subtareas_resultados.txt
│   │   ├── subtareas_regresion_resultados.txt
│   │   └── subtareas_suite_corregida_resultados.txt
│   └── modelo-de-datos.md
├── AGENTS.md
├── build.sh
├── render.yaml
├── requirements.txt
├── manage.py
└── .env.example

## Convenciones de trabajo

- **Commits:** utilizar el formato Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).
- **Ramas de trabajo:** crear ramas independientes a partir de `main`. Se recomienda el formato `feature/<descripcion>-<iniciales>`; también se utilizan ramas individuales como `YoselinC`.
- **Rama principal:** `main` está protegida. Los cambios deben integrarse mediante Pull Request (PR) aprobado por otra persona del equipo.
- **Pull Requests:** incluir un título descriptivo, resumen de los cambios realizados, pruebas ejecutadas y evidencias cuando corresponda.
- **Revisión de código:** resolver los comentarios y observaciones del PR antes de fusionarlo con `main`.
- **Pruebas QA:** ejecutar las pruebas automatizadas correspondientes antes de solicitar la aprobación del PR.
- **Seguridad:** no subir contraseñas, tokens, credenciales ni archivos `.env` al repositorio.
- **Base de datos:** realizar las pruebas automatizadas en entornos aislados, evitando modificar los datos reales de Supabase.
- **Documentación:** actualizar el `README.md` y las evidencias de QA cuando se incorporen cambios relevantes.
- **Integración:** fusionar los cambios con `main` únicamente después de la revisión y aprobación correspondiente.


## Despliegue
El proyecto está preparado para desplegarse como Web Service en Render.

El archivo render.yaml define:

Servicio web de Python
Gunicorn como servidor de producción
WhiteNoise para archivos estáticos
Health check mediante /api/health/
Variables de entorno para producción
Conexión a PostgreSQL mediante DATABASE_URL

El script build.sh instala las dependencias, genera los archivos estáticos y ejecuta las
migraciones de Django durante el proceso de construcción.

URL 
API --- https://pi1-grupo2-api.onrender.com/api/docs/
Frondtend --- https://pi1-grupo2-frontend.vercel.app/login
______________________________________________________________________________________________________________________________

## ENDPOINTS IMPLEMENTADOS 
API docuementada y completa: https://pi1-grupo2-frontend.vercel.app/login

RESUMEN

GET  /api/health/
GET  /api/events/
POST /api/events/
GET  /api/events/{id}/subtasks/
POST /api/events/{id}/subtasks/
PATCH /api/events/{id}/subtasks/{subtask_id}/
GET  /api/events/{id}/progress/
GET  /api/events/{id}/conflicts/

El archivo .env está en .gitignore y no se sube nunca. Una credencial que entra al historial de
Git queda visible aunque después se borre del archivo.

Modelo de datos

Actualmente la API implementa tres entidades principales:

Organizador

Representa l proyecto está preparado para desplegarse como Web Service en Render.

El archivo render.yaml define:

Servicio web de Python
Gunicorn como servidor de producción
WhiteNoise para archivos estáticos
Health check mediante /api/health/
Variables de entorno para producción
Conexión a PostgreSQL mediante DATABASE_URL

El script build.sh instala las dependencias, genera los archivos estáticos y ejecuta las
migraciones de Django durante el proceso de construcción.

Entorno	URL
API https://pi1-grupo2-api.onrender.com/api/docs/
Frontend https://pi1-grupo2-frontend.vercel.app/login.

Campos principales:

id
nombre
identidad_externa
limite_diario_horas
creado_en

El límite diario de horas se utiliza para detectar conflictos de carga logística.

Evento

Representa un evento organizado por un organizador.

Campos principales:

id
organizador
nombre
tipo
cliente_contacto
fecha_hora_evento
lugar
plazo_limite
creado_en
actualizado_en

Tipos de evento disponibles:

boda
social
corporativo
cumpleanos
otro
Subtarea logística

Representa una gestión necesaria para preparar un evento.

Campos principales:

id
evento
nombre
fecha_objetivo
horas_estimadas
estado
nota_posposicion
creado_en
actualizado_en

Estados disponibles:

PENDIENTE
EJECUTADA
POSPUESTA

La API también calcula la situación de una subtarea:

VENCIDA
PARA_HOY
PROXIMA
EJECUTADA
Endpoints

Salvo health y login, todas las rutas exigen el encabezado `Authorization: Bearer <token>`.
Cada organizador solo ve y modifica sus propios eventos.

Login

POST /api/auth/login/

{
  "correo": "natalia@demo.com",
  "password": "EventFlow2026"
}

La respuesta incluye `token`, `expira_en` y los datos del organizador, sin la contraseña.
La sesión dura 8 horas. Si el token vence o no es válido, la API responde 401 y no entrega eventos.
La cuenta de demostración es Natalia, correo `natalia@demo.com`, contraseña `EventFlow2026`.

Consultar la sesión actual:

GET /api/auth/sesion/

Cerrar la sesión:

DELETE /api/auth/sesion/

Health

Comprueba que la API y la conexión con la base de datos estén disponibles.

GET /api/health/
Eventos

Obtener los eventos del organizador autenticado:

GET /api/events/

Crear un evento:

POST /api/events/

Ejemplo:

{
  "organizador": 1,
  "nombre": "Boda de Ana y Carlos",
  "tipo": "boda",
  "cliente_contacto": "Ana - 3001234567",
  "fecha_hora_evento": "2026-10-15T18:00:00Z",
  "lugar": "Cali",
  "plazo_limite": "2026-10-10"
}
Subtareas de un evento

Consultar las subtareas de un evento:

GET /api/events/{evento_id}/subtasks/

Crear una subtarea:

POST /api/events/{evento_id}/subtasks/

Ejemplo:

{
  "nombre": "Reservar salón",
  "fecha_objetivo": "2026-09-25",
  "horas_estimadas": 2.0,
  "estado": "PENDIENTE"
}

La API asigna automáticamente la subtarea al evento indicado en la URL.

Actualizar una subtarea

Permite cambiar parcialmente los datos de una subtarea, incluyendo su estado,
fecha objetivo y nota de posposición.

PATCH /api/events/{evento_id}/subtasks/{subtarea_id}/

Ejemplo para marcar una subtarea como ejecutada:

{
  "estado": "EJECUTADA"
}

Ejemplo para reprogramar una subtarea:

{
  "fecha_objetivo": "2026-09-26",
  "estado": "POSPUESTA",
  "nota_posposicion": "Reprogramada por retraso del proveedor."
}
Progreso de un evento

Calcula el porcentaje de subtareas ejecutadas respecto al total de subtareas del evento.

GET /api/events/{evento_id}/progress/

Ejemplo de respuesta:

{
  "evento": 1,
  "total_subtareas": 4,
  "subtareas_ejecutadas": 2,
  "progreso": 50.0
}
Conflictos de carga

Detecta fechas en las que las horas planificadas de las subtareas pendientes o pospuestas
superan el límite diario de horas del organizador.

GET /api/events/{evento_id}/conflicts/

Ejemplo de respuesta:

{
  "evento": 1,
  "tiene_conflictos": true,
  "conflictos": [
    {
      "fecha": "2026-09-25",
      "horas_planificadas": 7.0,
      "limite_diario_horas": 6.0,
      "exceso_horas": 1.0,
      "subtareas": [
        {
          "id": 2,
          "nombre": "Enviar invitaciones",
          "horas_estimadas": 3.0,
          "estado": "PENDIENTE"
        }
      ]
    }
  ]
}

Las subtareas en estado EJECUTADA no se incluyen en el cálculo de conflictos

##fin de explicación de endpoinst implementados en sprint 1 

________________________________________________________________________________________________________________________

## ESTADO DEL BACKEND

### Sprint 1 — Implementación inicial de los endpoints de negocio

Se implementaron las funcionalidades principales para la gestión de eventos y subtareas logísticas:

- Modelo de organizador.
- Modelo de evento.
- Modelo de subtarea logística.
- Creación, consulta y actualización de eventos.
- Creación, consulta y actualización de subtareas.
- Reprogramación de subtareas.
- Clasificación de subtareas según su situación.
- Cálculo del progreso de los eventos.
- Detección de conflictos de carga diaria.
- Migración inicial de la base de datos PostgreSQL en Supabase.

### Sprint 2 — Autenticación y protección de rutas

Se incorporó la autenticación de organizadores mediante correo electrónico y contraseña.

- Registro de organizadores.
- Inicio de sesión y generación de token.
- Validación de sesión mediante `Authorization: Bearer <token>`.
- Protección de los endpoints de negocio.
- Restricción de acceso a los eventos y subtareas pertenecientes a cada organizador.
- Manejo de sesiones inválidas o expiradas.

Salvo los endpoints de health, login y registro, las rutas protegidas requieren autenticación.

| Situación | Código HTTP | Respuesta |
| --- | --- | --- |
| Token válido | Según la operación | Permite acceder a los recursos autorizados. |
| Token ausente, inválido o expirado | 401 | `{ "detail": "Sesión inválida o expirada" }` |
| Evento o subtarea de otro organizador | 404 | No permite acceder al recurso. |

### Sprint 3 — Planificación, reprogramación y conflictos

Se implementaron funcionalidades para gestionar la carga de trabajo de los organizadores:

- Actualización y reprogramación de subtareas.
- Validación de horas estimadas y fechas.
- Detección de sobrecarga diaria.
- Sugerencias de fechas alternativas.
- Reducción de horas para resolver conflictos.
- Confirmación explícita de operaciones que generan sobrecarga.
- Validación del límite máximo de 24 horas por día.

Las operaciones que generan conflictos devuelven respuestas estructuradas para que el frontend pueda mostrar mensajes, alertas y opciones de resolución.

### Sprint 4 — Estado de las gestiones y progreso

#### Cambiar el estado — `PATCH /api/events/{evento_id}/subtasks/{subtarea_id}/`

Permite registrar el avance de una gestión logística (US-09) mediante el endpoint de actualización existente.

**Marcar una gestión como ejecutada:**

```json
{
  "estado": "EJECUTADA"
}
```

**Posponer una gestión con nota opcional:**

```json
{
  "estado": "POSPUESTA",
  "nota_posposicion": "Esperando confirmación del salón"
}
```

| Caso | Código HTTP | Resultado |
| --- | --- | --- |
| Estado `EJECUTADA` o `POSPUESTA` | 200 | Devuelve la gestión actualizada. Si no se envía una nota, conserva la existente. |
| Estado distinto de `PENDIENTE`, `EJECUTADA` o `POSPUESTA` | 400 | Rechaza la actualización e informa el error en `estado`. |
| Sin sesión válida | 401 | Sesión inválida o expirada. |
| Evento o subtarea de otra cuenta | 404 | No permite modificar el recurso. |

**Reglas de negocio:**

- Una gestión ejecutada deja de sumar horas a la carga diaria.
- Una gestión pospuesta continúa sumando horas y conserva su fecha hasta que sea reprogramada.
- El estado de las gestiones se utiliza para calcular el progreso del evento.

#### Progreso — `GET /api/events/{evento_id}/progress/`

Calcula el porcentaje de gestiones ejecutadas respecto al total del evento (US-10).

El porcentaje se calcula en cada consulta y no se almacena como un valor independiente.

**Ejemplo de respuesta:**

```json
{
  "evento": 1,
  "nombre": "Boda de Ana",
  "total_subtareas": 2,
  "subtareas_ejecutadas": 1,
  "progreso": 50.0
}
```

**Reglas de negocio:**

- Las gestiones `EJECUTADA` cuentan para el progreso.
- Las gestiones `PENDIENTE` y `POSPUESTA` no cuentan como ejecutadas.
- Si el evento no tiene gestiones, `progreso` es `0`.

| Caso | Código HTTP |
| --- | --- |
| Evento perteneciente al organizador autenticado | 200 |
| Sin sesión válida | 401 |
| Evento inexistente o perteneciente a otra cuenta | 404 |

### Avisos de sobrecarga y gestión del límite diario

Como resultado de la retroalimentación del Sprint 3, se ampliaron las validaciones de sobrecarga para detectar conflictos al crear gestiones y al modificar el límite diario del organizador.

#### Consultar días con sobrecarga — `GET /api/organizador/sobrecarga/`

Devuelve los días desde la fecha actual cuya carga planificada supera el límite diario del organizador.

- Considera las gestiones de todos los eventos del organizador.
- Excluye las gestiones ejecutadas.
- Permite mostrar alertas en Configuración y en la vista `/hoy`.
- Acepta el parámetro opcional `?limite=4` para evaluar otro límite sin guardarlo.

**Ejemplo de respuesta:**

```json
{
  "limite_diario_horas": "6.0",
  "tiene_sobrecarga": true,
  "dias": [
    {
      "fecha": "2026-10-20",
      "horas_planificadas": "8.0",
      "limite_diario_horas": "6.0",
      "exceso_horas": "2.0",
      "gestiones": [
        {
          "id": 12,
          "evento": 3,
          "evento_nombre": "Boda de Ana",
          "nombre": "Catering",
          "horas_estimadas": "5.0",
          "estado": "PENDIENTE",
          "fecha_sugerida": "2026-10-21",
          "horas_sugeridas": "3.0"
        }
      ]
    }
  ]
}
```

**Interpretación de las sugerencias:**

- `fecha_sugerida`: primer día en el que la gestión puede programarse completamente sin superar el límite.
- `horas_sugeridas`: cantidad de horas que permitiría mantener la gestión en el mismo día sin exceder el límite.
- `horas_sugeridas` puede ser `null` cuando reducir únicamente esa gestión no permite resolver la sobrecarga.

#### Actualizar el límite diario — `PATCH` o `PUT /api/organizador/`

Permite modificar el límite de horas diarias y evaluar las consecuencias sobre la planificación existente.

| Caso | Código HTTP | Resultado |
| --- | --- | --- |
| Reducir el límite y generar sobrecarga | 409 | Devuelve `codigo: sobrecarga_por_limite`, `detail`, `limite_actual` y `dias`. No guarda el cambio. |
| Confirmar la sobrecarga mediante `"confirmar_sobrecarga": true` | 200 | Guarda el límite y devuelve `dias_sobrecargados`. |
| Aumentar el límite o reducirlo sin generar conflictos | 200 | Guarda el cambio y devuelve los días que continúen sobrecargados, si existen. |

#### Crear una gestión — `POST /api/events/{evento_id}/subtasks/`

La creación de subtareas incorpora validaciones de carga diaria.

| Caso | Código HTTP | Resultado |
| --- | --- | --- |
| Creación sin conflictos | 201 | Crea la gestión y devuelve `carga_del_dia`. |
| Creación que supera el límite diario | 409 | Devuelve `sobrecarga_diaria` y sugerencias de resolución. No crea la gestión. |
| Confirmación con `"confirmar_sobrecarga": true` | 201 | Permite crear la gestión aceptando la sobrecarga. |
| Carga superior a 24 horas en el día | 400 | Devuelve `dia_excedido` y rechaza la operación. |

### QA — Seguridad, pruebas automatizadas y regresión

Se realizaron pruebas de aseguramiento de calidad sobre los endpoints del backend, con especial atención a la autorización de las operaciones sobre subtareas.

#### Hallazgo de seguridad

Se identificó que una solicitud `PATCH` podía intentar modificar el campo `evento` de una subtarea existente para asociarla con un evento perteneciente a otro organizador.

Esto representaba un riesgo para la autorización y la integridad de los datos.

#### Corrección implementada

Se incorporó la validación `validate_evento` en `api/serializers.py`.

La corrección:

- Impide cambiar el evento asociado a una subtarea existente.
- Evita la reasignación de subtareas mediante solicitudes de actualización.
- Conserva el funcionamiento de la creación de subtareas.
- Refuerza el aislamiento de los datos entre organizadores.

#### Pruebas de regresión

Se incorporaron pruebas automatizadas en:

`api/tests/test_subtareas_qa.py`

También se agregó una configuración de pruebas aislada:

`api/tests/settings_qa.py`

Y un ejecutor de QA:

`docs/qa/ejecutar_sin_migraciones.py`

Este entorno utiliza SQLite en memoria para ejecutar las pruebas sin modificar la base de datos real de Supabase.

**Comando de ejecución:**

```bash
.venv/bin/python docs/qa/ejecutar_sin_migraciones.py api.tests
```

#### Resultados de QA

| Validación | Resultado |
| --- | --- |
| Pruebas específicas de subtareas | 11/11 aprobadas |
| Suite completa del backend | 138/138 aprobadas |
| Fallos reportados | 0 |
| Base de datos de pruebas | SQLite en memoria |
| Modificaciones sobre Supabase durante la suite QA | Ninguna |
| Corrección de autorización | Implementada y probada localmente |

**Evidencias disponibles:**

- `docs/qa/subtareas_reporte.md`
- `docs/qa/subtareas_resultados.txt`
- `docs/qa/subtareas_regresion_resultados.txt`
- `docs/qa/subtareas_suite_corregida_resultados.txt`

### Estado general

El backend cuenta con las funcionalidades de eventos, subtareas, autenticación, planificación, reprogramación, control de sobrecarga y seguimiento del progreso desarrolladas durante los Sprints 1 al 4.

La corrección de seguridad y las pruebas de regresión se encuentran implementadas y validadas localmente.

**Pendiente de cierre:**

- Revisión y aprobación del Pull Request.
- Integración de los cambios a `main`.
- Validación posterior al despliegue en Render.
- Limpieza de los registros temporales utilizados en las pruebas manuales, cuando corresponda.
