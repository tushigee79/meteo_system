# inventory/migrations/0060_fill_instrument_units.py
from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    InstrumentCatalog = apps.get_model("inventory", "InstrumentCatalog")

    unit_map = {
        "TEMP": "Â°C",
        "HUM": "%",
        "PRESS": "hPa",
        "WIND": "m/s",
        "PRECIP": "mm",
        "RAD": "W/mÂ²",
        "EVAP": "mm",
        "HYDRO_LEVEL": "m",   # Ñ…Ò¯ÑÐ²ÑÐ» 'cm'
        "HYDRO_FLOW": "mÂ³/s",
        "AWS_ELEC": "-",
        "OTHER": "-",
    }

    updated = 0
    for kind, unit in unit_map.items():
        updated += InstrumentCatalog.objects.filter(kind=kind, unit="").update(unit=unit)

    # Migration Ò¯ÐµÐ´ print Ñ…Ð°Ñ€Ð°Ð³Ð´Ð°Ñ…Ð³Ò¯Ð¹ Ð±Ð°Ð¹Ð¶ Ð±Ð¾Ð»Ð½Ð¾ (OK)
    # print("UPDATED:", updated)


def backwards(apps, schema_editor):
    InstrumentCatalog = apps.get_model("inventory", "InstrumentCatalog")
    # Ð±ÑƒÑ†Ð°Ð°Ñ…Ð°Ð´ unit-Ð¸Ð¹Ð³ Ñ…Ð¾Ð¾ÑÐ»Ð¾Ð½Ð¾ (Ð·Ó©Ð²Ñ…Ó©Ð½ Ð±Ð¸Ð´Ð½Ð¸Ð¹ Ð±Ó©Ð³Ð»Ó©ÑÓ©Ð½ Ñ„Ð¾Ñ€Ð¼Ð°Ñ‚ÑƒÑƒÐ´ Ð´ÑÑÑ€)
    allowed = {"Â°C", "%", "hPa", "m/s", "mm", "W/mÂ²", "m", "mÂ³/s", "-"}
    InstrumentCatalog.objects.filter(unit__in=allowed).update(unit="")


class Migration(migrations.Migration):
    dependencies = [
    ("inventory", "0053_merge_20260209_1038"),
]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

