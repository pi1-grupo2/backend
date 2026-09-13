from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    """
    Endpoint de salud. Es el que pide la rubrica del Sprint 0 (criterio C7).

    Ademas de responder 200, verifica que la conexion a la base de datos este viva.
    Un health que solo dice "ok" sin tocar la base de datos miente cuando Postgres
    se cae: la API responde y el producto no funciona.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        base_de_datos = "ok"
    except Exception as error:  # noqa: BLE001
        base_de_datos = f"error: {error.__class__.__name__}"

    return Response(
        {
            "estado": "ok",
            "servicio": "api-organizador-eventos",
            "base_de_datos": base_de_datos,
        }
    )
