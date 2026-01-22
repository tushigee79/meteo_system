import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import InstrumentCatalog

KIND_MAP = {
    "Эталон": "ETALON",
    "Цаг уур": "WEATHER",
    "Ус судлал": "HYDRO",
    "Хөдөө аж ахуй": "AGRI",
    "Радарын станц": "RADAR",
    "Аэрологийн станц": "AEROLOGY",
    "Цаг уурын автомат станц (AWS)": "AWS",
    "Бусад": "OTHER",
}

class Command(BaseCommand):
    help = "Import/update InstrumentCatalog from CSV (instrument_catalog_expanded.csv)"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["csv_path"]
        created, updated = 0, 0

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                code = (row.get("code") or "").strip()
                name_mn = (row.get("name_mn") or "").strip()
                kind_raw = (row.get("kind") or row.get("category") or "").strip()

                kind = KIND_MAP.get(kind_raw, None)
                if not kind:
                    # category->kind fallback
                    kind = "WEATHER"

                if not name_mn:
                    continue

                obj, is_created = InstrumentCatalog.objects.update_or_create(
                    kind=kind,
                    name_mn=name_mn,
                    defaults={
                        "code": code,
                        "is_active": True,
                    }
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}"))
