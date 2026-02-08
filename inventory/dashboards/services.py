# inventory/dashboards/services.py
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_date as _parse_date

from inventory.models import Device, Location, DeviceMovement, MaintenanceService, ControlAdjustment
from .selectors import scoped_devices_qs


# ----------------------------
# JSON helper expected by admin_dashboard.py
# ----------------------------
def dumps(obj: Any, **kwargs) -> str:
    """Stable JSON dumps helper used by templates/views."""
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", str)
    return json.dumps(obj, **kwargs)


# ----------------------------
# Date parsing
# ----------------------------
def parse_date(val: Optional[str]) -> Optional[date]:
    """
    Accepts:
      - YYYY-MM-DD
      - datetime ISO strings
    Returns date or None.
    """
    if not val:
        return None
    d = _parse_date(val)
    if d:
        return d
    # try datetime
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return dt.date()
    except Exception:
        return None


# ----------------------------
# Location type field resolver
# ----------------------------
def resolve_location_type_field() -> str:
    """
    Different code versions may use:
      - Location.location_type
      - Location.kind
      - etc.
    Return the best available field name.
    """
    # Prefer explicit 'location_type' if present
    for f in ("location_type", "kind", "type"):
        try:
            Location._meta.get_field(f)
            return f
        except Exception:
            continue
    # fallback (won't crash, but may not filter)
    return "location_type"


# ----------------------------
# Status timeline (device history)
# ----------------------------
def build_status_timeline(device: Device) -> List[Dict[str, Any]]:
    """
    Minimal timeline for a device.
    Later you can enrich with status changes, verification events, etc.
    """
    items: List[Dict[str, Any]] = []

    # movement events
    try:
        for m in DeviceMovement.objects.filter(device=device).order_by("date", "id"):
            items.append(
                {
                    "date": getattr(m, "date", None),
                    "type": "movement",
                    "title": "Байршил шилжилт",
                    "detail": f"{getattr(getattr(m,'source',None),'name', '')} → {getattr(getattr(m,'destination',None),'name','')}".strip(),
                }
            )
    except Exception:
        pass

    # maintenance events
    try:
        for s in MaintenanceService.objects.filter(device=device).order_by("date", "id"):
            items.append(
                {
                    "date": getattr(s, "date", None),
                    "type": "maintenance",
                    "title": "Засвар үйлчилгээ",
                    "detail": getattr(s, "reason", "") or "",
                }
            )
    except Exception:
        pass

    # control/adjustment events
    try:
        for c in ControlAdjustment.objects.filter(device=device).order_by("date", "id"):
            items.append(
                {
                    "date": getattr(c, "date", None),
                    "type": "control",
                    "title": "Хяналт/тохируулга",
                    "detail": getattr(c, "result", "") or "",
                }
            )
    except Exception:
        pass

    # sort (None-safe)
    def _key(x):
        v = x.get("date")
        if isinstance(v, (datetime, date)):
            return v
        return date.min

    items.sort(key=_key)
    # stringify dates for JSON safety
    for it in items:
        if isinstance(it.get("date"), (datetime, date)):
            it["date"] = it["date"].isoformat()
    return items


# -----------------------------
# Workflow timeline (aggregate)
# -----------------------------
def build_workflow_timeline(devices_qs):
    from inventory.models import MaintenanceService, ControlAdjustment

    out = []

    for Model, label in [
        (MaintenanceService, "maintenance"),
        (ControlAdjustment, "control"),
    ]:
        qs = Model.objects.filter(device__in=devices_qs)

        for s in qs:
            d = getattr(s, "submitted_at", None) or getattr(s, "created_at", None)
            if not d:
                continue
            out.append({
                "date": d.date().isoformat(),
                "type": label,
                "status": getattr(s, "workflow_status", ""),
            })

    return out


# -----------------------------
# Workflow pending counters
# -----------------------------
def build_workflow_pending_counts():
    pending_statuses = {"PENDING", "SUBMITTED", "NEED_APPROVAL", "IN_REVIEW"}

    def _count(qs):
        try:
            return qs.filter(workflow_status__in=pending_statuses).count()
        except Exception:
            return 0

    from inventory.models import MaintenanceService, ControlAdjustment

    out = {
        "maintenance": _count(MaintenanceService.objects.all()),
        "control": _count(ControlAdjustment.objects.all()),
    }

    # DeviceMovement дээр workflow_status байхгүй байж магадгүй тул safe
    try:
        from inventory.models import DeviceMovement
        out["movement"] = _count(DeviceMovement.objects.all())
    except Exception:
        out["movement"] = 0

    return out

# ----------------------------
# Map points builder
# ----------------------------
def build_map_points(
    request_user,
    aimag_id: Optional[str] = None,
    sum_id: Optional[str] = None,
    location_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Returns points for Leaflet (minimal).
    Filters are best-effort; won’t crash if fields differ.
    """
    qs: QuerySet = scoped_devices_qs(request_user)

    # optional filters
    if status:
        try:
            qs = qs.filter(status=status)
        except Exception:
            pass

    if location_type:
        lt_field = resolve_location_type_field()
        try:
            qs = qs.filter(**{f"location__{lt_field}": location_type})
        except Exception:
            pass

    if aimag_id:
        # common: location__aimag_ref or location__aimag
        try:
           qs = qs.filter(location__aimag_ref__id=aimag_id)
        except Exception:
            try:
                qs = qs.filter(location__aimag_id=aimag_id)
            except Exception:
                pass

    if sum_id:
        try:
            qs = qs.filter(location__sum_ref__id=sum_id)
        except Exception:
            try:
                qs = qs.filter(location__sum_ref__id=sum_id)
            except Exception:
                pass

    points: List[Dict[str, Any]] = []
    for d in qs.select_related("location"):
        loc = getattr(d, "location", None)
        if not loc:
            continue
        lat = getattr(loc, "latitude", None) or getattr(loc, "lat", None)
        lon = getattr(loc, "longitude", None) or getattr(loc, "lon", None)
        if lat is None or lon is None:
            continue

        points.append(
            {
                "id": d.id,
                "name": str(getattr(d, "name", None) or getattr(d, "serial_number", None) or f"Device #{d.id}"),
                "lat": float(lat),
                "lon": float(lon),
                "status": str(getattr(d, "status", "") or ""),
                "location": str(getattr(loc, "name", "") or ""),
            }
        )

    return points

# ----------------------------
# Verification buckets (expired / due30 / due90 / ok / unknown)
# ----------------------------
def build_verification_buckets(user) -> dict:
    """
    Returns counts for verification status:
      - expired: next_verification_date < today
      - due30: within 30 days
      - due90: within 90 days
      - ok: > 90 days
      - unknown: missing date
    Uses whatever 'next verification' field exists on Device.
    """
    qs = scoped_devices_qs(user)

    # detect next-verification field name
    candidates = ("next_verification_date", "next_verif_date", "next_verification", "verification_due_date")
    field = None
    for f in candidates:
        try:
            Device._meta.get_field(f)
            field = f
            break
        except Exception:
            continue

    buckets = {"expired": 0, "due30": 0, "due90": 0, "ok": 0, "unknown": 0}
    today = timezone.localdate()

    if not field:
        # cannot compute; everything unknown
        buckets["unknown"] = int(qs.count())
        return buckets

    for d in qs.only("id", field):
        dt = getattr(d, field, None)
        if not dt:
            buckets["unknown"] += 1
            continue

        # dt may be datetime/date
        try:
            due = dt.date() if hasattr(dt, "date") else dt
        except Exception:
            buckets["unknown"] += 1
            continue

        days = (due - today).days
        if days < 0:
            buckets["expired"] += 1
        elif days <= 30:
            buckets["due30"] += 1
        elif days <= 90:
            buckets["due90"] += 1
        else:
            buckets["ok"] += 1

    return buckets
