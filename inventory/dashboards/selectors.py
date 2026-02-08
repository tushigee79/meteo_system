# inventory/dashboards/selectors.py
from __future__ import annotations

from typing import Optional
from django.contrib.auth.models import User
from django.db.models import QuerySet

from inventory.models import Device

AIMAG_ENGINEER_GROUP = "AimagEngineer"


def _user_aimag_id(user: User) -> Optional[int]:
    profile = getattr(user, "userprofile", None)
    if not profile:
        return None
    aimag = getattr(profile, "aimag", None)
    if aimag:
        return aimag.id
    # fallback (if you used aimag_ref field somewhere)
    aimag_ref = getattr(profile, "aimag_ref", None)
    return getattr(aimag_ref, "id", None)


def scoped_devices_qs(user: User, base_qs: Optional[QuerySet] = None) -> QuerySet:
    """
    Returns Device queryset filtered for AimagEngineer users (only their aimag).
    Superusers/staff outside group get full queryset.
    Safe when UserProfile is missing.
    """
    qs = base_qs if base_qs is not None else Device.objects.all()

    if not getattr(user, "is_authenticated", False):
        return qs.none()

    # superuser sees all
    if getattr(user, "is_superuser", False):
        return qs

    in_group = user.groups.filter(name=AIMAG_ENGINEER_GROUP).exists()
    if not in_group:
        return qs

    aimag_id = _user_aimag_id(user)
    if not aimag_id:
        return qs.none()

    # Try common relations: device.location.aimag or device.location.aimag_ref
    # If your Location uses aimag_ref, this still works.
    qs = qs.filter(location__aimag_id=aimag_id)


