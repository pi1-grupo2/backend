"""Configuración exclusiva de QA: nunca utiliza PostgreSQL ni archivos de datos."""

import os

# Evita incluso interpretar DATABASE_URL del entorno o del .env.
os.environ["DATABASE_URL"] = ""

from config.settings import *  # noqa: F403,E402

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}
