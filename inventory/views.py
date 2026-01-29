import json
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import (
    Location,
    Device,
    MaintenanceService,
    ControlAdjustment,
)

ADMIN_NS = "admin"


# ---------------------------
# Scope helpers
# ---------------------------
def _get_scope(request):
    u = request.user
    if u.is_superuser:
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None) or getattr(getattr(prof, "aimag", None), "id", None)
    sum_id = (
        getattr(prof, "sumduureg_id", None)
        or getattr(prof, "sum_ref_id", None)
        or getattr(prof, "district_id", None)
        or getattr(getattr(prof, "sumduureg", None), "id", None)
        or getattr(getattr(prof, "sum_ref", None), "id", None)
    )
    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}


def _scope_locations(request):
    scope = _get_scope(request)
    qs = Location.objects.all()
    if scope["all"]:
        return qs
    if not scope["aimag_id"]:
        return qs.none()
    qs = qs.filter(aimag_ref_id=scope["aimag_id"])
    # UB (aimag_id==1) үед district/sum scope байвал
    if scope["aimag_id"] == 1 and scope["sum_id"] and hasattr(Location, "sum_ref_id"):
        qs = qs.filter(sum_ref_id=scope["sum_id"])
    return qs


def _scope_devices(request):
    loc_ids = _scope_locations(request).values_list("id", flat=True)
    return Device.objects.filter(location_id__in=list(loc_ids))


def _get_float(obj, *names):
    for n in names:
        if not n:
            continue
        try:
            v = getattr(obj, n)
        except Exception:
            continue
        if v in (None, ""):
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None


# ---------------------------
# ✅ Admin data-entry hub (ImportError guard)
# ---------------------------
@staff_member_required
def admin_data_entry(request):
    try:
        return render(
            request,
            "admin/inventory/admin_data_entry.html",
            {"title": "Өгөгдөл бүртгэх (Админ)"},
        )
    except Exception:
        return redirect("/django-admin/")


# ---------------------------
# Map: single point
# ---------------------------
@staff_member_required
@xframe_options_sameorigin
def station_map_view(request):
    loc_id = request.GET.get("id")
    if not loc_id:
        return render(request, "inventory/location_map_one.html", {"locations_json": "[]", "single": True})

    qs = _scope_locations(request)
    try:
        qs = qs.select_related("aimag_ref", "sum_ref", "owner_org").annotate(device_count=Count("devices"))
    except Exception:
        qs = qs.select_related("aimag_ref").annotate(device_count=Count("devices"))

    loc = get_object_or_404(qs, id=loc_id)
    lat = _get_float(loc, "latitude", "lat")
    lon = _get_float(loc, "longitude", "lon", "lng")

    points = []
    if lat is not None and lon is not None:
        points = [{
            "id": loc.id,
            "name": getattr(loc, "name", "") or str(loc),
            "lat": lat,
            "lon": lon,
            "kind": getattr(loc, "location_type", None) or getattr(loc, "kind", None) or "OTHER",
            "aimag": getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            "sum": getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            "org": getattr(getattr(loc, "owner_org", None), "name", "") or "",
            "device_count": int(getattr(loc, "device_count", 0) or 0),
        }]

    return render(
        request,
        "inventory/location_map_one.html",
        {"locations_json": json.dumps(points, cls=DjangoJSONEncoder), "single": True},
    )


# ---------------------------
# Map: ALL points (robust) + ?ajax=1 JSON debug
# ---------------------------
@staff_member_required
def location_map(request, location_id=None):
    ajax = (request.GET.get("ajax") or "").strip() == "1"
    loc_id = location_id or request.GET.get("id")

    qs = _scope_locations(request)
    for rel in ("aimag_ref", "sum_ref", "owner_org"):
        try:
            qs = qs.select_related(rel)
        except Exception:
            pass
    try:
        qs = qs.annotate(device_count=Count("devices"))
    except Exception:
        pass

    if loc_id:
        loc = get_object_or_404(qs, id=loc_id)
        lat = _get_float(loc, "latitude", "lat")
        lon = _get_float(loc, "longitude", "lon", "lng")
        points = []
        if lat is not None and lon is not None:
            points = [{
                "id": loc.id,
                "name": getattr(loc, "name", "") or str(loc),
                "lat": lat,
                "lon": lon,
                "kind": getattr(loc, "location_type", None) or getattr(loc, "kind", None) or "OTHER",
                "aimag": getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
                "sum": getattr(getattr(loc, "sum_ref", None), "name", "") or "",
                "org": getattr(getattr(loc, "owner_org", None), "name", "") or "",
                "device_count": int(getattr(loc, "device_count", 0) or 0),
            }]
        if ajax:
            return JsonResponse({"ok": True, "mode": "single", "count": len(points), "points": points})
        return render(
            request,
            "inventory/location_map_one.html",
            {"locations_json": json.dumps(points, cls=DjangoJSONEncoder), "single": True},
        )

    points = []
    for loc in qs.order_by("id")[:50000]:
        lat = _get_float(loc, "latitude", "lat")
        lon = _get_float(loc, "longitude", "lon", "lng")
        if lat is None or lon is None:
            continue
        points.append({
            "id": loc.id,
            "name": getattr(loc, "name", "") or str(loc),
            "lat": lat,
            "lon": lon,
            "kind": getattr(loc, "location_type", None) or getattr(loc, "kind", None) or "OTHER",
            "aimag": getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            "sum": getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            "org": getattr(getattr(loc, "owner_org", None), "name", "") or "",
            "device_count": int(getattr(loc, "device_count", 0) or 0),
        })

    if ajax:
        return JsonResponse({"ok": True, "mode": "all", "count": len(points), "sample": points[:3]})

    return render(
        request,
        "inventory/location_map.html",
        {"locations_json": json.dumps(points, cls=DjangoJSONEncoder), "single": False},
    )


# ---------------------------
# ✅ Dashboard cards (safe)
# ---------------------------
@staff_member_required
def dashboard_cards(request):
    ajax = (request.GET.get("ajax") or "").strip() == "1"

    loc_qs = _scope_locations(request)
    dev_qs = _scope_devices(request)

    total_locations = loc_qs.count()
    total_devices = dev_qs.count()

    pending_status = "SUBMITTED"
    pending_maint = MaintenanceService.objects.filter(
        workflow_status=pending_status,
        device__location_id__in=loc_qs.values_list("id", flat=True),
    ).count()
    pending_control = ControlAdjustment.objects.filter(
        workflow_status=pending_status,
        device__location_id__in=loc_qs.values_list("id", flat=True),
    ).count()

    ctx = {
        "title": "Dashboard",
        "total_locations": total_locations,
        "total_devices": total_devices,
        "pending_total": pending_maint + pending_control,
        "pending_maint": pending_maint,
        "pending_control": pending_control,
        "scope": _get_scope(request),
    }

    if ajax:
        return JsonResponse({"ok": True, **ctx})

    return render(request, "admin/inventory/reports/dashboard_cards.html", ctx)
