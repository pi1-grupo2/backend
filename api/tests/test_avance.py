"""US-09 y US-10. El avance se guarda y el progreso cuenta solo lo ejecutado."""

from rest_framework import status

from api.tests.test_sobrecarga import BaseCarga


class RegistroDeAvanceTests(BaseCarga):
    def test_marcar_ejecutada_guarda_el_estado(self):
        gestion = self.crear_gestion(2, nombre="Reservar salón")

        respuesta = self.reprogramar(gestion, estado="EJECUTADA")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "EJECUTADA")
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "EJECUTADA")

    def test_posponer_guarda_la_nota(self):
        gestion = self.crear_gestion(2, nombre="Confirmar catering")
        nota = "esperando confirmación de salón"

        respuesta = self.reprogramar(gestion, estado="POSPUESTA", nota_posposicion=nota)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "POSPUESTA")
        self.assertEqual(respuesta.data["nota_posposicion"], nota)
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "POSPUESTA")
        self.assertEqual(gestion.nota_posposicion, nota)

    def test_posponer_sin_nota_no_borra_la_que_ya_estaba(self):
        gestion = self.crear_gestion(2)
        gestion.nota_posposicion = "esperando confirmación de salón"
        gestion.save()

        respuesta = self.reprogramar(gestion, estado="POSPUESTA")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        gestion.refresh_from_db()
        self.assertEqual(gestion.nota_posposicion, "esperando confirmación de salón")

    def test_marcar_ejecutada_conserva_la_nota(self):
        gestion = self.crear_gestion(2, estado="POSPUESTA")
        gestion.nota_posposicion = "esperando confirmación de salón"
        gestion.save()

        self.reprogramar(gestion, estado="EJECUTADA")

        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "EJECUTADA")
        self.assertEqual(gestion.nota_posposicion, "esperando confirmación de salón")

    def test_un_estado_desconocido_no_se_guarda(self):
        gestion = self.crear_gestion(2)

        respuesta = self.reprogramar(gestion, estado="HECHA")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "PENDIENTE")

    def test_la_gestion_de_otra_cuenta_responde_404(self):
        gestion = self.crear_gestion(2)
        self.autenticar(self.crear_organizador("pedro@correo.com"))

        respuesta = self.reprogramar(gestion, estado="EJECUTADA")

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "PENDIENTE")


class ProgresoTests(BaseCarga):
    def url(self):
        return f"/api/events/{self.evento.id}/progress/"

    def test_el_porcentaje_es_ejecutadas_sobre_el_total(self):
        self.crear_gestion(2, estado="EJECUTADA", nombre="Salón")
        self.crear_gestion(1, nombre="Catering")

        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["subtareas_ejecutadas"], 1)
        self.assertEqual(respuesta.data["total_subtareas"], 2)
        self.assertEqual(respuesta.data["progreso"], 50.0)

    def test_una_pospuesta_no_cuenta_como_ejecutada(self):
        self.crear_gestion(2, estado="POSPUESTA")
        self.crear_gestion(1, estado="EJECUTADA")

        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.data["subtareas_ejecutadas"], 1)
        self.assertEqual(respuesta.data["total_subtareas"], 2)
        self.assertEqual(respuesta.data["progreso"], 50.0)

    def test_sin_gestiones_el_progreso_es_cero(self):
        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_subtareas"], 0)
        self.assertEqual(respuesta.data["subtareas_ejecutadas"], 0)
        self.assertEqual(respuesta.data["progreso"], 0)

    def test_el_progreso_de_otro_organizador_responde_404(self):
        self.autenticar(self.crear_organizador("pedro@correo.com"))

        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_sesion_responde_401(self):
        self.client.credentials()

        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(respuesta.data["detail"], "Sesión inválida o expirada")
