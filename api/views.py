from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Evento, SubtareaLogistica
from .serializers import EventoSerializer, SubtareaLogisticaSerializer


@api_view(["GET"])
def health(request):
    """
    Endpoint de salud.
    Verifica que la API y la base de datos estén disponibles.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        base_de_datos = "ok"
    except Exception as error:  # noqa: BLE001
        base_de_datos = f"error: {error.__class__.__name__}"

    return Response(
        {
            "estado": "ok",
            "servicio": "api-organizador-eventos",
            "base_de_datos": base_de_datos,
        }
    )



@api_view(["GET", "POST"])
def eventos(request):
    if request.method == "GET":
        eventos = Evento.objects.all().order_by("fecha_hora_evento")
        serializer = EventoSerializer(eventos, many=True)
        return Response(serializer.data)

    serializer = EventoSerializer(data=request.data)

    if serializer.is_valid():
        evento = serializer.save()

        return Response(
            EventoSerializer(evento).data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET", "POST"])
def subtareas_evento(request, evento_id):
    try:
        evento = Evento.objects.get(id=evento_id)
    except Evento.DoesNotExist:
        return Response(
            {"detail": "Evento no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        subtareas = SubtareaLogistica.objects.filter(
            evento=evento
        ).order_by("fecha_objetivo", "id")

        serializer = SubtareaLogisticaSerializer(
            subtareas,
            many=True,
        )

        return Response(serializer.data)

    data = request.data.copy()
    data["evento"] = evento.id

    serializer = SubtareaLogisticaSerializer(data=data)

    if serializer.is_valid():
        subtarea = serializer.save()

        return Response(
            SubtareaLogisticaSerializer(subtarea).data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )

@api_view(["GET"])
def progreso_evento(request, evento_id):
    try:
        evento = Evento.objects.get(id=evento_id)
    except Evento.DoesNotExist:
        return Response(
            {"detail": "Evento no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    total_subtareas = SubtareaLogistica.objects.filter(
        evento=evento
    ).count()

    subtareas_ejecutadas = SubtareaLogistica.objects.filter(
        evento=evento,
        estado="EJECUTADA",
    ).count()

    if total_subtareas == 0:
        progreso = 0
    else:
        progreso = round(
            (subtareas_ejecutadas / total_subtareas) * 100,
            2,
        )

    return Response(
        {
            "evento": evento.id,
            "total_subtareas": total_subtareas,
            "subtareas_ejecutadas": subtareas_ejecutadas,
            "progreso": progreso,
        }
    )

@api_view(["GET"])
def conflictos_evento(request, evento_id):
    try:
        evento = Evento.objects.get(id=evento_id)
    except Evento.DoesNotExist:
        return Response(
            {"detail": "Evento no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    subtareas = SubtareaLogistica.objects.filter(
        evento=evento
    ).exclude(
        estado="EJECUTADA"
    )

    conflictos = []

    fechas = (
        subtareas
        .values_list("fecha_objetivo", flat=True)
        .distinct()
        .order_by("fecha_objetivo")
    )

    limite = evento.organizador.limite_diario_horas

    for fecha in fechas:
        subtareas_fecha = subtareas.filter(
            fecha_objetivo=fecha
        )

        horas_planificadas = sum(
            subtarea.horas_estimadas
            for subtarea in subtareas_fecha
        )

        if horas_planificadas > limite:
            conflictos.append(
                {
                    "fecha": fecha,
                    "horas_planificadas": horas_planificadas,
                    "limite_diario_horas": limite,
                    "exceso_horas": horas_planificadas - limite,
                    "subtareas": [
                        {
                            "id": subtarea.id,
                            "nombre": subtarea.nombre,
                            "horas_estimadas": subtarea.horas_estimadas,
                            "estado": subtarea.estado,
                        }
                        for subtarea in subtareas_fecha
                    ],
                }
            )

    return Response(
        {
            "evento": evento.id,
            "tiene_conflictos": len(conflictos) > 0,
            "conflictos": conflictos,
        }
    )

@api_view(["PATCH"])
def actualizar_subtarea(request, evento_id, subtarea_id):
    try:
        evento = Evento.objects.get(id=evento_id)
    except Evento.DoesNotExist:
        return Response(
            {"detail": "Evento no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        subtarea = SubtareaLogistica.objects.get(
            id=subtarea_id,
            evento=evento,
        )
    except SubtareaLogistica.DoesNotExist:
        return Response(
            {"detail": "Subtarea no encontrada para este evento."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = SubtareaLogisticaSerializer(
        subtarea,
        data=request.data,
        partial=True,
    )

    if serializer.is_valid():
        subtarea = serializer.save()

        return Response(
            SubtareaLogisticaSerializer(subtarea).data,
            status=status.HTTP_200_OK,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )