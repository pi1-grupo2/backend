"""Descripción OpenAPI de los endpoints de estado, progreso y sugerencia (Sprint 4).

Las vistas son funciones con @api_view, así que drf-spectacular no puede deducir qué
reciben ni qué devuelven. Aquí se le dice de forma explícita, para que Swagger muestre
el cuerpo de cada petición, las respuestas posibles y ejemplos que se pueden probar.
Se deja en un módulo aparte para que views.py siga leyéndose como lógica de negocio.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from .serializers import SubtareaLogisticaSerializer

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
        "estado": serializers.ChoiceField(
            choices=["PENDIENTE", "EJECUTADA", "POSPUESTA"], required=False
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
