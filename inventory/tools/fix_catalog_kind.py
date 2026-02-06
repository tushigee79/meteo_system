# tools/fix_catalog_kind.py
import os
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meteo_config.settings")

import django
django.setup()

from django.db import transaction
from inventory.models import InstrumentCatalog

def guess_kind(name_mn: str, code: str, old_kind: str) -> str:
    text = f"{name_mn or ''} {code or ''} {old_kind or ''}".lower()

    # илүү хүчтэй түлхүүрүүд
    if "радар" in text or "radar" in text:
        return "RADAR"
    if "аэролог" in text or "aerolog" in text or "upper air" in text:
        return "AEROLOGY"
    if "aws" in text or "автомат" in text or "automatic" in text:
        return "AWS"
    if "ус" in text or "hydro" in text or "гол" in text:
        return "HYDRO"
    if "агро" in text or "хөдөө" in text or "agri" in text:
        return "AGRI"

    # хуучин том ангиллууд
    if (old_kind or "").strip() in ("Эталон",):
        return "ETALON"
    if (old_kind or "").strip() in ("Бусад",):
        return "OTHER"

    # үлдсэнийг цаг уур гэж үзнэ
    return "WEATHER"


def main():
    qs = InstrumentCatalog.objects.all()

    before = sorted(set(qs.values_list("kind", flat=True)))
    print("Before kinds:", before)

    updated = 0
    with transaction.atomic():
        for ic in qs:
            old = (ic.kind or "").strip()
            # аль хэдийн enum болсон бол алгас
            if old in {"ETALON","WEATHER","HYDRO","AGRI","RADAR","AEROLOGY","AWS","OTHER"}:
                continue

            new = guess_kind(getattr(ic, "name_mn", ""), getattr(ic, "code", ""), old)
            ic.kind = new
            ic.save(update_fields=["kind"])
            updated += 1

    after = sorted(set(InstrumentCatalog.objects.all().values_list("kind", flat=True)))
    print("Updated rows:", updated)
    print("After kinds:", after)

if __name__ == "__main__":
    main()
