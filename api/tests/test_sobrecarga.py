from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.autenticacion import crear_sesion
from api.models import Evento, Organizador, SubtareaLogistica


class BaseCarga(APITestCase):
    """Un organizador con sesión, un evento a 30 días y atajos para armar el día X."""

    def setUp(self):
        self.hoy = timezone.localdate()
        self.dia_x = self.hoy + timedelta(days=5)
        self.otro_dia = self.hoy + timedelta(days=6)
        self.organizador = self.crear_organizador("laura@correo.com")
        self.evento = self.crear_evento(self.organizador, "Boda Ramírez")
        self.autenticar(self.organizador)

    def crear_organizador(self, correo, limite="6.0"):
        return Organizador.objects.create(
            nombre=correo.split("@")[0],
            correo=correo,
            password="sin-uso-en-estas-pruebas",
            limite_diario_horas=Decimal(limite),
        )

    def crear_evento(self, organizador, nombre):
        fecha_evento = timezone.now() + timedelta(days=30)
        return Evento.objects.create(
            organizador=organizador,
            nombre=nombre,
            tipo="boda",
            cliente_contacto="Cliente",
            fecha_hora_evento=fecha_evento,
            lugar="Salón",
            plazo_limite=fecha_evento.date(),
        )

    def crear_gestion(self, horas, fecha=None, evento=None, estado="PENDIENTE", nombre="Gestión"):
        return SubtareaLogistica.objects.create(
            evento=evento or self.evento,
            nombre=nombre,
            fecha_objetivo=fecha or self.dia_x,
            horas_estimadas=Decimal(str(horas)),
            estado=estado,
        )

    def autenticar(self, organizador):
        token = crear_sesion(organizador).token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def reprogramar(self, gestion, **datos):
        if "fecha_objetivo" in datos:
            datos["fecha_objetivo"] = datos["fecha_objetivo"].isoformat()
        return self.client.patch(
            f"/api/events/{gestion.evento_id}/subtasks/{gestion.id}/",
            datos,
            format="json",
        )


class DetectarConflictoTests(BaseCarga):
    """US-07."""

    def test_escenario_1_conflicto_con_cifras(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia, nombre="Buscar proveedores")

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["codigo"], "sobrecarga_diaria")
        self.assertEqual(respuesta.data["fecha"], self.dia_x)
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("7.0"))
        self.assertEqual(respuesta.data["limite_diario_horas"], Decimal("6.0"))
        self.assertEqual(respuesta.data["exceso_horas"], Decimal("1.0"))
        self.assertEqual(
            respuesta.data["detail"],
            "Quedarías con 7h de gestión planificadas (límite 6h)",
        )

    def test_el_conflicto_no_guarda_el_cambio(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        proveedores.refresh_from_db()
        self.assertEqual(proveedores.fecha_objetivo, self.otro_dia)

    def test_escenario_2_sin_conflicto_cuando_queda_justo_en_el_limite(self):
        self.crear_gestion(4)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        proveedores.refresh_from_db()
        self.assertEqual(proveedores.fecha_objetivo, self.dia_x)

    def test_el_mensaje_muestra_medias_horas_con_coma(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion("2.5", fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(
            respuesta.data["detail"],
            "Quedarías con 7,5h de gestión planificadas (límite 6h)",
        )

    def test_las_gestiones_ejecutadas_no_cuentan(self):
        self.crear_gestion(3)
        self.crear_gestion(2, estado="EJECUTADA")
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_las_gestiones_pospuestas_si_cuentan(self):
        self.crear_gestion(3)
        self.crear_gestion(2, estado="POSPUESTA")
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    def test_suma_las_gestiones_de_todos_los_eventos_del_organizador(self):
        otro_evento = self.crear_evento(self.organizador, "Congreso")
        self.crear_gestion(5, evento=otro_evento)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("7.0"))

    def test_no_suma_las_gestiones_de_otro_organizador(self):
        ajeno = self.crear_organizador("pedro@correo.com")
        self.crear_gestion(5, evento=self.crear_evento(ajeno, "Evento ajeno"))
        self.crear_gestion(4)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_usa_el_limite_configurado_por_el_organizador(self):
        self.client.patch("/api/organizador/", {"limite_diario_horas": 4}, format="json")
        self.crear_gestion(3)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["limite_diario_horas"], Decimal("4.0"))
        self.assertEqual(
            respuesta.data["detail"],
            "Quedarías con 5h de gestión planificadas (límite 4h)",
        )


class NoRevisarCuandoNoCorrespondeTests(BaseCarga):
    def test_marcar_como_ejecutada_en_un_dia_sobrecargado_no_pide_confirmacion(self):
        self.crear_gestion(5)
        gestion = self.crear_gestion(3)

        respuesta = self.reprogramar(gestion, estado="EJECUTADA")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_cambiar_solo_el_nombre_no_dispara_conflicto(self):
        self.crear_gestion(5)
        gestion = self.crear_gestion(3)

        respuesta = self.reprogramar(gestion, nombre="Otro nombre")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_enviar_la_misma_fecha_no_dispara_conflicto(self):
        self.crear_gestion(5)
        gestion = self.crear_gestion(3)

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_la_gestion_que_se_edita_no_se_cuenta_dos_veces(self):
        gestion = self.crear_gestion(3)

        respuesta = self.reprogramar(gestion, horas_estimadas=5)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)


class ResolverConflictoTests(BaseCarga):
    """US-08."""

    def test_guardar_con_sobrecarga_cuando_el_usuario_confirma(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(
            proveedores,
            fecha_objetivo=self.dia_x,
            confirmar_sobrecarga=True,
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        proveedores.refresh_from_db()
        self.assertEqual(proveedores.fecha_objetivo, self.dia_x)

    def test_escenario_1_resolver_moviendo_a_un_dia_con_cupo(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)
        self.assertEqual(
            self.reprogramar(proveedores, fecha_objetivo=self.dia_x).status_code,
            status.HTTP_409_CONFLICT,
        )

        dia_libre = self.hoy + timedelta(days=7)
        respuesta = self.reprogramar(proveedores, fecha_objetivo=dia_libre)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["fecha_objetivo"], dia_libre.isoformat())

    def test_escenario_2_reducir_horas_resuelve_el_conflicto(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(2, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x, horas_estimadas=1)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        proveedores.refresh_from_db()
        self.assertEqual(proveedores.horas_estimadas, Decimal("1.0"))
        self.assertEqual(proveedores.fecha_objetivo, self.dia_x)

    def test_escenario_2_el_conflicto_persiste_si_la_reduccion_no_alcanza(self):
        self.crear_gestion(5)
        proveedores = self.crear_gestion(3, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x, horas_estimadas=2)

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("7.0"))
        self.assertEqual(respuesta.data["exceso_horas"], Decimal("1.0"))

    def test_el_listado_de_conflictos_queda_vacio_despues_de_resolver(self):
        self.crear_gestion(5)
        pesada = self.crear_gestion(3)
        url = f"/api/events/{self.evento.id}/conflicts/"
        self.assertTrue(self.client.get(url).data["tiene_conflictos"])

        self.reprogramar(pesada, horas_estimadas=1)

        self.assertFalse(self.client.get(url).data["tiene_conflictos"])


class LimiteDelDiaTests(BaseCarga):
    """Regla del docente: el único bloqueo es superar las 24 horas del día."""

    def test_superar_24_horas_se_rechaza(self):
        self.crear_gestion(20)
        proveedores = self.crear_gestion(5, fecha=self.otro_dia)

        respuesta = self.reprogramar(proveedores, fecha_objetivo=self.dia_x)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(respuesta.data["codigo"], "dia_excedido")
        self.assertEqual(respuesta.data["horas_planificadas"], Decimal("25.0"))

    def test_superar_24_horas_se_rechaza_aunque_el_usuario_confirme(self):
        self.crear_gestion(20)
        proveedores = self.crear_gestion(5, fecha=self.otro_dia)

        respuesta = self.reprogramar(
            proveedores,
            fecha_objetivo=self.dia_x,
            confirmar_sobrecarga=True,
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        proveedores.refresh_from_db()
        self.assertEqual(proveedores.fecha_objetivo, self.otro_dia)

    def test_exactamente_24_horas_se_permite_con_confirmacion(self):
        self.crear_gestion(20)
        proveedores = self.crear_gestion(4, fecha=self.otro_dia)

        respuesta = self.reprogramar(
            proveedores,
            fecha_objetivo=self.dia_x,
            confirmar_sobrecarga=True,
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_reducir_horas_se_permite_aunque_el_dia_siga_sobre_24(self):
        self.crear_gestion(20)
        pesada = self.crear_gestion(10)

        respuesta = self.reprogramar(pesada, horas_estimadas=8, confirmar_sobrecarga=True)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)


class FechaDeReprogramacionTests(BaseCarga):
    """US-06."""

    def test_reprogramar_guarda_y_devuelve_la_nueva_fecha(self):
        gestion = self.crear_gestion(2)

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["fecha_objetivo"], self.otro_dia.isoformat())
        self.assertEqual(respuesta.data["situacion"], "PROXIMA")

    def test_una_vencida_reprogramada_para_hoy_cambia_de_grupo(self):
        vencida = self.crear_gestion(2, fecha=self.hoy - timedelta(days=3))

        respuesta = self.reprogramar(vencida, fecha_objetivo=self.hoy)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["situacion"], "PARA_HOY")

    def test_no_se_puede_reprogramar_a_una_fecha_pasada(self):
        gestion = self.crear_gestion(2)

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.hoy - timedelta(days=1))

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            [str(error) for error in respuesta.data["fecha_objetivo"]],
            ["La nueva fecha no puede ser anterior al día de hoy."],
        )

    def test_una_vencida_se_puede_marcar_como_ejecutada_sin_cambiar_la_fecha(self):
        vencida = self.crear_gestion(2, fecha=self.hoy - timedelta(days=3))

        respuesta = self.reprogramar(vencida, estado="EJECUTADA")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_no_se_puede_reprogramar_despues_de_la_fecha_del_evento(self):
        gestion = self.crear_gestion(2)

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.hoy + timedelta(days=40))

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_objetivo", respuesta.data)

    def test_no_se_puede_reprogramar_la_gestion_de_otro_organizador(self):
        gestion = self.crear_gestion(2)
        self.autenticar(self.crear_organizador("pedro@correo.com"))

        respuesta = self.reprogramar(gestion, fecha_objetivo=self.otro_dia)

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        gestion.refresh_from_db()
        self.assertEqual(gestion.fecha_objetivo, self.dia_x)


class LimiteDiarioTests(BaseCarga):
    """US-12."""

    def test_acepta_medias_horas(self):
        respuesta = self.client.patch("/api/organizador/", {"limite_diario_horas": 6.5}, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(respuesta.data["limite_diario_horas"]), Decimal("6.5"))

    def test_rechaza_valores_que_no_son_horas_completas_ni_medias(self):
        respuesta = self.client.patch("/api/organizador/", {"limite_diario_horas": 6.3}, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limite_diario_horas", respuesta.data)

    def test_rechaza_valores_fuera_del_rango(self):
        for valor in (0.5, 16.5, 0, 17):
            respuesta = self.client.patch(
                "/api/organizador/",
                {"limite_diario_horas": valor},
                format="json",
            )
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST, valor)


class ListadoDeConflictosTests(BaseCarga):
    def test_suma_por_organizador_y_no_solo_por_evento(self):
        otro_evento = self.crear_evento(self.organizador, "Congreso")
        self.crear_gestion(4, evento=otro_evento)
        self.crear_gestion(3)

        respuesta = self.client.get(f"/api/events/{self.evento.id}/conflicts/")

        self.assertTrue(respuesta.data["tiene_conflictos"])
        conflicto = respuesta.data["conflictos"][0]
        self.assertEqual(conflicto["horas_planificadas"], Decimal("7.0"))
        self.assertEqual(conflicto["exceso_horas"], Decimal("1.0"))
