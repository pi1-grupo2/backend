"""Avisos de sobrecarga fuera del PATCH de la gestión.

Pedido del docente en la retroalimentación del Sprint 3: si al cambiar el límite algún
día queda con sobrecarga, la aplicación debe avisar y ofrecer qué hacer. Lo mismo al
crear una gestión. Reprogramar, editar y posponer ya se revisan en test_sobrecarga.py
y test_estado.py.
"""

from datetime import timedelta
from decimal import Decimal

from rest_framework import status

from api.models import SubtareaLogistica

from .test_sobrecarga import BaseCarga

URL_ORGANIZADOR = "/api/organizador/"
URL_SOBRECARGA = "/api/organizador/sobrecarga/"


class BajarLimiteTests(BaseCarga):
    """Configuración: bajar el límite con días que quedarían por encima."""

    def cambiar_limite(self, valor, metodo="patch", **extra):
        llamada = getattr(self.client, metodo)
        return llamada(URL_ORGANIZADOR, {"limite_diario_horas": valor, **extra}, format="json")

    def test_avisa_con_los_dias_que_quedarian_por_encima_y_no_guarda(self):
        self.crear_gestion(4, nombre="Catering")
        self.crear_gestion(2, nombre="Música")

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["codigo"], "sobrecarga_por_limite")
        self.assertEqual(respuesta.data["detail"], "Con un límite de 4h, 1 día quedaría por encima del límite.")
        self.assertEqual(respuesta.data["limite_actual"], Decimal("6.0"))
        dia = respuesta.data["dias"][0]
        self.assertEqual(dia["fecha"], self.dia_x)
        self.assertEqual(dia["horas_planificadas"], Decimal("6.0"))
        self.assertEqual(dia["exceso_horas"], Decimal("2.0"))
        self.organizador.refresh_from_db()
        self.assertEqual(self.organizador.limite_diario_horas, Decimal("6.0"))

    def test_el_mensaje_cuenta_varios_dias(self):
        self.crear_gestion(6)
        self.crear_gestion(5, fecha=self.otro_dia)

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.data["detail"], "Con un límite de 4h, 2 días quedarían por encima del límite.")

    def test_put_tambien_avisa(self):
        self.crear_gestion(6)

        respuesta = self.cambiar_limite(4, metodo="put")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    def test_con_confirmacion_guarda_y_devuelve_los_dias(self):
        self.crear_gestion(6)

        respuesta = self.cambiar_limite(4, confirmar_sobrecarga=True)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(respuesta.data["limite_diario_horas"]), Decimal("4.0"))
        self.assertEqual(len(respuesta.data["dias_sobrecargados"]), 1)
        self.organizador.refresh_from_db()
        self.assertEqual(self.organizador.limite_diario_horas, Decimal("4.0"))

    def test_sin_dias_afectados_guarda_sin_avisar(self):
        self.crear_gestion(3)

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["dias_sobrecargados"], [])

    def test_un_dia_justo_en_el_nuevo_limite_no_es_sobrecarga(self):
        self.crear_gestion(4)

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_subir_el_limite_no_pide_confirmacion_aunque_queden_dias_por_encima(self):
        self.crear_gestion(10)

        respuesta = self.cambiar_limite(8)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["dias_sobrecargados"][0]["exceso_horas"], Decimal("2.0"))

    def test_no_cuenta_dias_pasados_ni_gestiones_ejecutadas(self):
        self.crear_gestion(6, fecha=self.hoy - timedelta(days=1))
        self.crear_gestion(6, estado="EJECUTADA")

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_hoy_si_cuenta(self):
        self.crear_gestion(6, fecha=self.hoy)

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    def test_suma_todos_los_eventos_del_organizador_y_no_los_ajenos(self):
        self.crear_gestion(3)
        self.crear_gestion(3, evento=self.crear_evento(self.organizador, "Cumpleaños"))
        ajeno = self.crear_organizador("pedro@correo.com")
        self.crear_gestion(8, fecha=self.otro_dia, evento=self.crear_evento(ajeno, "Evento ajeno"))

        respuesta = self.cambiar_limite(4)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(len(respuesta.data["dias"]), 1)
        self.assertEqual(len(respuesta.data["dias"][0]["gestiones"]), 2)

    def test_un_limite_invalido_sigue_respondiendo_400(self):
        self.crear_gestion(6)

        respuesta = self.cambiar_limite(6.3)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class ListadoDeSobrecargaTests(BaseCarga):
    """GET /api/organizador/sobrecarga/: para avisar en Configuración y marcar días en /hoy."""

    def test_sin_sobrecarga(self):
        self.crear_gestion(6)

        respuesta = self.client.get(URL_SOBRECARGA)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(respuesta.data["tiene_sobrecarga"])
        self.assertEqual(respuesta.data["dias"], [])

    def test_lista_el_dia_con_las_gestiones_de_todos_los_eventos(self):
        cumpleanos = self.crear_evento(self.organizador, "Cumpleaños")
        self.crear_gestion(5, nombre="Catering")
        self.crear_gestion(3, evento=cumpleanos, nombre="Torta")

        respuesta = self.client.get(URL_SOBRECARGA)

        self.assertTrue(respuesta.data["tiene_sobrecarga"])
        dia = respuesta.data["dias"][0]
        self.assertEqual(dia["horas_planificadas"], Decimal("8.0"))
        self.assertEqual(dia["exceso_horas"], Decimal("2.0"))
        nombres = [(g["nombre"], g["evento_nombre"]) for g in dia["gestiones"]]
        self.assertEqual(nombres, [("Catering", "Boda Ramírez"), ("Torta", "Cumpleaños")])

    def test_ofrece_mover_o_reducir_cada_gestion(self):
        self.crear_gestion(5, nombre="Catering")
        self.crear_gestion(3, nombre="Torta")

        dia = self.client.get(URL_SOBRECARGA).data["dias"][0]
        catering, torta = dia["gestiones"]

        # Mover: el primer día con cupo es hoy, que está vacío.
        self.assertEqual(catering["fecha_sugerida"], self.hoy)
        # Reducir: sobran 2 h, así que cada una cabe quitándole 2 h.
        self.assertEqual(catering["horas_sugeridas"], Decimal("3.0"))
        self.assertEqual(torta["horas_sugeridas"], Decimal("1.0"))

    def test_no_sugiere_reducir_si_la_gestion_sola_no_alcanza(self):
        self.crear_gestion(6, nombre="Catering")
        self.crear_gestion(2, nombre="Torta")
        self.client.patch(URL_ORGANIZADOR, {"limite_diario_horas": 5, "confirmar_sobrecarga": True}, format="json")

        dia = self.client.get(URL_SOBRECARGA).data["dias"][0]
        torta = next(g for g in dia["gestiones"] if g["nombre"] == "Torta")

        # Sobran 3 h y Torta solo tiene 2: dejarla en cero no es una opción.
        self.assertIsNone(torta["horas_sugeridas"])

    def test_revisa_un_limite_sin_guardarlo(self):
        self.crear_gestion(5)

        respuesta = self.client.get(URL_SOBRECARGA, {"limite": "4"})

        self.assertTrue(respuesta.data["tiene_sobrecarga"])
        self.assertEqual(respuesta.data["limite_diario_horas"], Decimal("4.0"))
        self.organizador.refresh_from_db()
        self.assertEqual(self.organizador.limite_diario_horas, Decimal("6.0"))

    def test_un_limite_de_prueba_invalido_responde_400(self):
        respuesta = self.client.get(URL_SOBRECARGA, {"limite": "20"})

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limite_diario_horas", respuesta.data)

    def test_pide_sesion(self):
        self.client.credentials()

        respuesta = self.client.get(URL_SOBRECARGA)

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class CrearGestionTests(BaseCarga):
    """POST de gestiones: misma revisión que reprogramar."""

    def crear(self, horas, fecha=None, **extra):
        datos = {
            "nombre": "Decoración",
            "fecha_objetivo": (fecha or self.dia_x).isoformat(),
            "horas_estimadas": horas,
            **extra,
        }
        return self.client.post(f"/api/events/{self.evento.id}/subtasks/", datos, format="json")

    def test_con_cupo_crea_y_devuelve_la_carga_del_dia(self):
        self.crear_gestion(3)

        respuesta = self.crear(2)

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["carga_del_dia"]["horas_planificadas"], Decimal("5.0"))
        self.assertTrue(respuesta.data["carga_del_dia"]["dentro_del_limite"])

    def test_justo_en_el_limite_crea(self):
        self.crear_gestion(4)

        respuesta = self.crear(2)

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_dia_lleno_avisa_con_cifras_y_fecha_sugerida_y_no_crea(self):
        self.crear_gestion(5)

        respuesta = self.crear(2)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["codigo"], "sobrecarga_diaria")
        self.assertEqual(respuesta.data["detail"], "Quedarías con 7h de gestión planificadas (límite 6h)")
        self.assertEqual(respuesta.data["exceso_horas"], Decimal("1.0"))
        self.assertEqual(respuesta.data["fecha_sugerida"], self.hoy)
        self.assertFalse(SubtareaLogistica.objects.filter(nombre="Decoración").exists())

    def test_con_confirmacion_crea_aunque_pase_el_limite(self):
        self.crear_gestion(5)

        respuesta = self.crear(2, confirmar_sobrecarga=True)

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertFalse(respuesta.data["carga_del_dia"]["dentro_del_limite"])

    def test_nunca_crea_un_dia_de_mas_de_24_horas(self):
        self.crear_gestion(16)
        self.crear_gestion(7, evento=self.crear_evento(self.organizador, "Cumpleaños"))

        respuesta = self.crear(2, confirmar_sobrecarga=True)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["codigo"], "dia_excedido")

    def test_suma_las_gestiones_de_otros_eventos(self):
        self.crear_gestion(5, evento=self.crear_evento(self.organizador, "Cumpleaños"))

        respuesta = self.crear(2)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    def test_una_gestion_que_nace_ejecutada_no_ocupa_horas(self):
        self.crear_gestion(6)

        respuesta = self.crear(2, estado="EJECUTADA")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("carga_del_dia", respuesta.data)

    def test_los_errores_por_campo_van_antes_que_la_sobrecarga(self):
        self.crear_gestion(6)

        respuesta = self.crear(0)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("horas_estimadas", respuesta.data)
