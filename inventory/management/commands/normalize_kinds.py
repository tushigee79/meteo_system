# -*- coding: utf-8 -*-
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Device, Location, InstrumentCatalog

CANONICAL = {
    "WEATHER",
    "HYDRO",
    "AWS",
    "ETALON",
    "RADAR",
    "AEROLOGY",
    "AGRO",
    "OTHER",
}

ALIASES = {
    # Location/Device kind aliases seen in imports / older specs
    "METEO": "WEATHER",
    "MET": "WEATHER",
    "Meteo": "WEATHER",
    "weather": "WEATHER",
    "hydro": "HYDRO",
    "aws": "AWS",
    "radar": "RADAR",
    "aerology": "AEROLOGY",
    "agro": "AGRO",
    "etalon": "ETALON",
}

def normalize(value: str | None) -> str | None:
    if value is None:
        return None
    v = (value or "").strip()
    if not v:
        return v
    up = v.upper()
    if up in CANONICAL:
        return up
    if up in ALIASES:
        return ALIASES[up]
    # Try: if stored as label text -> fallback OTHER
    return "OTHER"


class Command(BaseCommand):
    help = "Normalize Device.kind / Location.location_type / InstrumentCatalog.kind to canonical 8 kinds."

    @transaction.atomic
    def handle(self, *args, **options):
        total_updates = 0

        for obj in Device.objects.all().only("id", "kind"):
            new = normalize(getattr(obj, "kind", None))
            if new is not None and obj.kind != new:
                Device.objects.filter(pk=obj.pk).update(kind=new)
                total_updates += 1

        for obj in Location.objects.all().only("id", "location_type"):
            new = normalize(getattr(obj, "location_type", None))
            if new is not None and obj.location_type != new:
                Location.objects.filter(pk=obj.pk).update(location_type=new)
                total_updates += 1

        for obj in InstrumentCatalog.objects.all().only("id", "kind"):
            new = normalize(getattr(obj, "kind", None))
            if new is not None and obj.kind != new:
                InstrumentCatalog.objects.filter(pk=obj.pk).update(kind=new)
                total_updates += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Updated rows: {total_updates}"))
