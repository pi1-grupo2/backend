"""Manejo de errores común a toda la API.

DRF ya responde en JSON los errores que conoce (datos inválidos, sesión ausente,
método no permitido). Un error inesperado en el código, en cambio, llega a Django
y sale como una página HTML con código 500 que el frontend no sabe leer.
Este manejador lo convierte en la misma forma que usan los demás errores.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

MENSAJE_ERROR_INTERNO = "Ocurrió un error inesperado. Intenta de nuevo en unos minutos."


def manejar_excepcion(exc, context):
    respuesta = exception_handler(exc, context)
    if respuesta is not None:
        return respuesta

    # El detalle técnico va al log del servidor, nunca a la respuesta:
    # al usuario no le sirve y a un atacante sí.
    vista = context.get("view")
    logger.exception("Error no controlado en %s", vista.__class__.__name__ if vista else "la API")
    return Response(
        {"codigo": "error_interno", "detail": MENSAJE_ERROR_INTERNO},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
