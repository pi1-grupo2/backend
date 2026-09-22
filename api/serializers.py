from datetime import date
from rest_framework import serializers

from .models import Evento, SubtareaLogistica


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
        read_only_fields = [
            "id",
            "creado_en",
            "actualizado_en",
        ]

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

    def get_situacion(self, obj):
        if obj.estado == "EJECUTADA":
            return "EJECUTADA"

        hoy = date.today()

        if obj.fecha_objetivo < hoy:
            return "VENCIDA"

        if obj.fecha_objetivo == hoy:
            return "PARA_HOY"

        return "PROXIMA"