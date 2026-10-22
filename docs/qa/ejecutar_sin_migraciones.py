"""Ejecutor QA aislado: crea esquema en memoria sin ejecutar migraciones.

Uso: .venv/bin/python docs/qa/ejecutar_sin_migraciones.py api.tests
"""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["DJANGO_SETTINGS_MODULE"] = "api.tests.settings_qa"

import django

django.setup()

from django.apps import apps
from django.db import connections
from django.test.runner import DiscoverRunner

from api.models import Organizador


class EjecutorSinMigraciones(DiscoverRunner):
    def setup_databases(self, **kwargs):
        conexion = connections["default"]
        if conexion.vendor != "sqlite" or conexion.settings_dict["NAME"] != ":memory:":
            raise RuntimeError("QA requiere exclusivamente SQLite en memoria.")
        print("QA: SQLite :memory:; esquema desde modelos; sin ejecutar migraciones.", flush=True)
        with conexion.schema_editor() as editor:
            for modelo in apps.get_models():
                editor.create_model(modelo)
        # Dato necesario para la prueba existente de correo demo duplicado.
        # No se importa ni ejecuta ninguna migración de datos.
        Organizador.objects.create(
            nombre="Demo QA",
            identidad_externa="demo",
            correo="natalia@demo.com",
            password="!",
        )
        return []

    def teardown_databases(self, old_config, **kwargs):
        connections.close_all()


if __name__ == "__main__":
    ejecutor = EjecutorSinMigraciones(verbosity=2, interactive=False, failfast=True)
    sys.exit(bool(ejecutor.run_tests(sys.argv[1:] or ["api.tests"])))
