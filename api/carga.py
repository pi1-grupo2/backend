"""Carga diaria de gestión de un organizador.

Aquí vive la única regla de sobrecarga del proyecto, para que reprogramar,
reducir horas y el listado de conflictos sumen siempre de la misma manera.
"""

from decimal import Decimal

from django.db.models import Sum

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


def formatear_horas(valor):
    """7.0 se muestra como 7 y 7.5 como 7,5."""
    texto = f"{Decimal(valor):f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")
