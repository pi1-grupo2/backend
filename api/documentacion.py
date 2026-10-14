"""Descripción OpenAPI de los endpoints de la API.

Las vistas son funciones con @api_view, así que drf-spectacular no puede deducir qué
reciben ni qué devuelven. Aquí se le dice de forma explícita, para que Swagger muestre
el cuerpo de cada petición, las respuestas posibles y ejemplos que se pueden probar.
Se deja en un módulo aparte para que views.py siga leyéndose como lógica de negocio.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from .models import SubtareaLogistica
from .serializers import (
    EventoSerializer,
    OrganizadorSerializer,
    RegistroSerializer,
    SubtareaLogisticaSerializer,
)

ETIQUETA = "Avance y progreso"

ERROR_DETALLE = inline_serializer(
    name="ErrorDetalle",
    fields={"detail": serializers.CharField()},
)

ERROR_CON_CODIGO = inline_serializer(
    name="ErrorConCodigo",
    fields={"codigo": serializers.CharField(), "detail": serializers.CharField()},
)

CIFRAS_DEL_DIA = {
    "fecha": serializers.DateField(),
    "horas_planificadas": serializers.DecimalField(max_digits=5, decimal_places=1),
    "limite_diario_horas": serializers.DecimalField(max_digits=4, decimal_places=1),
    "exceso_horas": serializers.DecimalField(max_digits=5, decimal_places=1),
}

SOBRECARGA = inline_serializer(
    name="SobrecargaDiaria",
    fields={
        "codigo": serializers.CharField(),
        "detail": serializers.CharField(),
        "fecha_sugerida": serializers.DateField(allow_null=True),
        **CIFRAS_DEL_DIA,
    },
)

DIA_EXCEDIDO = inline_serializer(
    name="DiaExcedido",
    fields={"codigo": serializers.CharField(), "detail": serializers.CharField(), **CIFRAS_DEL_DIA},
)

CAMBIO_DE_GESTION = inline_serializer(
    name="CambioDeGestion",
    fields={
        # Mismas opciones del modelo, para que Swagger muestre un solo enum de estado.
        "estado": serializers.ChoiceField(
            choices=SubtareaLogistica._meta.get_field("estado").choices, required=False
        ),
        "fecha_objetivo": serializers.DateField(required=False),
        "horas_estimadas": serializers.DecimalField(max_digits=4, decimal_places=1, required=False),
        "nombre": serializers.CharField(required=False),
        "nota_posposicion": serializers.CharField(required=False, allow_null=True),
        "confirmar_sobrecarga": serializers.BooleanField(required=False),
    },
)

ACTUALIZAR_SUBTAREA = extend_schema(
    methods=["PATCH"],
    tags=[ETIQUETA],
    summary="Cambiar el estado, la fecha o las horas de una gestión",
    description=(
        "Registra el avance (US-09) y sirve también para reprogramar (Sprint 3). "
        "Todos los campos son opcionales: se envía solo lo que cambia.\n\n"
        "- Ejecutar: `estado` EJECUTADA. Deja de sumar horas en su día.\n"
        "- Posponer: `estado` POSPUESTA, con `nota_posposicion` y `fecha_objetivo` opcionales. "
        "Si llega fecha, debe ser posterior a la actual. Una gestión ejecutada no se pospone.\n"
        "- Si el día queda por encima del límite diario responde 409 y no guarda; "
        "con `confirmar_sobrecarga: true` guarda de todos modos. Más de 24 h nunca se guarda.\n"
        "- Cuando cambia la fecha o las horas, el 200 trae `carga_del_dia`."
    ),
    request=CAMBIO_DE_GESTION,
    responses={
        200: OpenApiResponse(SubtareaLogisticaSerializer, description="Gestión guardada."),
        400: OpenApiResponse(
            OpenApiTypes.OBJECT,
            description="Error por campo (`estado`, `fecha_objetivo`, `horas_estimadas`) "
            "o `codigo: dia_excedido` si el día pasaría de 24 h.",
        ),
        401: OpenApiResponse(ERROR_DETALLE, description="Sin sesión o sesión vencida."),
        404: OpenApiResponse(ERROR_DETALLE, description="El evento o la gestión no son de esta cuenta."),
        409: OpenApiResponse(SOBRECARGA, description="El día supera el límite diario. No se guardó."),
    },
    examples=[
        OpenApiExample("Marcar como ejecutada", value={"estado": "EJECUTADA"}, request_only=True),
        OpenApiExample(
            "Posponer con nota, sin mover la fecha",
            value={"estado": "POSPUESTA", "nota_posposicion": "Esperando confirmación del salón"},
            request_only=True,
        ),
        OpenApiExample(
            "Posponer a la fecha sugerida",
            value={
                "estado": "POSPUESTA",
                "fecha_objetivo": "2026-10-20",
                "nota_posposicion": "Esperando confirmación del salón",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Guardar aunque el día quede sobrecargado",
            value={"fecha_objetivo": "2026-10-20", "confirmar_sobrecarga": True},
            request_only=True,
        ),
    ],
)

ELIMINAR_SUBTAREA = extend_schema(
    methods=["DELETE"],
    tags=[ETIQUETA],
    summary="Eliminar una gestión",
    responses={204: None, 401: ERROR_DETALLE, 404: ERROR_DETALLE},
)

PROGRESO = extend_schema(
    tags=[ETIQUETA],
    summary="Progreso de preparación de un evento",
    description=(
        "US-10. Porcentaje de gestiones ejecutadas sobre el total del evento, con un decimal. "
        "Las pospuestas siguen contando en el total porque falta hacerlas. "
        "Sin gestiones, el progreso es 0. Se calcula en cada consulta, no se guarda."
    ),
    responses={
        200: inline_serializer(
            name="ProgresoEvento",
            fields={
                "evento": serializers.IntegerField(),
                "nombre": serializers.CharField(),
                "total_subtareas": serializers.IntegerField(),
                "subtareas_ejecutadas": serializers.IntegerField(),
                "subtareas_pospuestas": serializers.IntegerField(),
                "subtareas_pendientes": serializers.IntegerField(),
                "progreso": serializers.FloatField(),
            },
        ),
        401: ERROR_DETALLE,
        404: ERROR_DETALLE,
    },
)

SUGERENCIA_POSPONER = extend_schema(
    tags=[ETIQUETA],
    summary="Día más cercano con cupo para posponer una gestión",
    description=(
        "Busca desde el día siguiente a la fecha actual de la gestión (desde hoy si está vencida) "
        "hasta el día del evento, y devuelve el primero donde la gestión cabe sin pasar el límite "
        "diario. Suma las gestiones de todos los eventos del organizador y no cuenta las ejecutadas. "
        "Si ningún día sirve, `fecha_sugerida` es null. No guarda nada."
    ),
    responses={
        200: inline_serializer(
            name="SugerenciaPosponer",
            fields={
                "fecha_sugerida": serializers.DateField(allow_null=True),
                "horas_planificadas": serializers.DecimalField(
                    max_digits=5, decimal_places=1, allow_null=True
                ),
                "limite_diario_horas": serializers.DecimalField(max_digits=4, decimal_places=1),
                "busqueda_desde": serializers.DateField(),
                "busqueda_hasta": serializers.DateField(),
            },
        ),
        400: OpenApiResponse(ERROR_CON_CODIGO, description="`codigo: gestion_ejecutada`."),
        401: ERROR_DETALLE,
        404: ERROR_DETALLE,
    },
)


# ---------------------------------------------------------------------------
# Resto de la API (sesión, organizador, eventos y gestiones).
# ---------------------------------------------------------------------------

ETIQUETA_SESION = "Sesión"
ETIQUETA_ORGANIZADOR = "Organizador"
ETIQUETA_EVENTOS = "Eventos"
ETIQUETA_GESTIONES = "Gestiones"


class EventoEntradaSerializer(EventoSerializer):
    """Solo para el esquema: el organizador lo pone la vista con la sesión, no el cliente."""

    class Meta(EventoSerializer.Meta):
        fields = [campo for campo in EventoSerializer.Meta.fields if campo != "organizador"]


class GestionEntradaSerializer(SubtareaLogisticaSerializer):
    """Solo para el esquema: el evento sale de la URL, no del cuerpo."""

    class Meta(SubtareaLogisticaSerializer.Meta):
        fields = [campo for campo in SubtareaLogisticaSerializer.Meta.fields if campo != "evento"]


SESION_ABIERTA = inline_serializer(
    name="SesionAbierta",
    fields={
        "token": serializers.CharField(),
        "expira_en": serializers.DateTimeField(),
        "organizador": OrganizadorSerializer(),
    },
)

HEALTH = extend_schema(
    tags=[ETIQUETA_SESION],
    summary="Estado de la API y de la base de datos",
    auth=[],
    responses={
        200: inline_serializer(
            name="Health",
            fields={
                "estado": serializers.CharField(),
                "servicio": serializers.CharField(),
                "base_de_datos": serializers.CharField(),
            },
        )
    },
)

LOGIN = extend_schema(
    tags=[ETIQUETA_SESION],
    summary="Iniciar sesión",
    description=(
        "Devuelve el token que se envía en el encabezado `Authorization: Bearer <token>`. "
        "En Swagger se copia el token de la respuesta y se pega en el botón Authorize. "
        "El mensaje de error no dice si el correo existe, para no revelar cuentas."
    ),
    auth=[],
    request=inline_serializer(
        name="Credenciales",
        fields={"correo": serializers.EmailField(), "password": serializers.CharField()},
    ),
    responses={
        200: SESION_ABIERTA,
        401: OpenApiResponse(ERROR_DETALLE, description="Credenciales inválidas."),
    },
    examples=[
        OpenApiExample(
            "Credenciales",
            value={"correo": "nombre@correo.com", "password": "tu contraseña"},
            request_only=True,
        )
    ],
)

REGISTRO = extend_schema(
    tags=[ETIQUETA_SESION],
    summary="Crear una cuenta de organizador",
    description="Crea la cuenta con límite diario de 6 horas y deja la sesión iniciada.",
    auth=[],
    request=RegistroSerializer,
    responses={
        201: SESION_ABIERTA,
        400: OpenApiResponse(OpenApiTypes.OBJECT, description="Error por campo."),
        409: OpenApiResponse(ERROR_DETALLE, description="El correo ya tiene cuenta."),
    },
)

SESION_CONSULTAR = extend_schema(
    methods=["GET"],
    tags=[ETIQUETA_SESION],
    summary="Organizador de la sesión actual",
    responses={200: OrganizadorSerializer, 401: ERROR_DETALLE},
)

SESION_CERRAR = extend_schema(
    methods=["DELETE"],
    tags=[ETIQUETA_SESION],
    summary="Cerrar sesión",
    description="Invalida el token actual.",
    responses={204: None, 401: ERROR_DETALLE},
)

ORGANIZADOR_CONSULTAR = extend_schema(
    methods=["GET"],
    tags=[ETIQUETA_ORGANIZADOR],
    summary="Datos del organizador y su límite diario",
    responses={200: OrganizadorSerializer, 401: ERROR_DETALLE},
)

ORGANIZADOR_ACTUALIZAR = extend_schema(
    methods=["PATCH", "PUT"],
    tags=[ETIQUETA_ORGANIZADOR],
    summary="Cambiar el límite diario de horas",
    description="Entre 1 y 16, solo horas completas o medias (6 o 6.5). El correo no se puede cambiar.",
    request=inline_serializer(
        name="CambioDeLimite",
        fields={"limite_diario_horas": serializers.DecimalField(max_digits=4, decimal_places=1)},
    ),
    responses={
        200: OrganizadorSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, description="Error en limite_diario_horas."),
        401: ERROR_DETALLE,
    },
    examples=[OpenApiExample("Límite de 6 horas", value={"limite_diario_horas": 6}, request_only=True)],
)

EVENTOS_LISTAR = extend_schema(
    methods=["GET"],
    operation_id="eventos_listar",
    tags=[ETIQUETA_EVENTOS],
    summary="Eventos del organizador",
    responses={200: EventoSerializer(many=True), 401: ERROR_DETALLE},
)

EVENTOS_CREAR = extend_schema(
    methods=["POST"],
    operation_id="eventos_crear",
    tags=[ETIQUETA_EVENTOS],
    summary="Crear un evento",
    request=EventoEntradaSerializer,
    responses={
        201: EventoSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, description="Error por campo."),
        401: ERROR_DETALLE,
    },
)

EVENTO_CONSULTAR = extend_schema(
    methods=["GET"],
    operation_id="evento_detalle",
    tags=[ETIQUETA_EVENTOS],
    summary="Detalle de un evento",
    responses={200: EventoSerializer, 401: ERROR_DETALLE, 404: ERROR_DETALLE},
)

EVENTO_EDITAR = extend_schema(
    methods=["PATCH"],
    tags=[ETIQUETA_EVENTOS],
    summary="Editar un evento",
    request=EventoEntradaSerializer(partial=True),
    responses={
        200: EventoSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, description="Error por campo."),
        401: ERROR_DETALLE,
        404: ERROR_DETALLE,
    },
)

EVENTO_ELIMINAR = extend_schema(
    methods=["DELETE"],
    tags=[ETIQUETA_EVENTOS],
    summary="Eliminar un evento y sus gestiones",
    responses={204: None, 401: ERROR_DETALLE, 404: ERROR_DETALLE},
)

GESTIONES_LISTAR = extend_schema(
    methods=["GET"],
    tags=[ETIQUETA_GESTIONES],
    summary="Gestiones de un evento",
    description="Ordenadas por fecha. Cada una trae su estado, su nota y su situación (VENCIDA, PARA_HOY, PROXIMA o EJECUTADA).",
    responses={200: SubtareaLogisticaSerializer(many=True), 401: ERROR_DETALLE, 404: ERROR_DETALLE},
)

GESTIONES_CREAR = extend_schema(
    methods=["POST"],
    tags=[ETIQUETA_GESTIONES],
    summary="Agregar una gestión al plan del evento",
    request=GestionEntradaSerializer,
    responses={
        201: SubtareaLogisticaSerializer,
        400: OpenApiResponse(OpenApiTypes.OBJECT, description="Error por campo."),
        401: ERROR_DETALLE,
        404: ERROR_DETALLE,
    },
)

CONFLICTOS = extend_schema(
    tags=[ETIQUETA_GESTIONES],
    summary="Días del evento por encima del límite diario",
    description="Suma por organizador, igual que la revisión de sobrecarga. No cuenta las ejecutadas.",
    responses={
        200: inline_serializer(
            name="ConflictosEvento",
            fields={
                "evento": serializers.IntegerField(),
                "tiene_conflictos": serializers.BooleanField(),
                "conflictos": inline_serializer(
                    name="ConflictoDelDia",
                    many=True,
                    fields={
                        **CIFRAS_DEL_DIA,
                        "subtareas": inline_serializer(
                            name="GestionEnConflicto",
                            many=True,
                            fields={
                                "id": serializers.IntegerField(),
                                "nombre": serializers.CharField(),
                                "horas_estimadas": serializers.DecimalField(max_digits=4, decimal_places=1),
                                "estado": serializers.CharField(),
                            },
                        ),
                    },
                ),
            },
        ),
        401: ERROR_DETALLE,
        404: ERROR_DETALLE,
    },
)
