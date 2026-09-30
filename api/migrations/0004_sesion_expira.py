from datetime import timedelta

from django.utils import timezone
from django.db import migrations, models


def marcar_vigencia(apps, schema_editor):
    Sesion = apps.get_model("api", "Sesion")
    Sesion.objects.filter(expira_en__isnull=True).update(expira_en=timezone.now() + timedelta(hours=8))


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_login_local"),
    ]

    operations = [
        migrations.AddField(
            model_name="sesion",
            name="expira_en",
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(marcar_vigencia, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sesion",
            name="expira_en",
            field=models.DateTimeField(),
        ),
    ]
