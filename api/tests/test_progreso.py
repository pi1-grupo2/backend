"""Sprint 4: progreso de un evento según sus gestiones ejecutadas."""

from .test_sobrecarga import BaseCarga


class ProgresoEventoTests(BaseCarga):
    def progreso(self, evento=None):
        return self.client.get(f"/api/events/{(evento or self.evento).id}/progress/")

    def test_cuenta_cada_estado_y_calcula_el_porcentaje(self):
        self.crear_gestion(1, estado="EJECUTADA")
        self.crear_gestion(1, estado="EJECUTADA")
        self.crear_gestion(1, estado="POSPUESTA")
        self.crear_gestion(1)

        datos = self.progreso().data

        self.assertEqual(datos["total_subtareas"], 4)
        self.assertEqual(datos["subtareas_ejecutadas"], 2)
        self.assertEqual(datos["subtareas_pospuestas"], 1)
        self.assertEqual(datos["subtareas_pendientes"], 1)
        self.assertEqual(datos["progreso"], 50.0)

    def test_el_porcentaje_se_redondea_a_un_decimal(self):
        self.crear_gestion(1, estado="EJECUTADA")
        self.crear_gestion(1)
        self.crear_gestion(1)

        self.assertEqual(self.progreso().data["progreso"], 33.3)

    def test_todas_ejecutadas_da_cien(self):
        self.crear_gestion(1, estado="EJECUTADA")
        self.crear_gestion(2, estado="EJECUTADA")

        self.assertEqual(self.progreso().data["progreso"], 100.0)

    def test_marcar_una_gestion_como_ejecutada_sube_el_progreso(self):
        gestion = self.crear_gestion(1)
        self.crear_gestion(1)
        self.assertEqual(self.progreso().data["progreso"], 0)

        self.reprogramar(gestion, estado="EJECUTADA")

        self.assertEqual(self.progreso().data["progreso"], 50.0)

    def test_no_cuenta_gestiones_de_otros_eventos(self):
        otro_evento = self.crear_evento(self.organizador, "Cumpleaños Rosa")
        self.crear_gestion(1, evento=otro_evento, estado="EJECUTADA")
        self.crear_gestion(1)

        datos = self.progreso().data

        self.assertEqual(datos["total_subtareas"], 1)
        self.assertEqual(datos["progreso"], 0)
