"""Carga diaria de gestión de un organizador.

Aquí vive la única regla de sobrecarga del proyecto, para que reprogramar,
reducir horas y el listado de conflictos sumen siempre de la misma manera.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import SubtareaLogistica

HORAS_DEL_DIA = Decimal("24")

# Una gestión ejecutada ya no ocupa tiempo del día. Las pospuestas sí: siguen pendientes.
ESTADO_QUE_NO_CUENTA = "EJECUTADA"


def horas_planificadas(organizador, fecha, excluir_id=None):
    """Suma las horas pendientes del organizador en una fecha, en todos sus eventos.

    excluir_id deja por fuera una gestión. Se usa al reprogramarla, para no contarla
    dos veces: una por lo que ya está guardado y otra por el valor nuevo.
    """
    gestiones = SubtareaLogistica.objects.filter(
        evento__organizador=organizador,
        fecha_objetivo=fecha,
    ).exclude(estado=ESTADO_QUE_NO_CUENTA)
    if excluir_id is not None:
        gestiones = gestiones.exclude(id=excluir_id)
    return gestiones.aggregate(total=Sum("horas_estimadas"))["total"] or Decimal("0")


def evaluar_carga(organizador, fecha, horas, excluir_id=None):
    """Calcula cómo quedaría el día si una gestión de `horas` se ubica en `fecha`."""
    limite = organizador.limite_diario_horas
    total = horas_planificadas(organizador, fecha, excluir_id) + horas
    return {
        "fecha": fecha,
        "horas_planificadas": total,
        "limite_diario_horas": limite,
        "exceso_horas": max(total - limite, Decimal("0")),
        "supera_limite": total > limite,
        "supera_dia": total > HORAS_DEL_DIA,
    }


def fecha_del_evento(evento):
    """Día del evento en America/Bogota. Una gestión no puede quedar después."""
    momento = evento.fecha_hora_evento
    if timezone.is_aware(momento):
        return timezone.localtime(momento).date()
    return momento.date()


def sugerir_fecha(organizador, evento, fecha_rechazada, horas, excluir_id=None):
    """Primer día entre hoy y el evento, distinto al rechazado, donde estas horas caben.

    Devuelve None si ningún día deja el plan dentro del límite y de las 24 h.
    No inventa una fecha fuera de ese rango.
    """
    hoy = timezone.localdate()
    ultimo = fecha_del_evento(evento)
    if ultimo < hoy:
        return None

    dia = hoy
    while dia <= ultimo:
        if dia != fecha_rechazada:
            carga = evaluar_carga(organizador, dia, horas, excluir_id=excluir_id)
            if not carga["supera_limite"] and not carga["supera_dia"]:
                return dia
        dia += timedelta(days=1)
    return None


def carga_guardada(organizador, fecha):
    """Horas que quedaron en el día después de guardar, ya con la gestión incluida."""
    total = horas_planificadas(organizador, fecha)
    limite = organizador.limite_diario_horas
    return {
        "fecha": fecha,
        "horas_planificadas": total,
        "limite_diario_horas": limite,
        "dentro_del_limite": total <= limite,
    }


def formatear_horas(valor):
    """7.0 se muestra como 7 y 7.5 como 7,5."""
    texto = f"{Decimal(valor):f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")
