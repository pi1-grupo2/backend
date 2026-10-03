from django.utils import timezone
from rest_framework import serializers

from .models import Evento, Organizador, SubtareaLogistica

OBLIGATORIO = "Este campo es obligatorio para planificar el evento."
HORAS_INVALIDAS = "Las horas estimadas deben ser un valor mayor a 0 (ej. 1.5, 3)."
FECHA_EVENTO = "La fecha del evento debe ser posterior al día de hoy."
FECHA_GESTION = "El plazo de la gestión logística no puede ser posterior a la fecha del evento."
LIMITE_HORAS = "Las horas de gestión deben ser un valor entre 1 y 16."
LIMITE_MEDIAS_HORAS = "El límite se define en horas completas o medias (ej. 6 o 6.5)."
FECHA_PASADA = "La nueva fecha no puede ser anterior al día de hoy."

# Los textos de registro repiten los que ya muestra Registro.jsx,
# para que el mismo error se lea igual venga del formulario o de la API.
FALTA_NOMBRE = "Falta el nombre."
FALTA_CORREO = "Falta el correo electrónico."
FORMATO_CORREO = "El correo debe tener el formato nombre@correo.com."
FALTA_PASSWORD = "Falta la contraseña."
PASSWORD_CORTA = "La contraseña debe tener al menos 8 caracteres."
PASSWORD_LARGA = "La contraseña no puede tener más de 128 caracteres."
NOMBRE_LARGO = "El nombre no puede tener más de 150 caracteres."


class OrganizadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizador
        fields = [
            "id",
            "nombre",
            "identidad_externa",
            "correo",
            "limite_diario_horas",
            "creado_en",
        ]
        read_only_fields = ["id", "identidad_externa", "correo", "creado_en"]

    def validate_limite_diario_horas(self, value):
        if value < 1 or value > 16:
            raise serializers.ValidationError(LIMITE_HORAS)
        # Mismo paso de 0,5 que usan las horas de las gestiones en el formulario.
        if (value * 2) % 1 != 0:
            raise serializers.ValidationError(LIMITE_MEDIAS_HORAS)
        return value


class RegistroSerializer(serializers.Serializer):
    """Valida los datos para crear una cuenta. No guarda nada: eso lo hace la vista."""

    nombre = serializers.CharField(
        max_length=150,
        error_messages={
            "required": FALTA_NOMBRE,
            "blank": FALTA_NOMBRE,
            "null": FALTA_NOMBRE,
            "max_length": NOMBRE_LARGO,
        },
    )
    correo = serializers.EmailField(
        max_length=254,
        error_messages={
            "required": FALTA_CORREO,
            "blank": FALTA_CORREO,
            "null": FALTA_CORREO,
            "invalid": FORMATO_CORREO,
            "max_length": FORMATO_CORREO,
        },
    )
    # trim_whitespace=False: un espacio al inicio o al final es parte de la contraseña.
    password = serializers.CharField(
        min_length=8,
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "required": FALTA_PASSWORD,
            "blank": FALTA_PASSWORD,
            "null": FALTA_PASSWORD,
            "min_length": PASSWORD_CORTA,
            "max_length": PASSWORD_LARGA,
        },
    )

    def validate_correo(self, value):
        # El login busca el correo en minúsculas. Se guarda igual para que coincidan.
        return value.strip().lower()


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

        # Reprogramar hacia el pasado no tiene sentido. Solo se revisa cuando la fecha
        # cambia: una gestión vencida debe poder marcarse como ejecutada sin tocarla.
        nueva_fecha = attrs.get("fecha_objetivo")
        if (
            self.instance is not None
            and nueva_fecha is not None
            and nueva_fecha != self.instance.fecha_objetivo
            and nueva_fecha < timezone.localdate()
        ):
            raise serializers.ValidationError({"fecha_objetivo": FECHA_PASADA})

        return attrs
