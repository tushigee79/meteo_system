# inventory/migrations/0060_fill_instrument_units.py
from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):
    InstrumentCatalog = apps.get_model("inventory", "InstrumentCatalog")

    unit_map = {
        "TEMP": "°C",
        "HUM": "%",
        "PRESS": "hPa",
        "WIND": "m/s",
        "PRECIP": "mm",
        "RAD": "W/m²",
        "EVAP": "mm",
        "HYDRO_LEVEL": "m",   # хүсвэл 'cm'
        "HYDRO_FLOW": "m³/s",
        "AWS_ELEC": "-",
        "OTHER": "-",
    }

    updated = 0
    for kind, unit in unit_map.items():
        updated += InstrumentCatalog.objects.filter(kind=kind, unit="").update(unit=unit)

    # Migration үед print харагдахгүй байж болно (OK)
    # print("UPDATED:", updated)


def backwards(apps, schema_editor):
    InstrumentCatalog = apps.get_model("inventory", "InstrumentCatalog")
    # буцаахад unit-ийг хоослоно (зөвхөн бидний бөглөсөн форматууд дээр)
    allowed = {"°C", "%", "hPa", "m/s", "mm", "W/m²", "m", "m³/s", "-"}
    InstrumentCatalog.objects.filter(unit__in=allowed).update(unit="")


class Migration(migrations.Migration):
    dependencies = [
    ("inventory", "0053_merge_20260209_1038"),
]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
