from django.db import migrations


def crear_organizador_demo(apps, schema_editor):
    Organizador = apps.get_model("api", "Organizador")
    if Organizador.objects.filter(identidad_externa="demo").exists():
        return
    Organizador.objects.create(
        nombre="Natalia",
        identidad_externa="demo",
        limite_diario_horas=6,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_organizador_demo, migrations.RunPython.noop),
    ]
