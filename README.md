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

## Requisitos

- Python 3.11 o superior
- La cadena de conexión de la base de datos del equipo. Se pide por el canal oficial, nunca se
  comparte por el repositorio

## Arranque local

```bash
git clone https://github.com/pi1-grupo2/backend.git
cd backend

python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # y llenar los valores
python manage.py migrate
python manage.py runserver
```

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
|---|---|
| `DJANGO_SECRET_KEY` | Clave de firma de Django. En Render se genera sola |
| `DJANGO_DEBUG` | `true` en local, `false` en producción |
| `DJANGO_ALLOWED_HOSTS` | Dominios que puede servir la API. En Render se agrega solo |
| `CORS_ALLOWED_ORIGINS` | URLs del frontend autorizadas a llamar a la API |
| `DATABASE_URL` | Cadena de conexión de Supabase, usando el Session pooler |

El archivo `.env` está en `.gitignore` y no se sube nunca. Una credencial que entra al historial de
Git queda visible aunque después se borre del archivo.

## Estructura
backend/
├── config/ configuración del proyecto (settings, urls, wsgi)
├── api/ aplicación de la API
│ ├── urls.py
│ └── views.py /api/health/
├── build.sh lo ejecuta Render en cada despliegue
├── render.yaml definición del servicio en Render
└── .env.example plantilla de variables, sin valores


## Convenciones de trabajo

- Commits en formato Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Ramas: `feature/<descripcion>-<iniciales>`
- `main` está protegida. Nada entra sin pull request aprobado por otra persona del equipo
- Los comentarios del PR se resuelven antes de fusionar

## Despliegue

| Entorno | URL |
|---|---|
| API en producción | pendiente |
| Frontend | pendiente |

## Estado

Sprint 0. Base técnica operativa (TS-01) y modelo de datos (TS-02).

Los endpoints de negocio entran desde el Sprint 1. La autenticación llega en el Sprint 2: hasta
entonces se trabaja con usuario demo, según lo permite el enunciado.