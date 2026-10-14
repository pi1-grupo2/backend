"""Forma de los errores de la API."""

from unittest import mock

from rest_framework import status

from api.errores import MENSAJE_ERROR_INTERNO

from .test_sobrecarga import BaseCarga


class ErrorInesperadoTests(BaseCarga):
    def test_un_error_inesperado_responde_json_sin_detalle_tecnico(self):
        # Se fuerza una falla dentro de la vista de progreso.
        with mock.patch("api.views.SubtareaLogistica.objects.filter", side_effect=RuntimeError("fallo")), \
                self.assertLogs("api.errores", level="ERROR"):
            respuesta = self.client.get(f"/api/events/{self.evento.id}/progress/")

        self.assertEqual(respuesta.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(respuesta.data["codigo"], "error_interno")
        self.assertEqual(respuesta.data["detail"], MENSAJE_ERROR_INTERNO)
        self.assertNotIn("fallo", str(respuesta.data))

    def test_los_errores_conocidos_de_drf_no_cambian(self):
        respuesta = self.client.delete(f"/api/events/{self.evento.id}/progress/")

        self.assertEqual(respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn("detail", respuesta.data)
