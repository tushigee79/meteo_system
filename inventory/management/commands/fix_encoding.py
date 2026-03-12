from django.core.management.base import BaseCommand
from django.apps import apps
import re

MOJIBAKE_RE = re.compile(r'[ÐÑ][\x80-\xBF]')

def fix_mojibake(s):
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s

class Command(BaseCommand):
    help = "Fix mojibake UTF-8 encoding issues"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply fixes")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        total = 0

        for model in apps.get_models():
            for field in model._meta.fields:
                if field.get_internal_type() in ("CharField", "TextField"):
                    qs = model.objects.exclude(**{f"{field.name}__isnull": True})
                    for obj in qs.iterator():
                        val = getattr(obj, field.name)
                        if isinstance(val, str) and MOJIBAKE_RE.search(val):
                            fixed = fix_mojibake(val)
                            if fixed != val:
                                total += 1
                                self.stdout.write(
                                    f"{model.__name__}.{field.name} pk={obj.pk}"
                                )
                                if apply:
                                    setattr(obj, field.name, fixed)
                                    obj.save(update_fields=[field.name])

        self.stdout.write(self.style.SUCCESS(f"FOUND/FIXED: {total}"))
