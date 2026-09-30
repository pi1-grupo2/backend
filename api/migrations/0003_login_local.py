from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion


def asignar_acceso_demo(apps, schema_editor):
    Organizador = apps.get_model("api", "Organizador")
    demo = Organizador.objects.filter(identidad_externa="demo").first()
    acceso = {
        "correo": "natalia@demo.com",
        "password": make_password("EventFlow2026"),
    }
    if demo is None:
        Organizador.objects.create(
            nombre="Natalia",
            identidad_externa="demo",
            limite_diario_horas=6,
            **acceso,
        )
        return
    demo.correo = acceso["correo"]
    demo.password = acceso["password"]
    demo.save(update_fields=["correo", "password"])


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_organizador_demo"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizador",
            name="correo",
            field=models.EmailField(max_length=254, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="organizador",
            name="password",
            field=models.CharField(default="", max_length=128),
        ),
        migrations.CreateModel(
            name="Sesion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=64, unique=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "organizador",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sesiones",
                        to="api.organizador",
                    ),
                ),
            ],
            options={"db_table": "sesion"},
        ),
        migrations.RunPython(asignar_acceso_demo, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organizador",
            name="correo",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name="organizador",
            name="password",
            field=models.CharField(max_length=128),
        ),
    ]
