"""Sprint 4: al posponer, la API sugiere el día más cercano donde la gestión cabe."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

from api.serializers import POSPONER_EJECUTADA

from .test_sobrecarga import BaseCarga


class SugerenciaPosponerTests(BaseCarga):
    def sugerencia(self, gestion):
        return self.client.get(
            f"/api/events/{gestion.evento_id}/subtasks/{gestion.id}/sugerencia-posponer/"
        )

    def test_sugiere_el_dia_siguiente_si_tiene_cupo(self):
        gestion = self.crear_gestion(2)

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["fecha_sugerida"], self.dia_x + timedelta(days=1))
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("2.0"))
        self.assertEqual(respuesta.data["limite_diario_horas"], Decimal("6.0"))
        self.assertEqual(respuesta.data["busqueda_desde"], self.dia_x + timedelta(days=1))

    def test_salta_los_dias_que_quedarian_por_encima_del_limite(self):
        gestion = self.crear_gestion(2)
        self.crear_gestion(5, fecha=self.dia_x + timedelta(days=1))
        self.crear_gestion(6, fecha=self.dia_x + timedelta(days=2))

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.data["fecha_sugerida"], self.dia_x + timedelta(days=3))

    def test_un_dia_que_queda_justo_en_el_limite_sirve(self):
        gestion = self.crear_gestion(2)
        self.crear_gestion(4, fecha=self.dia_x + timedelta(days=1))

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.data["fecha_sugerida"], self.dia_x + timedelta(days=1))
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("6.0"))

    def test_cuenta_las_gestiones_de_otros_eventos_del_organizador(self):
        otro_evento = self.crear_evento(self.organizador, "Cumpleaños")
        gestion = self.crear_gestion(2)
        self.crear_gestion(5, fecha=self.dia_x + timedelta(days=1), evento=otro_evento)

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.data["fecha_sugerida"], self.dia_x + timedelta(days=2))

    def test_no_cuenta_las_ejecutadas_de_ese_dia(self):
        gestion = self.crear_gestion(2)
        self.crear_gestion(5, fecha=self.dia_x + timedelta(days=1), estado="EJECUTADA")

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.data["fecha_sugerida"], self.dia_x + timedelta(days=1))

    def test_una_vencida_busca_desde_hoy(self):
        gestion = self.crear_gestion(2, fecha=self.hoy - timedelta(days=3))

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.data["fecha_sugerida"], self.hoy)
        self.assertEqual(respuesta.data["busqueda_desde"], self.hoy)

    def test_sin_cupo_antes_del_evento_no_sugiere_nada(self):
        fecha_evento = timezone.now() + timedelta(days=2)
        self.evento.fecha_hora_evento = fecha_evento
        self.evento.plazo_limite = fecha_evento.date()
        self.evento.save()
        gestion = self.crear_gestion(2, fecha=self.hoy)
        self.crear_gestion(6, fecha=self.hoy + timedelta(days=1))
        self.crear_gestion(5, fecha=self.hoy + timedelta(days=2))

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data["fecha_sugerida"])
        self.assertIsNone(respuesta.data["horas_planificadas"])

    def test_una_ejecutada_no_tiene_sugerencia(self):
        gestion = self.crear_gestion(2, estado="EJECUTADA")

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["codigo"], "gestion_ejecutada")
        self.assertEqual(respuesta.data["detail"], POSPONER_EJECUTADA)

    def test_consultar_la_sugerencia_no_cambia_la_gestion(self):
        gestion = self.crear_gestion(2)

        self.sugerencia(gestion)

        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "PENDIENTE")
        self.assertEqual(gestion.fecha_objetivo, self.dia_x)

    def test_la_gestion_de_otra_cuenta_responde_404(self):
        gestion = self.crear_gestion(2)
        self.autenticar(self.crear_organizador("pedro@correo.com"))

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_sesion_responde_401(self):
        gestion = self.crear_gestion(2)
        self.client.credentials()

        respuesta = self.sugerencia(gestion)

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class SugerenciaEnElConflictoAlPosponerTests(BaseCarga):
    def test_el_409_al_posponer_no_sugiere_un_dia_anterior_a_la_fecha_actual(self):
        # Hoy está libre, pero posponer a hoy sería adelantar la gestión.
        gestion = self.crear_gestion(2)
        self.crear_gestion(5, fecha=self.otro_dia)

        respuesta = self.reprogramar(gestion, estado="POSPUESTA", fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertGreater(respuesta.data["fecha_sugerida"], self.dia_x)
        self.assertNotEqual(respuesta.data["fecha_sugerida"], self.otro_dia)

    def test_el_409_al_reprogramar_sigue_sugiriendo_desde_hoy(self):
        gestion = self.crear_gestion(2)
        self.crear_gestion(5, fecha=self.otro_dia)

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["fecha_sugerida"], self.hoy)
