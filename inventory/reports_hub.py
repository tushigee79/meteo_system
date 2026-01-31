from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.contrib import admin as dj_admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

# ----------------------------
# Safe model imports (never crash Django startup)
# ----------------------------
Aimag = SumDuureg = Device = Location = InstrumentCatalog = MaintenanceService = ControlAdjustment = None  # type: ignore
DeviceMovement = SparePartOrder = SparePartItem = AuthAuditLog = None  # type: ignore
try:
    from .models import (  # type: ignore
        Aimag,
        SumDuureg,
        Device,
        Location,
        InstrumentCatalog,
        MaintenanceService,
        ControlAdjustment,
        DeviceMovement,
        SparePartOrder,
        SparePartItem,
        AuthAuditLog,
    )
except Exception as e:
    logger.warning("reports_hub: model import failed (partial ok): %s", e)
    try:
        from .models import (  # type: ignore
            Aimag,
            SumDuureg,
            Device,
            Location,
            InstrumentCatalog,
            MaintenanceService,
            ControlAdjustment,
        )
    except Exception as e2:
        logger.warning("reports_hub: core model import failed: %s", e2)

# ----------------------------
# Constants (UI)
# ----------------------------
REPORT_CHOICES: List[Tuple[str, str]] = [
    ("ALL", "Нэгдсэн тайлан (All indicators)"),
    ("DEVICES", "Багаж (Devices)"),
    ("MAINTENANCE", "Засвар үйлчилгээ (Maintenance)"),
    ("CONTROL", "Хяналт/тохируулга (Control)"),
    ("MOVEMENTS", "Шилжилт (Movements)"),
    ("LOCATIONS", "Байршил (Locations)"),
    ("SPAREPARTS", "Сэлбэгийн захиалга (Spare parts)"),
    ("AUTH", "Нэвтрэлт/аудит (Auth audit)"),
]

METRIC_CHOICES: List[Tuple[str, str]] = [
    ("STATUS", "Device status counts"),
    ("KIND", "Device kind counts"),
    ("LOCATION_TYPE", "Location type counts"),
    ("WORKFLOW", "Workflow per day (MS/CA)"),
]

CANONICAL_KINDS = {"WEATHER","HYDRO","AWS","ETALON","RADAR","AEROLOGY","AGRO","OTHER"}
KIND_ALIASES = {
    "METEO": "WEATHER",
    "MET": "WEATHER",
    "WEATHER_STATION": "WEATHER",
    "AERO": "AEROLOGY",
    "AGRICULTURE": "AGRO",
}

# ----------------------------
# Helpers
# ----------------------------
def _get_param(request: HttpRequest, key: str) -> str:
    return (request.GET.get(key) or "").strip()

def _get_param_any(request: HttpRequest, keys: List[str]) -> str:
    for k in keys:
        v = _get_param(request, k)
        if v:
            return v
    return ""

def _int_or_none(x: str) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None

def _parse_date(x: str) -> Optional[date]:
    x = (x or "").strip()
    if not x:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(x, fmt).date()
        except Exception:
            continue
    return None

def _admin_url(request: HttpRequest, viewname_suffix: str) -> str:
    site = getattr(request, "admin_site", None)
    ns = getattr(site, "name", "") if site else ""

    if ns:
        try:
            return reverse(f"{ns}:{viewname_suffix}")
        except NoReverseMatch:
            pass
    try:
        return reverse(f"admin:{viewname_suffix}")
    except NoReverseMatch:
        try:
            return reverse(f"inventory_admin:{viewname_suffix}")
        except NoReverseMatch:
            return "#"

def normalize_kind(v: str) -> str:
    vv = (v or "").strip().upper()
    if not vv:
        return ""
    if vv in CANONICAL_KINDS:
        return vv
    return KIND_ALIASES.get(vv, vv)

def _scope_is_restricted(request: HttpRequest) -> bool:
    u = getattr(request, "user", None)
    if not u:
        return False
    if getattr(u, "is_superuser", False):
        return False
    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    return bool(getattr(prof, "aimag_id", None))

def _scope_aimag_sum(request: HttpRequest) -> Tuple[Optional[int], Optional[int]]:
    u = getattr(request, "user", None)
    if not u or getattr(u, "is_superuser", False):
        return (None, None)
    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)
    sum_id = getattr(prof, "sumduureg_id", None) or getattr(prof, "sum_ref_id", None)
    try:
        aimag_id = int(aimag_id) if aimag_id else None
    except Exception:
        aimag_id = None
    try:
        sum_id = int(sum_id) if sum_id else None
    except Exception:
        sum_id = None
    return (aimag_id, sum_id)

def _apply_location_filters(qs, request: HttpRequest):
    aimag = _int_or_none(_get_param_any(request, ["aimag", "aimag_ref", "aimag_ref__id__exact"]))
    sum_id = _int_or_none(_get_param_any(request, ["sum", "sum_ref", "sum_ref__id__exact", "sumduureg"]))
    district = _get_param_any(request, ["district", "district_name", "district_name__exact"])
    loc_type = normalize_kind(_get_param_any(request, ["location_type", "location_type__exact", "kind"]))
    if aimag:
        qs = qs.filter(aimag_ref_id=aimag)
    if sum_id:
        qs = qs.filter(sum_ref_id=sum_id)
    if district:
        qs = qs.filter(district_name__iexact=district)
    if loc_type:
        qs = qs.filter(location_type__iexact=loc_type)
    return qs

def _apply_device_filters(qs, request: HttpRequest):
    aimag = _int_or_none(_get_param_any(request, ["aimag", "aimag_ref", "aimag_ref__id__exact"]))
    sum_id = _int_or_none(_get_param_any(request, ["sum", "sum_ref", "sum_ref__id__exact", "sumduureg"]))
    kind = normalize_kind(_get_param(request, "kind"))
    status = _get_param(request, "status")
    loc_type = normalize_kind(_get_param(request, "location_type"))
    if aimag:
        qs = qs.filter(location__aimag_ref_id=aimag)
    if sum_id:
        qs = qs.filter(location__sum_ref_id=sum_id)
    if kind:
        qs = qs.filter(kind__iexact=kind)
    if status:
        qs = qs.filter(status=status)
    if loc_type:
        qs = qs.filter(location__location_type__iexact=loc_type)
    return qs

def _date_window(request: HttpRequest) -> Tuple[Optional[date], Optional[date]]:
    d1 = _parse_date(_get_param(request, "date_from")) or _parse_date(_get_param(request, "from"))
    d2 = _parse_date(_get_param(request, "date_to")) or _parse_date(_get_param(request, "to"))
    return (d1, d2)

def _choices_from_model(model, attr_names: List[str]) -> List[Tuple[str,str]]:
    for a in attr_names:
        ch = getattr(model, a, None)
        if ch:
            return list(ch)
    return []

def _aimag_choices(request: HttpRequest) -> List[Tuple[int, str]]:
    if not Location:
        return []
    qs = Location.objects.exclude(aimag_ref__isnull=True).values("aimag_ref_id", "aimag_ref__name").distinct().order_by("aimag_ref__name")
    out = []
    for r in qs:
        if r.get("aimag_ref_id") and r.get("aimag_ref__name"):
            out.append((int(r["aimag_ref_id"]), str(r["aimag_ref__name"])))
    a_scope, _ = _scope_aimag_sum(request)
    if a_scope:
        out = [x for x in out if x[0] == a_scope]
    return out

def _sum_choices(request: HttpRequest, aimag_id: Optional[int]) -> List[Tuple[int, str]]:
    if not Location:
        return []
    qs = Location.objects.exclude(sum_ref__isnull=True)
    if aimag_id:
        qs = qs.filter(aimag_ref_id=aimag_id)
    qs = qs.values("sum_ref_id", "sum_ref__name").distinct().order_by("sum_ref__name")
    out = []
    for r in qs:
        if r.get("sum_ref_id") and r.get("sum_ref__name"):
            out.append((int(r["sum_ref_id"]), str(r["sum_ref__name"])))
    _, s_scope = _scope_aimag_sum(request)
    if s_scope:
        out = [x for x in out if x[0] == s_scope]
    return out

def _csv_response(filename: str) -> HttpResponse:
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")
    return resp

# ----------------------------
# Views
# ----------------------------
@staff_member_required(login_url="/django-admin/login/")
def reports_sums_by_aimag(request: HttpRequest):
    aimag_id = _int_or_none(_get_param_any(request, ["aimag_id", "aimag"]))
    sums = _sum_choices(request, aimag_id)
    return JsonResponse({"ok": True, "sums": [{"id": sid, "name": name} for sid, name in sums]})

@staff_member_required(login_url="/django-admin/login/")
def reports_chart_json(request: HttpRequest):
    if not Device or not Location:
        return JsonResponse({"ok": False, "error": "models_not_ready"})

    metric = (_get_param(request, "metric") or "STATUS").upper()
    d1, d2 = _date_window(request)

    a_scope, s_scope = _scope_aimag_sum(request)

    dqs = Device.objects.select_related("location")
    dqs = _apply_device_filters(dqs, request)
    if a_scope and not _get_param(request, "aimag"):
        dqs = dqs.filter(location__aimag_ref_id=a_scope)
    if s_scope and not _get_param(request, "sum"):
        dqs = dqs.filter(location__sum_ref_id=s_scope)

    payload: Dict[str, Any] = {"ok": True}

    if metric in ("STATUS", "KIND", "LOCATION_TYPE"):
        if metric == "STATUS":
            rows = list(dqs.values("status").annotate(v=Count("id")).order_by("-v"))
            payload["counts"] = {"status": [{"name": (r["status"] or "-"), "value": int(r["v"] or 0)} for r in rows]}
        elif metric == "KIND":
            rows = list(dqs.values("kind").annotate(v=Count("id")).order_by("-v"))
            payload["counts"] = {"status": [{"name": normalize_kind(r["kind"] or "-"), "value": int(r["v"] or 0)} for r in rows]}
        else:
            rows = list(dqs.values("location__location_type").annotate(v=Count("id")).order_by("-v"))
            payload["counts"] = {"status": [{"name": normalize_kind(r["location__location_type"] or "-"), "value": int(r["v"] or 0)} for r in rows]}

    # workflow window
    if d2 is None:
        d2 = date.today()
    if d1 is None:
        d1 = d2 - timedelta(days=29)
    if d1 > d2:
        d1, d2 = d2, d1

    axis: List[str] = []
    ms_vals: List[int] = []
    ca_vals: List[int] = []

    ms_by_day: Dict[date, int] = {}
    ca_by_day: Dict[date, int] = {}

    if MaintenanceService:
        ms_q = MaintenanceService.objects.select_related("device", "device__location")
        ms_q = ms_q.filter(date__gte=d1, date__lte=d2)
        # join by filtered devices
        ms_q = ms_q.filter(device_id__in=dqs.values_list("id", flat=True))
        for r in ms_q.values("date").annotate(v=Count("id")):
            dd = r.get("date")
            if isinstance(dd, date):
                ms_by_day[dd] = int(r.get("v") or 0)

    if ControlAdjustment:
        ca_q = ControlAdjustment.objects.select_related("device", "device__location")
        # Use date if exists, else created_at
        if hasattr(ControlAdjustment, "date"):
            ca_q = ca_q.filter(date__gte=d1, date__lte=d2)
            for r in ca_q.filter(device_id__in=dqs.values_list("id", flat=True)).values("date").annotate(v=Count("id")):
                dd = r.get("date")
                if isinstance(dd, date):
                    ca_by_day[dd] = int(r.get("v") or 0)
        else:
            # fallback: group by created_at day (approx)
            for r in ca_q.filter(device_id__in=dqs.values_list("id", flat=True)).values("created_at").annotate(v=Count("id")):
                dd = r.get("created_at")
                if isinstance(dd, datetime):
                    dd = dd.date()
                if isinstance(dd, date) and d1 <= dd <= d2:
                    ca_by_day[dd] = ca_by_day.get(dd, 0) + int(r.get("v") or 0)

    d = d1
    while d <= d2:
        axis.append(d.strftime("%Y-%m-%d"))
        ms_vals.append(int(ms_by_day.get(d, 0) or 0))
        ca_vals.append(int(ca_by_day.get(d, 0) or 0))
        d += timedelta(days=1)

    payload["workflow"] = {"axis": axis, "ms": ms_vals, "ca": ca_vals}
    payload["status_series"] = payload.get("counts", {}).get("status", [])
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False}, encoder=DjangoJSONEncoder)

@staff_member_required(login_url="/django-admin/login/")
def reports_export_devices_csv(request: HttpRequest):
    if not Device:
        return HttpResponse("models_not_ready", status=503)
    qs = _apply_device_filters(Device.objects.select_related("location", "location__aimag_ref", "location__sum_ref"), request)
    resp = _csv_response("devices.csv")
    w = csv.writer(resp)
    w.writerow(["id","serial_number","kind","status","location","aimag","sum","location_type"])
    for d in qs.order_by("id")[:200000]:
        loc = getattr(d, "location", None)
        w.writerow([
            d.id,
            getattr(d, "serial_number", "") or "",
            getattr(d, "kind", "") or "",
            getattr(d, "status", "") or "",
            getattr(loc, "name", "") if loc else "",
            getattr(getattr(loc, "aimag_ref", None), "name", "") if loc else "",
            getattr(getattr(loc, "sum_ref", None), "name", "") if loc else "",
            getattr(loc, "location_type", "") if loc else "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_locations_csv(request: HttpRequest):
    if not Location:
        return HttpResponse("models_not_ready", status=503)
    qs = _apply_location_filters(Location.objects.select_related("aimag_ref", "sum_ref", "owner_org"), request)
    qs = qs.annotate(device_count=Count("devices", distinct=True))
    resp = _csv_response("locations.csv")
    w = csv.writer(resp)
    w.writerow(["id","name","location_type","aimag","sum","district","org","wmo_index","lat","lon","device_count"])
    for loc in qs.order_by("id")[:200000]:
        w.writerow([
            loc.id,
            getattr(loc, "name", "") or "",
            getattr(loc, "location_type", "") or "",
            getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            getattr(loc, "district_name", "") or "",
            getattr(getattr(loc, "owner_org", None), "name", "") or "",
            getattr(loc, "wmo_index", "") or "",
            getattr(loc, "latitude", "") or "",
            getattr(loc, "longitude", "") or "",
            int(getattr(loc, "device_count", 0) or 0),
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_maintenance_csv(request: HttpRequest):
    if not MaintenanceService or not Device:
        return HttpResponse("models_not_ready", status=503)
    dqs = _apply_device_filters(Device.objects.all(), request).values_list("id", flat=True)
    qs = MaintenanceService.objects.select_related("device", "device__location").filter(device_id__in=list(dqs))
    d1, d2 = _date_window(request)
    if d1:
        qs = qs.filter(date__gte=d1)
    if d2:
        qs = qs.filter(date__lte=d2)
    resp = _csv_response("maintenance.csv")
    w = csv.writer(resp)
    w.writerow(["id","date","workflow_status","reason","device_id","serial_number","kind","status","location"])
    for r in qs.order_by("-date", "-id")[:200000]:
        d = getattr(r, "device", None)
        w.writerow([
            r.id,
            getattr(r, "date", "") or "",
            getattr(r, "workflow_status", "") or "",
            getattr(r, "reason", "") or "",
            getattr(d, "id", "") if d else "",
            getattr(d, "serial_number", "") if d else "",
            getattr(d, "kind", "") if d else "",
            getattr(d, "status", "") if d else "",
            getattr(getattr(d, "location", None), "name", "") if d else "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_control_csv(request: HttpRequest):
    if not ControlAdjustment or not Device:
        return HttpResponse("models_not_ready", status=503)
    dqs = _apply_device_filters(Device.objects.all(), request).values_list("id", flat=True)
    qs = ControlAdjustment.objects.select_related("device", "device__location").filter(device_id__in=list(dqs))
    d1, d2 = _date_window(request)
    if hasattr(ControlAdjustment, "date"):
        if d1:
            qs = qs.filter(date__gte=d1)
        if d2:
            qs = qs.filter(date__lte=d2)
    resp = _csv_response("control.csv")
    w = csv.writer(resp)
    w.writerow(["id","date","workflow_status","device_id","serial_number","kind","status","location"])
    for r in qs.order_by("-id")[:200000]:
        d = getattr(r, "device", None)
        w.writerow([
            r.id,
            getattr(r, "date", "") if hasattr(r, "date") else getattr(r, "created_at", ""),
            getattr(r, "workflow_status", "") or "",
            getattr(d, "id", "") if d else "",
            getattr(d, "serial_number", "") if d else "",
            getattr(d, "kind", "") if d else "",
            getattr(d, "status", "") if d else "",
            getattr(getattr(d, "location", None), "name", "") if d else "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_movements_csv(request: HttpRequest):
    if not DeviceMovement or not Device:
        return HttpResponse("models_not_ready", status=503)
    dqs = _apply_device_filters(Device.objects.all(), request).values_list("id", flat=True)
    qs = DeviceMovement.objects.select_related("device", "source_location", "dest_location").filter(device_id__in=list(dqs))
    resp = _csv_response("movements.csv")
    w = csv.writer(resp)
    w.writerow(["id","date","device_id","serial_number","from","to","reason"])
    for r in qs.order_by("-id")[:200000]:
        d = getattr(r, "device", None)
        w.writerow([
            r.id,
            getattr(r, "date", "") or getattr(r, "moved_at", "") or "",
            getattr(d, "id", "") if d else "",
            getattr(d, "serial_number", "") if d else "",
            getattr(getattr(r, "source_location", None), "name", "") or "",
            getattr(getattr(r, "dest_location", None), "name", "") or "",
            getattr(r, "reason", "") or "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_spareparts_csv(request: HttpRequest):
    if not SparePartOrder:
        return HttpResponse("models_not_ready", status=503)
    qs = SparePartOrder.objects.all()
    resp = _csv_response("spareparts.csv")
    w = csv.writer(resp)
    w.writerow(["id","created_at","aimag","status","notes"])
    for r in qs.order_by("-id")[:200000]:
        w.writerow([
            r.id,
            getattr(r, "created_at", "") or "",
            getattr(getattr(r, "aimag", None), "name", "") or getattr(r, "aimag_id", "") or "",
            getattr(r, "status", "") or "",
            getattr(r, "notes", "") or "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_export_auth_audit_csv(request: HttpRequest):
    if not AuthAuditLog:
        return HttpResponse("models_not_ready", status=503)
    qs = AuthAuditLog.objects.select_related("user").all()
    resp = _csv_response("auth_audit.csv")
    w = csv.writer(resp)
    w.writerow(["id","created_at","user","ip","action","success"])
    for r in qs.order_by("-id")[:200000]:
        u = getattr(r, "user", None)
        w.writerow([
            r.id,
            getattr(r, "created_at", "") or "",
            getattr(u, "username", "") if u else "",
            getattr(r, "ip_address", "") or getattr(r, "ip", "") or "",
            getattr(r, "action", "") or getattr(r, "event", "") or "",
            getattr(r, "success", "") if hasattr(r, "success") else "",
        ])
    return resp

@staff_member_required(login_url="/django-admin/login/")
def reports_hub_view(request: HttpRequest):
    if not Device or not Location or not InstrumentCatalog:
        return HttpResponse("models_not_ready", status=503)

    filt: Dict[str, str] = {
        "report": _get_param(request, "report") or "ALL",
        "metric": (_get_param(request, "metric") or "STATUS").upper(),
        "aimag": _get_param(request, "aimag"),
        "sum": _get_param(request, "sum"),
        "kind": normalize_kind(_get_param(request, "kind")),
        "location_type": normalize_kind(_get_param(request, "location_type")),
        "status": _get_param(request, "status"),
        "date_from": _get_param(request, "date_from") or _get_param(request, "from"),
        "date_to": _get_param(request, "date_to") or _get_param(request, "to"),
    }

    aimag_id = _int_or_none(filt["aimag"])
    sum_choices = _sum_choices(request, aimag_id)

    KIND_CHOICES = (
        _choices_from_model(Device, ["KIND_CHOICES"])
        or _choices_from_model(InstrumentCatalog, ["KIND_CHOICES"])
        or [(k, k) for k in sorted(CANONICAL_KINDS)]
    )
    STATUS_CHOICES = _choices_from_model(Device, ["STATUS_CHOICES"]) or []
    LOCATION_TYPE_CHOICES = (
        _choices_from_model(Location, ["LOCATION_TYPE_CHOICES", "TYPE_CHOICES", "LOCATION_TYPES"])
        or [(k, k) for k in sorted(CANONICAL_KINDS)]
    )

    is_scoped_user = _scope_is_restricted(request)

    dqs = _apply_device_filters(Device.objects.select_related("location"), request)
    lqs = _apply_location_filters(Location.objects.all(), request)

    total_devices = dqs.count()
    total_locations = lqs.count()

    st_map = {r["status"]: int(r["v"] or 0) for r in dqs.values("status").annotate(v=Count("id"))}
    cards = [
        {"k": "Devices (нийт)", "v": total_devices},
        {"k": "Locations (нийт)", "v": total_locations},
        {"k": "Active", "v": st_map.get("Active", 0)},
        {"k": "Broken", "v": st_map.get("Broken", 0)},
        {"k": "Repair", "v": st_map.get("Repair", 0)},
        {"k": "Spare", "v": st_map.get("Spare", 0)},
        {"k": "Retired", "v": st_map.get("Retired", 0)},
    ]

    pending_ms = 0
    pending_ca = 0
    if MaintenanceService and hasattr(MaintenanceService, "workflow_status"):
        pending_ms = MaintenanceService.objects.filter(workflow_status="SUBMITTED").count()
        cards.append({"k": "Pending MS", "v": pending_ms})
    if ControlAdjustment and hasattr(ControlAdjustment, "workflow_status"):
        pending_ca = ControlAdjustment.objects.filter(workflow_status="SUBMITTED").count()
        cards.append({"k": "Pending CA", "v": pending_ca})

    hub_url = _admin_url(request, "reports-hub")
    chart_url = _admin_url(request, "reports-chart-json")
    sums_url = _admin_url(request, "reports-sums-json")

    export_links = [
        {"label": "Devices CSV", "url": _admin_url(request, "reports-export-devices-csv")},
        {"label": "Locations CSV", "url": _admin_url(request, "reports-export-locations-csv")},
        {"label": "Maintenance CSV", "url": _admin_url(request, "reports-export-maintenance-csv")},
        {"label": "Control CSV", "url": _admin_url(request, "reports-export-control-csv")},
        {"label": "Movements CSV", "url": _admin_url(request, "reports-export-movements-csv")},
        {"label": "Spareparts CSV", "url": _admin_url(request, "reports-export-spareparts-csv")},
        {"label": "Auth audit CSV", "url": _admin_url(request, "reports-export-auth-audit-csv")},
    ]

    return render(
    request,
    "admin/inventory/reports/reports_hub.html",
    {
        "title": "Тайлан (ReportsHub)",
        "hub_url": hub_url,
        "chart_url": chart_url,
        "sums_url": sums_url,
        "export_csv_url": export_links[0]["url"],
        "EXPORT_LINKS": export_links,

        "REPORT_CHOICES": REPORT_CHOICES,
        "METRIC_CHOICES": METRIC_CHOICES,
        "AIMAG_CHOICES": _aimag_choices(request),
        "SUM_CHOICES": sum_choices,
        "KIND_CHOICES": KIND_CHOICES,
        "LOCATION_TYPE_CHOICES": LOCATION_TYPE_CHOICES,
        "STATUS_CHOICES": STATUS_CHOICES,

        "filter": filt,
        "is_scoped_user": is_scoped_user,
        "CARDS": cards,
    },
)

@staff_member_required(login_url="/django-admin/login/")
def reports_export_csv(request: HttpRequest):
    # legacy endpoint: devices
    return reports_export_devices_csv(request)
