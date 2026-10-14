"""Sprint 4: registrar una gestión como ejecutada o pospuesta."""

from datetime import timedelta
from decimal import Decimal

from rest_framework import status

from api.models import SubtareaLogistica
from api.serializers import (
    ESTADO_INVALIDO,
    POSPONER_EJECUTADA,
    POSPONER_FECHA_ANTERIOR,
)

from .test_sobrecarga import BaseCarga


class BaseEstado(BaseCarga):
    def cambiar(self, gestion, **datos):
        """Mismo PATCH que reprogramar. Se renombra para que cada prueba diga lo que hace."""
        return self.reprogramar(gestion, **datos)


class MarcarEjecutadaTests(BaseEstado):
    def test_marcar_como_ejecutada_no_cambia_la_fecha_ni_las_horas(self):
        gestion = self.crear_gestion(2)

        self.cambiar(gestion, estado="EJECUTADA")

        gestion.refresh_from_db()
        self.assertEqual(gestion.fecha_objetivo, self.dia_x)
        self.assertEqual(gestion.horas_estimadas, Decimal("2.0"))

    def test_estado_desconocido_se_rechaza_con_mensaje_en_espanol(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(gestion, estado="TERMINADA")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["estado"], [ESTADO_INVALIDO])


class PosponerTests(BaseEstado):
    """Posponer cambia el estado. La nota y la fecha nueva son opcionales; la fecha solo va hacia adelante."""

    def test_posponer_guarda_estado_fecha_y_nota(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion,
            estado="POSPUESTA",
            fecha_objetivo=self.otro_dia,
            nota_posposicion="El salón confirma la otra semana.",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "POSPUESTA")
        self.assertEqual(gestion.fecha_objetivo, self.otro_dia)
        self.assertEqual(gestion.nota_posposicion, "El salón confirma la otra semana.")

    def test_la_nota_es_opcional(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(gestion, estado="POSPUESTA", fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data["nota_posposicion"])

    def test_una_nota_con_solo_espacios_se_guarda_vacia(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion, estado="POSPUESTA", fecha_objetivo=self.otro_dia, nota_posposicion="   "
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data["nota_posposicion"])

    def test_posponer_sin_fecha_nueva_conserva_la_fecha(self):
        # US-09 escenario 2: basta con el estado y la nota.
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(gestion, estado="POSPUESTA", nota_posposicion="Esperando al salón.")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "POSPUESTA")
        self.assertEqual(gestion.fecha_objetivo, self.dia_x)

    def test_posponer_a_la_misma_fecha_se_rechaza(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(gestion, estado="POSPUESTA", fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["fecha_objetivo"], [POSPONER_FECHA_ANTERIOR])

    def test_posponer_a_una_fecha_anterior_se_rechaza(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion, estado="POSPUESTA", fecha_objetivo=self.dia_x - timedelta(days=1)
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["fecha_objetivo"], [POSPONER_FECHA_ANTERIOR])

    def test_una_vencida_se_puede_posponer_a_hoy(self):
        gestion = self.crear_gestion(2, fecha=self.hoy - timedelta(days=2))

        respuesta = self.cambiar(gestion, estado="POSPUESTA", fecha_objetivo=self.hoy)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["situacion"], "PARA_HOY")

    def test_no_se_puede_posponer_despues_de_la_fecha_del_evento(self):
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion, estado="POSPUESTA", fecha_objetivo=self.hoy + timedelta(days=60)
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_objetivo", respuesta.data)

    def test_una_ejecutada_no_se_puede_posponer(self):
        gestion = self.crear_gestion(2, estado="EJECUTADA")

        respuesta = self.cambiar(gestion, estado="POSPUESTA", fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["estado"], [POSPONER_EJECUTADA])

    def test_reprogramar_una_pospuesta_sin_enviar_estado_sigue_las_reglas_normales(self):
        # El diálogo de reprogramar solo envía la fecha. Mover hacia atrás es válido ahí.
        gestion = self.crear_gestion(2, fecha=self.otro_dia, estado="POSPUESTA")

        respuesta = self.cambiar(gestion, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "POSPUESTA")


class PosponerConSobrecargaTests(BaseEstado):
    """Posponer mueve la fecha, así que pasa por la misma revisión de sobrecarga del Sprint 3."""

    def test_posponer_a_un_dia_lleno_pide_confirmacion_y_no_guarda(self):
        self.crear_gestion(5, fecha=self.otro_dia)
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion,
            estado="POSPUESTA",
            fecha_objetivo=self.otro_dia,
            nota_posposicion="Se cruza con la prueba de menú.",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["codigo"], "sobrecarga_diaria")
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("7.0"))
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "PENDIENTE")
        self.assertIsNone(gestion.nota_posposicion)

    def test_posponer_a_un_dia_lleno_se_guarda_si_el_usuario_confirma(self):
        self.crear_gestion(5, fecha=self.otro_dia)
        gestion = self.crear_gestion(2)

        respuesta = self.cambiar(
            gestion,
            estado="POSPUESTA",
            fecha_objetivo=self.otro_dia,
            confirmar_sobrecarga=True,
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "POSPUESTA")


class DesmarcarEjecutadaTests(BaseEstado):
    """Una gestión que deja de estar ejecutada vuelve a ocupar horas en su día."""

    def test_volver_a_pendiente_en_un_dia_lleno_pide_confirmacion(self):
        self.crear_gestion(5)
        gestion = self.crear_gestion(2, estado="EJECUTADA")

        respuesta = self.cambiar(gestion, estado="PENDIENTE")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("7.0"))
        gestion.refresh_from_db()
        self.assertEqual(gestion.estado, "EJECUTADA")

    def test_volver_a_pendiente_con_cupo_no_pide_confirmacion(self):
        self.crear_gestion(3)
        gestion = self.crear_gestion(2, estado="EJECUTADA")

        respuesta = self.cambiar(gestion, estado="PENDIENTE")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            SubtareaLogistica.objects.get(id=gestion.id).estado, "PENDIENTE"
        )
