from django.utils import timezone
from rest_framework import serializers

from .models import Evento, Organizador, SubtareaLogistica

OBLIGATORIO = "Este campo es obligatorio para planificar el evento."
HORAS_INVALIDAS = "Las horas estimadas deben ser un valor mayor a 0 (ej. 1.5, 3)."
FECHA_EVENTO = "La fecha del evento debe ser posterior al día de hoy."
FECHA_GESTION = "El plazo de la gestión logística no puede ser posterior a la fecha del evento."
LIMITE_HORAS = "Las horas de gestión deben ser un valor entre 1 y 16."


class OrganizadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizador
        fields = [
            "id",
            "nombre",
            "identidad_externa",
            "limite_diario_horas",
            "creado_en",
        ]
        read_only_fields = ["id", "identidad_externa", "creado_en"]

    def validate_limite_diario_horas(self, value):
        if value < 1 or value > 16:
            raise serializers.ValidationError(LIMITE_HORAS)
        return value


class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evento
        fields = [
            "id",
            "organizador",
            "nombre",
            "tipo",
            "cliente_contacto",
            "fecha_hora_evento",
            "lugar",
            "plazo_limite",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]
        extra_kwargs = {
            "nombre": {"error_messages": {"blank": OBLIGATORIO, "required": OBLIGATORIO}},
            "tipo": {"error_messages": {"blank": OBLIGATORIO, "required": OBLIGATORIO, "invalid_choice": OBLIGATORIO}},
            "cliente_contacto": {"error_messages": {"blank": OBLIGATORIO, "required": OBLIGATORIO}},
            "fecha_hora_evento": {"error_messages": {"required": OBLIGATORIO, "invalid": FECHA_EVENTO}},
            "lugar": {"error_messages": {"blank": OBLIGATORIO, "required": OBLIGATORIO}},
            "plazo_limite": {"error_messages": {"required": OBLIGATORIO, "invalid": FECHA_EVENTO}},
            "organizador": {"error_messages": {"required": OBLIGATORIO}},
        }

    def validate_fecha_hora_evento(self, value):
        fecha = timezone.localtime(value).date()
        if fecha <= timezone.localdate():
            raise serializers.ValidationError(FECHA_EVENTO)
        return value


class SubtareaLogisticaSerializer(serializers.ModelSerializer):
    situacion = serializers.SerializerMethodField()

    class Meta:
        model = SubtareaLogistica
        fields = [
            "id",
            "evento",
            "nombre",
            "fecha_objetivo",
            "horas_estimadas",
            "estado",
            "nota_posposicion",
            "situacion",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = [
            "id",
            "situacion",
            "creado_en",
            "actualizado_en",
        ]
        extra_kwargs = {
            "nombre": {"error_messages": {"blank": "El nombre de la gestión es obligatorio.", "required": "El nombre de la gestión es obligatorio."}},
            "fecha_objetivo": {"error_messages": {"required": "La fecha objetivo es obligatoria.", "invalid": FECHA_GESTION}},
            "horas_estimadas": {"error_messages": {"required": HORAS_INVALIDAS, "invalid": HORAS_INVALIDAS}},
        }

    def get_situacion(self, obj):
        if obj.estado == "EJECUTADA":
            return "EJECUTADA"

        hoy = timezone.localdate()

        if obj.fecha_objetivo < hoy:
            return "VENCIDA"

        if obj.fecha_objetivo == hoy:
            return "PARA_HOY"

        return "PROXIMA"

    def validate_horas_estimadas(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(HORAS_INVALIDAS)
        return value

    def validate(self, attrs):
        fecha = attrs.get("fecha_objetivo", getattr(self.instance, "fecha_objetivo", None))
        evento = attrs.get("evento", getattr(self.instance, "evento", None))

        if fecha and evento is not None:
            limite = timezone.localtime(evento.fecha_hora_evento).date()
            if fecha > limite:
                raise serializers.ValidationError({"fecha_objetivo": FECHA_GESTION})

        return attrs
