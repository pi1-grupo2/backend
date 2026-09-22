from django.db import models


class Organizador(models.Model):
    nombre = models.CharField(max_length=150)
    identidad_externa = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    limite_diario_horas = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=6.0,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organizador"

    def __str__(self):
        return self.nombre


class Evento(models.Model):
    TIPOS_EVENTO = [
        ("boda", "Boda"),
        ("social", "Social"),
        ("corporativo", "Corporativo"),
        ("cumpleanos", "Cumpleaños"),
        ("otro", "Otro"),
    ]

    organizador = models.ForeignKey(
        Organizador,
        on_delete=models.CASCADE,
        related_name="eventos",
    )
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPOS_EVENTO)
    cliente_contacto = models.CharField(max_length=255)
    fecha_hora_evento = models.DateTimeField()
    lugar = models.CharField(max_length=255)
    plazo_limite = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evento"

    def __str__(self):
        return self.nombre


class SubtareaLogistica(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("EJECUTADA", "Ejecutada"),
        ("POSPUESTA", "Pospuesta"),
    ]

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="subtareas",
    )
    nombre = models.CharField(max_length=200)
    fecha_objetivo = models.DateField()
    horas_estimadas = models.DecimalField(
        max_digits=5,
        decimal_places=1,
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default="PENDIENTE",
    )
    nota_posposicion = models.TextField(
        null=True,
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subtarea_logistica"

    def __str__(self):
        return self.nombre
