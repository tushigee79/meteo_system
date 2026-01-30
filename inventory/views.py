import json
import logging
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.http import JsonResponse, HttpRequest, FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils import timezone

from .device_passport_pdf import generate_device_passport_pdf

from .models import (
    Location,
    Device,
    MaintenanceService,
    ControlAdjustment,
)

ADMIN_NS = "admin"

logger = logging.getLogger(__name__)




def get_ub_aimag_id():
    """Return Ulaanbaatar Aimag ID without hardcoding. Cached for 1 day."""
    key = "inventory:ub_aimag_id:v1"
    v = cache.get(key)
    if v is not None:
        return v or None
    try:
        from .models import Aimag
        ub = Aimag.objects.get(name__icontains="улаанбаатар")
        cache.set(key, int(ub.id), 86400)
        return int(ub.id)
    except Exception:
        logger.warning("UB aimag not found by name__icontains='улаанбаатар'.")
        cache.set(key, 0, 3600)
        return None

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
    ub_id = get_ub_aimag_id()
    if ub_id is not None and scope["aimag_id"] == ub_id and scope["sum_id"] and hasattr(Location, "sum_ref_id"):
        qs = qs.filter(sum_ref_id=scope["sum_id"])
    return qs


def _scope_devices(request):
    loc_ids = _scope_locations(request).values_list("id", flat=True)
    return Device.objects.filter(location_id__in=loc_ids).select_related("location", "location__aimag_ref", "location__sum_ref", "catalog_item")



@staff_member_required
def qr_device_lookup(request: HttpRequest, token):
    """
    QR token-оор багажийг олж admin change page руу оруулна.
    ✅ Admin login шаардана (staff_member_required).
    ✅ AimagEngineer зэрэг role scope-г _scope_devices() ашиглан мөрдөнө.
    """
    # _scope_devices нь хэрэглэгчийн эрхээр (aimag гэх мэт) төхөөрөмжийг шүүнэ
    qs = _scope_devices(request)
    device = get_object_or_404(qs, qr_token=token)
    return redirect(f"/django-admin/inventory/device/{device.pk}/change/")


def _is_qr_active(device: Device) -> bool:
    if getattr(device, "qr_revoked_at", None):
        return False
    exp = getattr(device, "qr_expires_at", None)
    if exp and exp <= timezone.now():
        return False
    return True


def _device_timeline(device: Device):
    """Unified lifecycle timeline: movements + maintenance + adjustments."""
    items = []

    # Movements
    for mv in getattr(device, "movements", None).all().order_by("-moved_at")[:50]:
        items.append({
            "date": mv.moved_at,
            "kind": "MOVEMENT",
            "title": "Шилжилт",
            "details": f"{mv.source_location} → {mv.destination_location}",
        })

    # Maintenance / repair
    for ms in MaintenanceService.objects.filter(device=device).order_by("-date")[:50]:
        items.append({
            "date": ms.date,
            "kind": "MAINTENANCE",
            "title": "Засвар үйлчилгээ",
            "details": f"{ms.maintenance_type} — {ms.result_status}",
        })

    # Control / calibration adjustment
    for ca in ControlAdjustment.objects.filter(device=device).order_by("-date")[:50]:
        items.append({
            "date": ca.date,
            "kind": "ADJUSTMENT",
            "title": "Калибровка/шалгалт",
            "details": f"{ca.control_type} — {ca.result_status}",
        })

    # Sort newest first; handle None dates
    items.sort(key=lambda x: x["date"] or timezone.now(), reverse=True)
    return items


def qr_device_public_view(request: HttpRequest, token):
    """Public read-only QR page (no login)."""
    device = get_object_or_404(Device.objects.select_related("location"), qr_token=token)
    if not _is_qr_active(device):
        raise Http404("QR token expired or revoked.")

    timeline = _device_timeline(device)[:100]

    # Map link (google) if coordinates exist
    lat = _get_float(getattr(device, "location", None), "latitude", "lat")
    lon = _get_float(getattr(device, "location", None), "longitude", "lon")
    gmap = None
    if lat is not None and lon is not None:
        gmap = f"https://www.google.com/maps?q={lat},{lon}"

    return render(
        request,
        "inventory/qr_device_public.html",
        {
            "device": device,
            "timeline": timeline,
            "google_map_url": gmap,
        },
    )


def qr_device_public_passport_pdf(request: HttpRequest, token):
    """Public PDF download (readonly) via QR token."""
    device = get_object_or_404(Device.objects.select_related("location"), qr_token=token)
    if not _is_qr_active(device):
        raise Http404("QR token expired or revoked.")
    pdf_bytes = generate_device_passport_pdf(device, request=request)
    filename = f"device_passport_{device.serial_number or device.pk}.pdf"
    return FileResponse(pdf_bytes, as_attachment=True, filename=filename, content_type="application/pdf")


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


# ============================================================
# ✅ Compatibility endpoints (restores URLs used in urls.py)
#   Added without modifying existing logic.
# ============================================================
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

def _try_import(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name, None)
    except Exception:
        return None

@require_GET
def api_sum_duureg(request):
    """Dependent dropdown API. Delegates to inventory.views_api.api_sum_duureg if present."""
    fn = _try_import('inventory.views_api', 'api_sum_duureg')
    if callable(fn):
        return fn(request)
    # Safe fallback
    try:
        from .models import SumDuureg
    except Exception:
        return JsonResponse({'ok': True, 'results': []})
    aimag_id = (request.GET.get('aimag_id') or '').strip()
    q = (request.GET.get('q') or '').strip()
    qs = SumDuureg.objects.all()
    if aimag_id.isdigit():
        qs = qs.filter(aimag_id=int(aimag_id))
    else:
        return JsonResponse({'ok': True, 'results': []})
    if q:
        qs = qs.filter(name__icontains=q)
    return JsonResponse({'ok': True, 'results': [{'id': s.id, 'name': s.name} for s in qs.order_by('name')[:500]]})

@require_GET
def api_catalog_items(request):
    """InstrumentCatalog API. Delegates to inventory.views_api.api_catalog_items if present."""
    fn = _try_import('inventory.views_api', 'api_catalog_items')
    if callable(fn):
        return fn(request)
    try:
        from .models import InstrumentCatalog
    except Exception:
        return JsonResponse({'ok': True, 'results': []})
    kind = (request.GET.get('kind') or '').strip().upper()
    q = (request.GET.get('q') or '').strip()
    qs = InstrumentCatalog.objects.all()
    if hasattr(InstrumentCatalog, 'is_active'):
        qs = qs.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(name_mn__icontains=q) | qs.filter(code__icontains=q)
    out = [{'id': c.id, 'code': getattr(c,'code',''), 'name': getattr(c,'name_mn','') or str(c), 'kind': getattr(c,'kind','')} for c in qs.order_by('id')[:500]]
    return JsonResponse({'ok': True, 'results': out})

@staff_member_required
def device_import_csv(request):
    """CSV import view. Delegates to inventory.views_import.device_import_csv if present."""
    fn = _try_import('inventory.views_import', 'device_import_csv')
    if callable(fn):
        return fn(request)
    return HttpResponse('device_import_csv not implemented in this branch.', status=501)
