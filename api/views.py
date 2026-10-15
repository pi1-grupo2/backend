from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Q

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import documentacion
from .autenticacion import MENSAJE_CREDENCIALES, crear_sesion
from .carga import (
    carga_guardada,
    dias_sobrecargados,
    evaluar_carga,
    fecha_del_evento,
    formatear_horas,
    horas_planificadas,
    primer_dia_para_posponer,
    sugerir_fecha,
)
from .models import Evento, Organizador, SubtareaLogistica
from .serializers import (
    POSPONER_EJECUTADA,
    EventoSerializer,
    OrganizadorSerializer,
    RegistroSerializer,
    SubtareaLogisticaSerializer,
)

# Mismo texto que muestra Registro.jsx cuando el correo ya tiene cuenta.
MENSAJE_CORREO_NO_DISPONIBLE = "No fue posible crear la cuenta con este correo."

MENSAJE_DIA_EXCEDIDO = "Un día no puede tener más de 24 horas de gestión planificadas."
VALORES_DE_CONFIRMACION = (True, "true", "True", "1", 1)


def _respuesta_sesion(organizador, codigo=status.HTTP_200_OK):
    """Abre una sesión y arma la respuesta que el frontend guarda tal cual."""
    sesion = crear_sesion(organizador)
    return Response(
        {
            "token": sesion.token,
            "expira_en": sesion.expira_en,
            "organizador": OrganizadorSerializer(organizador).data,
        },
        status=codigo,
    )


@documentacion.HEALTH
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


@documentacion.ORGANIZADOR_CONSULTAR
@documentacion.ORGANIZADOR_ACTUALIZAR
@api_view(["GET", "PATCH", "PUT"])
def organizador_actual(request):
    organizador = request.user

    if request.method == "GET":
        return Response(OrganizadorSerializer(organizador).data)

    # PUT y PATCH actualizan el límite. El resto de la cuenta es de solo lectura,
    # así que no se exige reenviar nombre ni correo.
    serializer = OrganizadorSerializer(organizador, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    nuevo = serializer.validated_data.get("limite_diario_horas", organizador.limite_diario_horas)
    anterior = organizador.limite_diario_horas
    dias = _dias_con_limite(organizador, nuevo)

    # Solo bajar el límite puede crear sobrecargas nuevas. Subirlo nunca pide confirmación,
    # aunque queden días por encima: el cambio los alivia.
    confirmado = request.data.get("confirmar_sobrecarga") in VALORES_DE_CONFIRMACION
    if dias and nuevo < anterior and not confirmado:
        return Response(
            {
                "codigo": "sobrecarga_por_limite",
                "detail": _texto_dias_por_encima(nuevo, len(dias)),
                "limite_diario_horas": nuevo,
                "limite_actual": anterior,
                "dias": dias,
            },
            status=status.HTTP_409_CONFLICT,
        )

    serializer.save()
    return Response({**serializer.data, "dias_sobrecargados": dias})


def _dias_con_limite(organizador, limite):
    """Días sobrecargados si el organizador tuviera este límite. No guarda nada."""
    anterior = organizador.limite_diario_horas
    organizador.limite_diario_horas = limite
    try:
        return dias_sobrecargados(organizador)
    finally:
        organizador.limite_diario_horas = anterior


def _texto_dias_por_encima(limite, cantidad):
    dias = "1 día quedaría" if cantidad == 1 else f"{cantidad} días quedarían"
    return f"Con un límite de {formatear_horas(limite)}h, {dias} por encima del límite."


@documentacion.SOBRECARGA_ORGANIZADOR
@api_view(["GET"])
def sobrecarga_organizador(request):
    """Días desde hoy por encima del límite, en todos los eventos del organizador.

    Con ?limite=4 revisa ese límite sin guardarlo, para avisar en Configuración
    antes de que el organizador confirme el cambio.
    """
    organizador = request.user
    limite = organizador.limite_diario_horas
    if "limite" in request.query_params:
        prueba = OrganizadorSerializer(
            organizador,
            data={"limite_diario_horas": request.query_params["limite"]},
            partial=True,
        )
        if not prueba.is_valid():
            return Response(prueba.errors, status=status.HTTP_400_BAD_REQUEST)
        limite = prueba.validated_data["limite_diario_horas"]

    dias = _dias_con_limite(organizador, limite)
    return Response({"limite_diario_horas": limite, "tiene_sobrecarga": bool(dias), "dias": dias})


@documentacion.EVENTOS_LISTAR
@documentacion.EVENTOS_CREAR
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


@documentacion.EVENTO_CONSULTAR
@documentacion.EVENTO_EDITAR
@documentacion.EVENTO_ELIMINAR
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


@documentacion.GESTIONES_LISTAR
@documentacion.GESTIONES_CREAR
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
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Una gestión nueva ocupa horas en su día igual que una reprogramada,
    # así que pasa por la misma revisión. Si nace ejecutada, no ocupa nada.
    validados = serializer.validated_data
    cuenta = validados.get("estado", "PENDIENTE") != "EJECUTADA"
    if cuenta:
        fecha = validados["fecha_objetivo"]
        horas = validados["horas_estimadas"]
        carga = evaluar_carga(request.user, fecha, horas)
        if carga["supera_dia"]:
            return _respuesta_dia_excedido(carga)
        confirmado = request.data.get("confirmar_sobrecarga") in VALORES_DE_CONFIRMACION
        if carga["supera_limite"] and not confirmado:
            return _respuesta_sobrecarga(carga, sugerir_fecha(request.user, evento, fecha, horas))

    subtarea = serializer.save()
    cuerpo = SubtareaLogisticaSerializer(subtarea).data
    if cuenta:
        cuerpo["carga_del_dia"] = carga_guardada(request.user, subtarea.fecha_objetivo)
    return Response(cuerpo, status=status.HTTP_201_CREATED)


@documentacion.ACTUALIZAR_SUBTAREA
@documentacion.ELIMINAR_SUBTAREA
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
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    conflicto = _revisar_sobrecarga(request, subtarea, serializer.validated_data)
    if conflicto is not None:
        return conflicto

    fecha_anterior = subtarea.fecha_objetivo
    horas_anteriores = subtarea.horas_estimadas
    subtarea = serializer.save()
    cuerpo = SubtareaLogisticaSerializer(subtarea).data
    cambio_de_carga = subtarea.estado != "EJECUTADA" and (
        subtarea.fecha_objetivo != fecha_anterior or subtarea.horas_estimadas != horas_anteriores
    )
    if cambio_de_carga:
        cuerpo["carga_del_dia"] = carga_guardada(request.user, subtarea.fecha_objetivo)
    return Response(cuerpo)


def _revisar_sobrecarga(request, subtarea, datos):
    """Devuelve la respuesta de conflicto si el cambio sobrecarga el día. Si no, None.

    Se revisa cuando una gestión que queda sin ejecutar cambia de fecha o de horas,
    o cuando deja de estar ejecutada y vuelve a ocupar tiempo en su día.
    Cambiar el nombre o marcarla como ejecutada no pasa por aquí.
    """
    fecha = datos.get("fecha_objetivo", subtarea.fecha_objetivo)
    horas = datos.get("horas_estimadas", subtarea.horas_estimadas)
    estado = datos.get("estado", subtarea.estado)

    cambia_fecha = fecha != subtarea.fecha_objetivo
    cambia_horas = horas != subtarea.horas_estimadas
    vuelve_a_contar = subtarea.estado == "EJECUTADA" and estado != "EJECUTADA"
    if estado == "EJECUTADA" or not (cambia_fecha or cambia_horas or vuelve_a_contar):
        return None

    carga = evaluar_carga(request.user, fecha, horas, excluir_id=subtarea.id)

    # Reducir horas sin mover la gestión siempre alivia el día. No se bloquea aunque
    # el día siga por encima de 24 h: sería impedirle al usuario arreglar el problema.
    solo_reduce = not cambia_fecha and not vuelve_a_contar and horas < subtarea.horas_estimadas
    if carga["supera_dia"] and not solo_reduce:
        return _respuesta_dia_excedido(carga)

    confirmado = request.data.get("confirmar_sobrecarga") in VALORES_DE_CONFIRMACION
    if carga["supera_limite"] and not confirmado:
        fecha_sugerida = sugerir_fecha(
            request.user,
            subtarea.evento,
            fecha,
            horas,
            excluir_id=subtarea.id,
            # Al posponer, sugerir un día anterior llevaría a otro error.
            desde=primer_dia_para_posponer(subtarea) if estado == "POSPUESTA" else None,
        )
        return _respuesta_sobrecarga(carga, fecha_sugerida)

    return None


def _cifras(carga):
    return {
        "fecha": carga["fecha"],
        "horas_planificadas": carga["horas_planificadas"],
        "limite_diario_horas": carga["limite_diario_horas"],
        "exceso_horas": carga["exceso_horas"],
    }


def _respuesta_dia_excedido(carga):
    return Response(
        {"codigo": "dia_excedido", "detail": MENSAJE_DIA_EXCEDIDO, **_cifras(carga)},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _respuesta_sobrecarga(carga, fecha_sugerida):
    detalle = (
        f"Quedarías con {formatear_horas(carga['horas_planificadas'])}h de gestión "
        f"planificadas (límite {formatear_horas(carga['limite_diario_horas'])}h)"
    )
    return Response(
        {"codigo": "sobrecarga_diaria", "detail": detalle, "fecha_sugerida": fecha_sugerida, **_cifras(carga)},
        status=status.HTTP_409_CONFLICT,
    )


@documentacion.SUGERENCIA_POSPONER
@api_view(["GET"])
def sugerencia_posponer(request, evento_id, subtarea_id):
    """Día más cercano, después de la fecha actual, donde la gestión cabe sin pasar el límite.

    El diálogo de posponer la pide antes de guardar, para ofrecer esa fecha como opción
    principal. No guarda nada. Busca hasta el día del evento.
    """
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

    if subtarea.estado == "EJECUTADA":
        return Response(
            {"codigo": "gestion_ejecutada", "detail": POSPONER_EJECUTADA},
            status=status.HTTP_400_BAD_REQUEST,
        )

    desde = primer_dia_para_posponer(subtarea)
    fecha = sugerir_fecha(
        request.user,
        evento,
        subtarea.fecha_objetivo,
        subtarea.horas_estimadas,
        excluir_id=subtarea.id,
        desde=desde,
    )
    horas_del_dia = None
    if fecha is not None:
        horas_del_dia = evaluar_carga(
            request.user, fecha, subtarea.horas_estimadas, excluir_id=subtarea.id
        )["horas_planificadas"]

    return Response(
        {
            "fecha_sugerida": fecha,
            "horas_planificadas": horas_del_dia,
            "limite_diario_horas": request.user.limite_diario_horas,
            "busqueda_desde": desde,
            "busqueda_hasta": fecha_del_evento(evento),
        }
    )


@documentacion.PROGRESO
@api_view(["GET"])
def progreso_evento(request, evento_id):
    evento, error = _obtener_evento(evento_id, request.user)
    if error:
        return error

    # Una sola consulta cuenta todo. Las pospuestas siguen en el total: falta hacerlas.
    conteo = SubtareaLogistica.objects.filter(evento=evento).aggregate(
        total=Count("id"),
        ejecutadas=Count("id", filter=Q(estado="EJECUTADA")),
        pospuestas=Count("id", filter=Q(estado="POSPUESTA")),
    )
    total = conteo["total"]
    ejecutadas = conteo["ejecutadas"]
    progreso = 0 if total == 0 else round((ejecutadas / total) * 100, 1)

    return Response(
        {
            "evento": evento.id,
            "nombre": evento.nombre,
            "total_subtareas": total,
            "subtareas_ejecutadas": ejecutadas,
            "subtareas_pospuestas": conteo["pospuestas"],
            "subtareas_pendientes": total - ejecutadas - conteo["pospuestas"],
            "progreso": progreso,
        }
    )


@documentacion.CONFLICTOS
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
        # El límite es del organizador: el día se suma con las gestiones de todos sus eventos.
        horas_del_dia = horas_planificadas(evento.organizador, fecha)
        if horas_del_dia > limite:
            conflictos.append(
                {
                    "fecha": fecha,
                    "horas_planificadas": horas_del_dia,
                    "limite_diario_horas": limite,
                    "exceso_horas": horas_del_dia - limite,
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


@documentacion.LOGIN
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

    return _respuesta_sesion(organizador)


@documentacion.REGISTRO
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def registro(request):
    """Crea una cuenta de organizador y la deja con la sesión iniciada."""
    serializer = RegistroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    datos = serializer.validated_data
    correo_en_uso = Response(
        {"detail": MENSAJE_CORREO_NO_DISPONIBLE},
        status=status.HTTP_409_CONFLICT,
    )
    if Organizador.objects.filter(correo=datos["correo"]).exists():
        return correo_en_uso

    try:
        # atomic: si la base rechaza el correo por duplicado, no queda nada a medias.
        with transaction.atomic():
            organizador = Organizador.objects.create(
                nombre=datos["nombre"],
                correo=datos["correo"],
                password=make_password(datos["password"]),
            )
    except IntegrityError:
        # Dos registros con el mismo correo al mismo tiempo: gana el primero.
        return correo_en_uso

    return _respuesta_sesion(organizador, status.HTTP_201_CREATED)


@documentacion.SESION_CONSULTAR
@documentacion.SESION_CERRAR
@api_view(["GET", "DELETE"])
def sesion_actual(request):
    if request.method == "DELETE":
        if request.auth is not None:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(OrganizadorSerializer(request.user).data)
