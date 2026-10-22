"""Casos pendientes de QA; todos los objetos proceden de la base de pruebas."""

from datetime import timedelta

from api.models import SubtareaLogistica
from .test_sobrecarga import BaseCarga


class SubtareasQATests(BaseCarga):
    def url(self, gestion, evento=None):
        return f"/api/events/{(evento or self.evento).id}/subtasks/{gestion.id}/"

    def test_eliminar_libera_carga_y_actualiza_progreso_http_204_200_404(self):
        gestion = self.crear_gestion(6)
        otra = self.crear_gestion(1, fecha=self.otro_dia)
        respuesta = self.client.delete(self.url(gestion))
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(respuesta.content, b"")
        self.assertFalse(SubtareaLogistica.objects.filter(pk=gestion.pk).exists())
        self.assertTrue(SubtareaLogistica.objects.filter(pk=otra.pk).exists())
        progreso = self.client.get(f"/api/events/{self.evento.id}/progress/")
        self.assertEqual(progreso.status_code, 200)
        self.assertEqual(progreso.data["total_subtareas"], 1)
        self.assertEqual(self.reprogramar(otra, fecha_objetivo=self.dia_x).status_code, 200)
        self.assertEqual(self.client.delete(self.url(gestion)).status_code, 404)

    def test_eliminar_sin_sesion_http_401_conserva_datos(self):
        gestion = self.crear_gestion(1)
        self.client.credentials()
        self.assertEqual(self.client.delete(self.url(gestion)).status_code, 401)
        self.assertTrue(SubtareaLogistica.objects.filter(pk=gestion.pk).exists())

    def test_eliminar_evento_ajeno_http_404_conserva_datos(self):
        ajeno = self.crear_evento(self.crear_organizador("ajeno@example.com"), "Ajeno")
        gestion = self.crear_gestion(1, evento=ajeno)
        self.assertEqual(self.client.delete(self.url(gestion, ajeno)).status_code, 404)
        self.assertTrue(SubtareaLogistica.objects.filter(pk=gestion.pk).exists())

    def test_eliminar_con_evento_incorrecto_http_404_conserva_datos(self):
        otro = self.crear_evento(self.organizador, "Otro")
        gestion = self.crear_gestion(1, evento=otro)
        self.assertEqual(self.client.delete(self.url(gestion)).status_code, 404)
        self.assertTrue(SubtareaLogistica.objects.filter(pk=gestion.pk).exists())

    def test_validaciones_patch_http_400_sin_cambios(self):
        gestion = self.crear_gestion(1)
        casos = [
            ("nombre", ""), ("nombre", "x" * 201), ("nombre", None),
            ("horas_estimadas", 0), ("horas_estimadas", -1),
            ("horas_estimadas", "abc"), ("horas_estimadas", "1.25"),
            ("horas_estimadas", None), ("estado", "INVALIDO"),
            ("fecha_objetivo", "no-es-fecha"),
            ("fecha_objetivo", (self.hoy - timedelta(days=1)).isoformat()),
        ]
        original = SubtareaLogistica.objects.values().get(pk=gestion.pk)
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                respuesta = self.client.patch(self.url(gestion), {campo: valor}, format="json")
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(campo, respuesta.data)
                self.assertEqual(SubtareaLogistica.objects.values().get(pk=gestion.pk), original)

    def test_ejecucion_repetida_http_200_conserva_fecha_horas_y_nota(self):
        gestion = self.crear_gestion(2)
        gestion.nota_posposicion = "Nota QA"
        gestion.save()
        for _ in range(2):
            respuesta = self.reprogramar(gestion, estado="EJECUTADA")
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.data["situacion"], "EJECUTADA")
        gestion.refresh_from_db()
        self.assertEqual(gestion.fecha_objetivo, self.dia_x)
        self.assertEqual(gestion.horas_estimadas, 2)
        self.assertEqual(gestion.nota_posposicion, "Nota QA")

    def test_patch_no_debe_trasladar_subtarea_a_evento_ajeno_http_400(self):
        """Regresión de autorización: se espera rechazo, nunca traslado entre cuentas."""
        gestion = self.crear_gestion(1)
        ajeno = self.crear_evento(self.crear_organizador("otra@example.com"), "Ajeno")
        respuesta = self.reprogramar(gestion, evento=ajeno.id)
        gestion.refresh_from_db()
        self.assertEqual(
            (respuesta.status_code, gestion.evento_id),
            (400, self.evento.id),
            "PATCH debe rechazar el evento ajeno y conservar el evento original.",
        )
        self.assertIn("evento", respuesta.data)

    def test_patch_rechaza_otro_evento_propio_http_400(self):
        gestion = self.crear_gestion(1)
        otro = self.crear_evento(self.organizador, "Otro propio")
        respuesta = self.reprogramar(gestion, evento=otro.id)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("evento", respuesta.data)
        gestion.refresh_from_db()
        self.assertEqual(gestion.evento_id, self.evento.id)

    def test_patch_permite_mismo_evento_http_200(self):
        gestion = self.crear_gestion(1)
        respuesta = self.reprogramar(gestion, evento=self.evento.id, nombre="Actualizada")
        self.assertEqual(respuesta.status_code, 200)
        gestion.refresh_from_db()
        self.assertEqual(gestion.evento_id, self.evento.id)
        self.assertEqual(gestion.nombre, "Actualizada")

    def test_patch_traslado_y_nombre_http_400_sin_ningun_cambio(self):
        gestion = self.crear_gestion(1)
        destinos = [
            self.crear_evento(self.organizador, "Otro propio"),
            self.crear_evento(self.crear_organizador("destino@example.com"), "Ajeno"),
        ]
        original = SubtareaLogistica.objects.values().get(pk=gestion.pk)
        for destino in destinos:
            with self.subTest(evento=destino.pk):
                respuesta = self.reprogramar(gestion, evento=destino.pk, nombre="No guardar")
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("evento", respuesta.data)
                self.assertEqual(SubtareaLogistica.objects.values().get(pk=gestion.pk), original)

    def test_post_usa_evento_de_url_aunque_cuerpo_indique_otro_http_201(self):
        ajeno = self.crear_evento(self.crear_organizador("post@example.com"), "Ajeno")
        respuesta = self.client.post(
            f"/api/events/{self.evento.id}/subtasks/",
            {
                "evento": ajeno.pk,
                "nombre": "Nueva QA",
                "fecha_objetivo": self.dia_x.isoformat(),
                "horas_estimadas": "1.0",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["evento"], self.evento.pk)
        creada = SubtareaLogistica.objects.get(pk=respuesta.data["id"])
        self.assertEqual(creada.evento_id, self.evento.pk)
        self.assertFalse(SubtareaLogistica.objects.filter(evento=ajeno).exists())
