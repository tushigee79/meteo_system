# inventory/migrations/0016_location_type_normalize.py
from django.db import migrations


def forwards(apps, schema_editor):
    Location = apps.get_model("inventory", "Location")

    # METEO -> WEATHER
    Location.objects.filter(location_type="METEO").update(location_type="WEATHER")

    # хоосон/NULL/“-” -> OTHER
    Location.objects.filter(location_type__in=["", "-", None]).update(location_type="OTHER")


def backwards(apps, schema_editor):
    Location = apps.get_model("inventory", "Location")
    Location.objects.filter(location_type="WEATHER").update(location_type="METEO")


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0015_alter_device_kind_alter_instrumentcatalog_kind_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
