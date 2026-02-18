# detect_mojibake.py
import re
from django.apps import apps

MOJIBAKE_RE = re.compile(r'[ÐÑ][\x80-\xBF]')

bad = []

for model in apps.get_models():
    for field in model._meta.fields:
        if field.get_internal_type() in ("CharField", "TextField"):
            qs = model.objects.exclude(**{f"{field.name}__isnull": True})
            for obj in qs[:5000]:  # safety limit
                val = getattr(obj, field.name, "")
                if isinstance(val, str) and MOJIBAKE_RE.search(val):
                    bad.append((model.__name__, field.name, obj.pk, val))

print("FOUND:", len(bad))
for b in bad[:20]:
    print(b)
