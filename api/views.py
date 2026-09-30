from django.db import connection
from django.contrib.auth.hashers import check_password
import secrets

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .autenticacion import MENSAJE_CREDENCIALES
from .models import Evento, Organizador, Sesion, SubtareaLogistica
from .serializers import (
    EventoSerializer,
    OrganizadorSerializer,
    SubtareaLogisticaSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Comprueba que la API y la base de datos respondan."""
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


@api_view(["GET", "PATCH"])
def organizador_actual(request):
    organizador = request.user

    if request.method == "GET":
        return Response(OrganizadorSerializer(organizador).data)

    serializer = OrganizadorSerializer(organizador, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def eventos(request):
    if request.method == "GET":
        queryset = Evento.objects.filter(organizador=request.user).order_by("fecha_hora_evento")
        return Response(EventoSerializer(queryset, many=True).data)

    datos = request.data.copy()
    datos["organizador"] = request.user.id

    serializer = EventoSerializer(data=datos)
    if serializer.is_valid():
        evento = serializer.save()
        return Response(EventoSerializer(evento).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _obtener_evento(evento_id, organizador):
    try:
        return Evento.objects.get(id=evento_id, organizador=organizador), None
    except Evento.DoesNotExist:
        return None, Response(
            {"detail": "Evento no encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["GET", "PATCH", "DELETE"])
def evento_detalle(request, evento_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    if request.method == "GET":
        return Response(EventoSerializer(evento).data)

    if request.method == "DELETE":
        evento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = EventoSerializer(evento, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def subtareas_evento(request, evento_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    if request.method == "GET":
        subtareas = SubtareaLogistica.objects.filter(evento=evento).order_by("fecha_objetivo", "id")
        return Response(SubtareaLogisticaSerializer(subtareas, many=True).data)

    datos = request.data.copy()
    datos["evento"] = evento.id
    serializer = SubtareaLogisticaSerializer(data=datos)
    if serializer.is_valid():
        subtarea = serializer.save()
        return Response(SubtareaLogisticaSerializer(subtarea).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH", "DELETE"])
def actualizar_subtarea(request, evento_id, subtarea_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    try:
        subtarea = SubtareaLogistica.objects.get(id=subtarea_id, evento=evento)
    except SubtareaLogistica.DoesNotExist:
        return Response(
            {"detail": "Subtarea no encontrada para este evento."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        subtarea.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SubtareaLogisticaSerializer(subtarea, data=request.data, partial=True)
    if serializer.is_valid():
        subtarea = serializer.save()
        return Response(SubtareaLogisticaSerializer(subtarea).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def progreso_evento(request, evento_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    total_subtareas = SubtareaLogistica.objects.filter(evento=evento).count()
    subtareas_ejecutadas = SubtareaLogistica.objects.filter(evento=evento, estado="EJECUTADA").count()
    progreso = 0 if total_subtareas == 0 else round((subtareas_ejecutadas / total_subtareas) * 100, 1)

    return Response(
        {
            "evento": evento.id,
            "nombre": evento.nombre,
            "total_subtareas": total_subtareas,
            "subtareas_ejecutadas": subtareas_ejecutadas,
            "progreso": progreso,
        }
    )


@api_view(["GET"])
def conflictos_evento(request, evento_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    subtareas = SubtareaLogistica.objects.filter(evento=evento).exclude(estado="EJECUTADA")
    fechas = subtareas.values_list("fecha_objetivo", flat=True).distinct().order_by("fecha_objetivo")
    limite = evento.organizador.limite_diario_horas
    conflictos = []

    for fecha in fechas:
        subtareas_fecha = list(subtareas.filter(fecha_objetivo=fecha))
        horas_planificadas = sum(subtarea.horas_estimadas for subtarea in subtareas_fecha)
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


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    correo = str(request.data.get("correo") or "").strip().lower()
    password = request.data.get("password") or ""
    organizador = Organizador.objects.filter(correo=correo).first() if correo else None
    clave_valida = (
        organizador is not None
        and organizador.password
        and check_password(password, organizador.password)
    )
    if not clave_valida:
        return Response({"detail": MENSAJE_CREDENCIALES}, status=status.HTTP_401_UNAUTHORIZED)

    sesion = Sesion.objects.create(organizador=organizador, token=secrets.token_urlsafe(32))
    return Response(
        {
            "token": sesion.token,
            "organizador": OrganizadorSerializer(organizador).data,
        }
    )


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def sesion_actual(request):
    if request.method == "DELETE":
        if request.auth is not None:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(OrganizadorSerializer(request.user).data)
