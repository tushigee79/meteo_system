# inventory/admin_compat.py
from __future__ import annotations
from typing import Any, Optional
from django.urls import reverse

def has_field(model: Any, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False

def get_user_aimag(user) -> Optional[object]:
    if not user or getattr(user, "is_anonymous", False):
        return None
    for attr in ("userprofile", "profile"):
        prof = getattr(user, attr, None)
        if prof is not None:
            aimag = getattr(prof, "aimag", None)
            if aimag is not None:
                return aimag
    return None

def admin_url(obj) -> str:
    if obj is None:
        return ""
    opts = obj._meta
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
