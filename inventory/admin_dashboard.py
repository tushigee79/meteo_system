# inventory/admin_dashboard.py
from __future__ import annotations

import json
from datetime import timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Device, Location, MaintenanceService, ControlAdjustment


# -----------------------------
# Helpers (robust / safe)
# -----------------------------
def _field_exists(model, name: str) -> bool:
    try:
        return name in {f.name for f in model._meta.fields}
    except Exception:
        return False

def _date_range_from_request(request: HttpRequest) -> Tuple[date, date]:
    """
    Default: last 30 days.
    """
    today = timezone.localdate()
    d_to = _parse_date(request.GET.get("date_to")) or today
    d_from = _parse_date(request.GET.get("date_from")) or (d_to - timedelta(days=30))
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    return d_from, d_to

def _pick_field(model, preferred: List[str]) -> Optional[str]:
    for n in preferred:
        if _field_exists(model, n):
            return n
    return None


def _get_user_aimag_id(user) -> Optional[int]:
    """
    AimagEngineer scope enforcement (best-effort).
    - If you have UserProfile.aimag FK, it will be used.
    - Otherwise returns None (no restriction).
    """
    try:
        # Typical pattern: user.userprofile.aimag_id
        up = getattr(user, "userprofile", None)
        if up and getattr(up, "aimag_id", None):
            return int(up.aimag_id)
    except Exception:
        pass
    return None


def _is_aimag_engineer(user) -> bool:
    try:
        return user.groups.filter(name="AimagEngineer").exists()
    except Exception:
        return False


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        # expecting YYYY-MM-DD
        return timezone.datetime.fromisoformat(s).date()
    except Exception:
        return None


def _date_range_from_request(request: HttpRequest) -> Tuple[date, date]:
    """
    Default: last 30 days.
    """
    today = timezone.localdate()
    d_to = _parse_date(request.GET.get("date_to")) or today
    d_from = _parse_date(request.GET.get("date_from")) or (d_to - timedelta(days=30))
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    return d_from, d_to


def _apply_location_filters_to_qs(request: HttpRequest, qs):
    """
    Optional filters:
    - aimag_id
    - location_type
    """
    aimag_id = request.GET.get("aimag_id")
    if aimag_id:
        try:
            qs = qs.filter(aimag_ref_id=int(aimag_id))
        except Exception:
            pass

    location_type = request.GET.get("location_type")
    if location_type and _field_exists(Location, "location_type"):
        qs = qs.filter(location_type=location_type)

    return qs


def _apply_device_filters_to_qs(request: HttpRequest, qs):
    """
    Optional filters:
    - kind
    """
    kind = request.GET.get("kind")
    if kind and _field_exists(Device, "kind"):
        qs = qs.filter(kind=kind)
    return qs


# -----------------------------
# Core data builders (single JSON schema)
# -----------------------------
def build_graph_payload(request: HttpRequest) -> Dict[str, Any]:
    user = request.user
    date_from, date_to = _date_range_from_request(request)

    # Role scope (AimagEngineer)
    scoped_aimag_id = _get_user_aimag_id(user) if _is_aimag_engineer(user) else None

    # -----------------
    # Locations (for map + aimag breakdown)
    # -----------------
    loc_qs = Location.objects.all()
    loc_qs = _apply_location_filters_to_qs(request, loc_qs)

    if scoped_aimag_id:
        # enforce aimag scope
        if _field_exists(Location, "aimag_ref"):
            loc_qs = loc_qs.filter(aimag_ref_id=scoped_aimag_id)

    # lat/lon fields (best-effort)
    lat_f = _pick_field(Location, ["lat", "latitude", "y"])
    lon_f = _pick_field(Location, ["lon", "lng", "longitude", "x"])
    name_f = _pick_field(Location, ["name", "title"])
    type_f = _pick_field(Location, ["location_type", "kind", "type"])

    # -----------------
    # Devices by kind (bar)
    # -----------------
    dev_qs = Device.objects.all()
    if _field_exists(Device, "location_id") and scoped_aimag_id and _field_exists(Location, "aimag_ref"):
        dev_qs = dev_qs.filter(location__aimag_ref_id=scoped_aimag_id)

    dev_qs = _apply_device_filters_to_qs(request, dev_qs)

    # time window (if Device has created_at / registered_at / commissioned_date etc.)
    dev_date_f = _pick_field(Device, ["created_at", "registered_at", "commissioned_date", "date_created"])
    if dev_date_f:
        # inclusive range
        dev_qs = dev_qs.filter(**{f"{dev_date_f}__date__gte": date_from, f"{dev_date_f}__date__lte": date_to})

    kind_f = _pick_field(Device, ["kind", "device_type", "category"])
    if kind_f:
        by_kind = list(
            dev_qs.values(kind_f).annotate(cnt=Count("id")).order_by("-cnt")[:30]
        )
        echarts_kind = [{"name": (r.get(kind_f) or "—"), "value": r["cnt"]} for r in by_kind]
    else:
        echarts_kind = []

    # -----------------
    # Workflow stacked (Maintenance + Control)
    # -----------------
    # status fields (best-effort)
    m_status_f = _pick_field(MaintenanceService, ["status", "workflow_status", "state"])
    c_status_f = _pick_field(ControlAdjustment, ["status", "workflow_status", "state"])
    m_dt_f = _pick_field(MaintenanceService, ["created_at", "submitted_at", "date_created", "requested_at"])
    c_dt_f = _pick_field(ControlAdjustment, ["created_at", "submitted_at", "date_created", "requested_at"])

    def _filter_by_dates(qs, dt_field):
        if not dt_field:
            return qs
        return qs.filter(**{f"{dt_field}__date__gte": date_from, f"{dt_field}__date__lte": date_to})

    m_qs = MaintenanceService.objects.all()
    c_qs = ControlAdjustment.objects.all()

    # scope to aimag via related device/location if available
    if scoped_aimag_id:
        if _field_exists(MaintenanceService, "device_id") and _field_exists(Device, "location_id") and _field_exists(Location, "aimag_ref"):
            m_qs = m_qs.filter(device__location__aimag_ref_id=scoped_aimag_id)
        if _field_exists(ControlAdjustment, "device_id") and _field_exists(Device, "location_id") and _field_exists(Location, "aimag_ref"):
            c_qs = c_qs.filter(device__location__aimag_ref_id=scoped_aimag_id)

    m_qs = _filter_by_dates(m_qs, m_dt_f)
    c_qs = _filter_by_dates(c_qs, c_dt_f)

    # normalize status buckets
    def _norm_status(s: Optional[str]) -> str:
        if not s:
            return "UNKNOWN"
        s2 = str(s).upper()
        if "PEND" in s2 or "WAIT" in s2 or "NEED" in s2:
            return "PENDING"
        if "APPROV" in s2 or "DONE" in s2 or "OK" in s2 or "COMPLET" in s2:
            return "APPROVED"
        if "REJ" in s2 or "DECLIN" in s2:
            return "REJECTED"
        return s2[:30]

    wf_counts = {"PENDING": 0, "APPROVED": 0, "REJECTED": 0, "UNKNOWN": 0}

    if m_status_f:
        for r in m_qs.values(m_status_f).annotate(cnt=Count("id")):
            wf_counts[_norm_status(r.get(m_status_f))] = wf_counts.get(_norm_status(r.get(m_status_f)), 0) + r["cnt"]
    if c_status_f:
        for r in c_qs.values(c_status_f).annotate(cnt=Count("id")):
            wf_counts[_norm_status(r.get(c_status_f))] = wf_counts.get(_norm_status(r.get(c_status_f)), 0) + r["cnt"]

    # stacked format for ECharts
    echarts_workflow_stacked = [
        {"name": "PENDING", "value": wf_counts.get("PENDING", 0)},
        {"name": "APPROVED", "value": wf_counts.get("APPROVED", 0)},
        {"name": "REJECTED", "value": wf_counts.get("REJECTED", 0)},
        {"name": "UNKNOWN", "value": wf_counts.get("UNKNOWN", 0)},
    ]

    # -----------------
    # SLA buckets (based on age of PENDING items)
    # < 30 days = OK, 30-90 = WARNING, > 90 = OVERDUE
    # -----------------
    now = timezone.now()

    def _pending_qs(qs, status_field):
        if not status_field:
            return qs.none()
        # try common pending tokens
        return qs.filter(Q(**{status_field + "__icontains": "pend"}) | Q(**{status_field + "__icontains": "need"}))

    def _sla_bucket(qs, dt_field):
        if not dt_field:
            return {"OK": 0, "WARNING": 0, "OVERDUE": 0}
        ok = 0
        warn = 0
        over = 0
        # only check last N rows to stay fast; adjust if needed
        for row in qs.values(dt_field)[:5000]:
            dt = row.get(dt_field)
            if not dt:
                continue
            age = (now - dt).days
            if age < 30:
                ok += 1
            elif age < 90:
                warn += 1
            else:
                over += 1
        return {"OK": ok, "WARNING": warn, "OVERDUE": over}

    m_pending = _pending_qs(m_qs, m_status_f)
    c_pending = _pending_qs(c_qs, c_status_f)
    m_sla = _sla_bucket(m_pending, m_dt_f)
    c_sla = _sla_bucket(c_pending, c_dt_f)

    echarts_sla = [
        {"name": "OK", "value": int(m_sla["OK"] + c_sla["OK"])},
        {"name": "WARNING", "value": int(m_sla["WARNING"] + c_sla["WARNING"])},
        {"name": "OVERDUE", "value": int(m_sla["OVERDUE"] + c_sla["OVERDUE"])},
    ]

    # -----------------
    # Aimag breakdown (bar)
    # -----------------
    echarts_aimag: List[Dict[str, Any]] = []
    if _field_exists(Location, "aimag_ref"):
        # count locations per aimag within filters/scope
        aimag_counts = list(loc_qs.values("aimag_ref_id").annotate(cnt=Count("id")).order_by("-cnt"))
        for r in aimag_counts[:50]:
            echarts_aimag.append({"name": str(r["aimag_ref_id"]), "value": r["cnt"]})

    # -----------------
    # Map points
    # -----------------
    points: List[Dict[str, Any]] = []
    if lat_f and lon_f:
        for loc in loc_qs.only("id", *(f for f in [lat_f, lon_f, name_f, type_f] if f) )[:3000]:
            lat = getattr(loc, lat_f, None)
            lon = getattr(loc, lon_f, None)
            if lat is None or lon is None:
                continue
            points.append(
                {
                    "id": loc.id,
                    "name": getattr(loc, name_f, None) if name_f else f"Location #{loc.id}",
                    "location_type": getattr(loc, type_f, None) if type_f else None,
                    "lat": float(lat),
                    "lon": float(lon),
                }
            )

    return {
        "meta": {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "scoped_aimag_id": scoped_aimag_id,
        },
        # ✅ single, stable schema:
        "echarts_workflow_stacked": echarts_workflow_stacked,
        "echarts_sla": echarts_sla,
        "echarts_aimag": echarts_aimag,
        "echarts_kind": echarts_kind,
        "locations": points,
    }


# -----------------------------
# Views
# -----------------------------
@staff_member_required
def dashboard_graph_view(request: HttpRequest):
    """
    HTML page by default.
    If ?ajax=1 -> JSON payload (single schema).
    """
    if request.GET.get("ajax") == "1":
        payload = build_graph_payload(request)
        return JsonResponse(payload, encoder=DjangoJSONEncoder)

    date_from, date_to = _date_range_from_request(request)
    ctx = {
        "date_from": str(date_from),
        "date_to": str(date_to),
    }
    return render(request, "admin/dashboard_graph.html", ctx)


@staff_member_required
def workflow_pending_counts(request):
    """
    GET /django-admin/inventory/workflow/pending-counts/
    """
    from .models import MaintenanceService, ControlAdjustment, DeviceMovement

    # Танайх workflow_status ашиглаж байна
    pending_statuses = ["PENDING", "NEED_APPROVAL", "SUBMITTED", "REVIEW"]

    ms = MaintenanceService.objects.filter(workflow_status__in=pending_statuses).count()

    # ControlAdjustment дээр workflow_status байхгүй байж магадгүй тул try хамгаалалттай
    try:
        ca = ControlAdjustment.objects.filter(workflow_status__in=pending_statuses).count()
    except Exception:
        ca = 0

    # DeviceMovement дээр workflow_status байхгүй байж магадгүй
    try:
        mv = DeviceMovement.objects.filter(workflow_status__in=pending_statuses).count()
    except Exception:
        mv = 0

    return JsonResponse({
        "maintenance_pending": ms,
        "control_pending": ca,
        "movement_pending": mv,
        "total_pending": ms + ca + mv,
    })
    return render(request, "admin/dashboard_graph.html", ctx)


