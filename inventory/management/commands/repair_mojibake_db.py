from django.core.management.base import BaseCommand
from django.db import transaction

def repair_mojibake(s: str) -> str:
    if not isinstance(s, str):
        return s
    if ("Ð" not in s) and ("Ñ" not in s) and ("Ã" not in s):
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s

class Command(BaseCommand):
    help = "Repair mojibake (Ð/Ñ/Ã) strings in DB fields by latin1->utf8 roundtrip."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry-run).")
        parser.add_argument("--limit", type=int, default=2000, help="Max rows per model to scan.")
        parser.add_argument("--model", type=str, default="", help="Optional: app_label.ModelName (e.g. inventory.Location)")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        limit = opts["limit"]
        model_filter = (opts["model"] or "").strip().lower()

        # импорт энд — танай project дээр model нэр өөр байж магадгүй
        from inventory.models import Location, Organization, InstrumentCatalog

        targets = [
            ("inventory.Location", Location, ["name"]),
            ("inventory.Organization", Organization, ["name"]),
            ("inventory.InstrumentCatalog", InstrumentCatalog, ["name_mn"]),
        ]

        if model_filter:
            targets = [t for t in targets if t[0].lower() == model_filter]
            if not targets:
                self.stdout.write(self.style.ERROR("Model not found in targets list."))
                return

        total_changes = 0

        for label, Model, fields in targets:
            qs = Model.objects.all().only("id", *fields)[:limit]
            changes = 0

            if apply:
                ctx = transaction.atomic()
            else:
                # no-op context
                class _Ctx:
                    def __enter__(self): return None
                    def __exit__(self, *a): return False
                ctx = _Ctx()

            with ctx:
                for obj in qs:
                    dirty = False
                    for f in fields:
                        old = getattr(obj, f, "")
                        new = repair_mojibake(old)
                        if new != old:
                            setattr(obj, f, new)
                            dirty = True
                    if dirty:
                        changes += 1
                        total_changes += 1
                        if apply:
                            obj.save(update_fields=fields)
                        self.stdout.write(f"{label} id={obj.id} repaired")

            self.stdout.write(self.style.SUCCESS(f"{label}: changes={changes} (limit={limit}, apply={apply})"))

        self.stdout.write(self.style.SUCCESS(f"DONE total_changes={total_changes} apply={apply}"))
