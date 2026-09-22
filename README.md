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
| `DJANGO_SECRET_KEY` | Clave de firma de Django. En Render se genera sola |
| `DJANGO_DEBUG` | `true` en local, `false` en producción |
| `DJANGO_ALLOWED_HOSTS` | Dominios que puede servir la API. En Render se agrega solo |
| `CORS_ALLOWED_ORIGINS` | URLs del frontend autorizadas a llamar a la API |
| `DATABASE_URL` | Cadena de conexión de Supabase, usando el Session pooler |

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
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── docs/
│   └── modelo-de-datos.md
├── build.sh
├── render.yaml
├── requirements.txt
├── manage.py
└── .env.example

## Convenciones de trabajo
Commits en formato Conventional Commits: feat:, fix:, docs:, refactor:, test:, chore:
Ramas: feature/<descripcion>-<iniciales>
main está protegida. Nada entra sin pull request aprobado por otra persona del equipo
Los comentarios del PR se resuelven antes de fusionar


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
API --- Pendiente 
Frondtend --- Pendiente 
______________________________________________________________________________________________________________________________

## ENDPOINTS IMPLEMENTADOS SPRINT 1

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
API en producción	pendiente
Frontend	pendienteal organizador de eventos.

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
Health

Comprueba que la API y la conexión con la base de datos estén disponibles.

GET /api/health/
Eventos

Obtener todos los eventos:

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

ESTADO DEL BACKEND 

Sprint 1. Implementación inicial de los endpoints de negocio.

Actualmente están implementados:

Modelo de organizador
Modelo de evento
Modelo de subtarea logística
Creación y consulta de eventos
Creación y consulta de subtareas
Actualización y reprogramación de subtareas
Clasificación de subtareas por situación
Cálculo del progreso de un evento
Detección de conflictos de carga diaria
Migración inicial de la base de datos

La autenticación llega en el Sprint 2: hasta entonces se trabaja con usuario demo,
según lo permite el enunciado.
