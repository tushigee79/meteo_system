# inventory/reports_hub.py (production-ready)
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.contrib import admin as dj_admin
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count, QuerySet
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Aimag,
    ControlAdjustment,
    Device,
    DeviceMovement,
    Location,
    MaintenanceService,
    SparePartOrder,
    SumDuureg,
)

AIMAG_ENGINEER_GROUP = "AimagEngineer"


# ============================================================
# Scoping helpers (AimagEngineer -> own aimag only)
# ============================================================

def _is_aimag_engineer(request: HttpRequest) -> bool:
    u = request.user
    return bool(u.is_authenticated and u.groups.filter(name=AIMAG_ENGINEER_GROUP).exists())


def _get_user_aimag_id(request: HttpRequest) -> Optional[int]:
    # production-safe: some projects use request.user.profile (related_name)
    profile = getattr(request.user, "userprofile", None) or getattr(request.user, "profile", None)
    if not profile:
        return None
    return getattr(profile, "aimag_id", None) or None


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def _movement_fields() -> Tuple[str, str]:
    """Return (from_field, to_field) for DeviceMovement across variants."""
    if _has_field(DeviceMovement, "from_location") and _has_field(DeviceMovement, "to_location"):
        return "from_location", "to_location"
    # older/alt naming
    if _has_field(DeviceMovement, "source_location") and _has_field(DeviceMovement, "destination_location"):
        return "source_location", "destination_location"
    # last resort (avoid crashing)
    return "from_location", "to_location"


_MV_FROM_FIELD, _MV_TO_FIELD = _movement_fields()


def _scope_qs(request: HttpRequest, qs: QuerySet, aimag_path: str) -> QuerySet:
    """
    aimag_path examples:
      - "aimag_ref_id"
      - "location__aimag_ref_id"
      - "device__location__aimag_ref_id"
      - "destination_location__aimag_ref_id"
    """
    if request.user.is_superuser:
        return qs
    if _is_aimag_engineer(request):
        aid = _get_user_aimag_id(request)
        if not aid:
            return qs.none()
        return qs.filter(**{aimag_path: aid})
    return qs


# ============================================================
# Small utils
# ============================================================

def _get_param(request: HttpRequest, key: str) -> str:
    return (request.GET.get(key) or "").strip()


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _choice_label(choices: Iterable[Tuple[str, str]], key: str) -> str:
    for k, v in choices:
        if str(k) == str(key):
            return str(v)
    return str(key)


def _series_from_kv(rows: Iterable[Tuple[str, int]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name, value in rows:
        if name is None or str(name).strip() == "":
            name = "—"
        out.append({"name": str(name), "value": int(value or 0)})
    # deterministic order: desc by value, then name
    out.sort(key=lambda r: (-int(r["value"]), str(r["name"])))
    return out


# ============================================================
# Filters
# ============================================================

def _apply_device_filters(request: HttpRequest, qs: QuerySet[Device]) -> QuerySet[Device]:
    aimag = _get_param(request, "aimag")
    sum_id = _get_param(request, "sum")
    kind = _get_param(request, "kind")
    status = _get_param(request, "status")
    loc_type = _get_param(request, "location_type")

    if aimag:
        qs = qs.filter(location__aimag_ref_id=aimag)
    if sum_id:
        qs = qs.filter(location__sum_ref_id=sum_id)
    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    if loc_type:
        qs = qs.filter(location__location_type=loc_type)
    return qs


def _apply_location_filters(request: HttpRequest, qs: QuerySet[Location]) -> QuerySet[Location]:
    aimag = _get_param(request, "aimag")
    sum_id = _get_param(request, "sum")
    loc_type = _get_param(request, "location_type")

    if aimag:
        qs = qs.filter(aimag_ref_id=aimag)
    if sum_id:
        qs = qs.filter(sum_ref_id=sum_id)
    if loc_type:
        qs = qs.filter(location_type=loc_type)
    return qs


def _date_window(request: HttpRequest) -> Tuple[date, date]:
    today = timezone.localdate()
    date_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = _parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


# ============================================================
# ReportsHub page
# ============================================================

REPORT_CHOICES = [
    ("devices", "Багаж (Devices)"),
    ("locations", "Байршил (Locations)"),
    ("workflow", "Workflow (Засвар/Хяналт)"),
    ("movements", "Шилжилт (Movements)"),
]

METRIC_CHOICES = [
    ("count_by_status", "Count by status"),
    ("count_by_kind", "Count by kind"),
    ("count_by_location_type", "Count by location type"),
    ("count_by_aimag", "Count by aimag"),
    ("count_by_sum", "Count by sum/district"),
    ("count_by_district", "Count by UB district_name"),
]

def _current_filter(request: HttpRequest) -> Dict[str, str]:
    return {
        "report": _get_param(request, "report") or "devices",
        "metric": _get_param(request, "metric") or "count_by_kind",
        "aimag": _get_param(request, "aimag"),
        "sum": _get_param(request, "sum"),
        "kind": _get_param(request, "kind"),
        "status": _get_param(request, "status"),
        "location_type": _get_param(request, "location_type"),
        "date_from": _get_param(request, "date_from"),
        "date_to": _get_param(request, "date_to"),
    }


def reports_hub_view(request: HttpRequest, admin_site: Optional[AdminSite] = None) -> HttpResponse:
    """
    IMPORTANT:
      - Must receive the *same* AdminSite instance that serves /django-admin/,
        otherwise reverse('app_list') may fail (NoReverseMatch).
    Usage in admin.py:
      path("reports/", self.admin_view(lambda r: reports_hub_view(r, admin_site=self)), name="reports-hub")
    """
    site = admin_site or dj_admin.site
    flt = _current_filter(request)
    is_scoped = (not request.user.is_superuser) and _is_aimag_engineer(request)

    # choices
    aimags_qs = _scope_qs(request, Aimag.objects.all().order_by("name"), "id")
    aimag_choices = [(a.id, a.name) for a in aimags_qs]

    sums_qs = SumDuureg.objects.all().order_by("name")
    if flt["aimag"]:
        sums_qs = sums_qs.filter(aimag_id=flt["aimag"])
    sums_choices = [(s.id, s.name) for s in sums_qs[:5000]]

    kind_choices = list(getattr(Device, "KIND_CHOICES", Device.Kind.choices))
    status_choices = list(getattr(Device, "STATUS_CHOICES", []))
    loc_type_choices = list(getattr(Location, "LOCATION_TYPE_CHOICES", Location.LOCATION_TYPES))

    # cards (lightweight: based on current filters)
    devices_qs = _scope_qs(request, Device.objects.select_related("location"), "location__aimag_ref_id")
    devices_qs = _apply_device_filters(request, devices_qs)

    loc_qs = _scope_qs(request, Location.objects.all(), "aimag_ref_id")
    loc_qs = _apply_location_filters(request, loc_qs)

    date_from, date_to = _date_window(request)
    start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())

    ms_qs = _scope_qs(request, MaintenanceService.objects.all(), "device__location__aimag_ref_id")
    ca_qs = _scope_qs(request, ControlAdjustment.objects.all(), "device__location__aimag_ref_id")
    mv_qs = _scope_qs(request, DeviceMovement.objects.all(), f"{_MV_TO_FIELD}__aimag_ref_id")
    sp_qs = _scope_qs(request, SparePartOrder.objects.all(), "aimag_id")

    # apply same location-related filters (aimag/sum/location_type/kind/status) to workflow datasets where possible
    if flt["aimag"]:
        ms_qs = ms_qs.filter(device__location__aimag_ref_id=flt["aimag"])
        ca_qs = ca_qs.filter(device__location__aimag_ref_id=flt["aimag"])
        mv_qs = mv_qs.filter(**{f"{_MV_TO_FIELD}__aimag_ref_id": flt["aimag"]})
        sp_qs = sp_qs.filter(aimag_id=flt["aimag"])
    if flt["sum"]:
        ms_qs = ms_qs.filter(device__location__sum_ref_id=flt["sum"])
        ca_qs = ca_qs.filter(device__location__sum_ref_id=flt["sum"])
        mv_qs = mv_qs.filter(**{f"{_MV_TO_FIELD}__sum_ref_id": flt["sum"]})
    if flt["location_type"]:
        ms_qs = ms_qs.filter(device__location__location_type=flt["location_type"])
        ca_qs = ca_qs.filter(device__location__location_type=flt["location_type"])
        mv_qs = mv_qs.filter(**{f"{_MV_TO_FIELD}__location_type": flt["location_type"]})
    if flt["kind"]:
        ms_qs = ms_qs.filter(device__kind=flt["kind"])
        ca_qs = ca_qs.filter(device__kind=flt["kind"])
        mv_qs = mv_qs.filter(device__kind=flt["kind"])
    if flt["status"]:
        ms_qs = ms_qs.filter(device__status=flt["status"])
        ca_qs = ca_qs.filter(device__status=flt["status"])
        mv_qs = mv_qs.filter(device__status=flt["status"])

    # date window
    ms_qs_window = ms_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    ca_qs_window = ca_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    mv_qs_window = mv_qs.filter(moved_at__gte=start_dt, moved_at__lt=end_dt)
    sp_qs_window = sp_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt) if hasattr(SparePartOrder, "created_at") else sp_qs

    cards = [
        {"k": "Devices (filtered)", "v": devices_qs.count()},
        {"k": "Locations (filtered)", "v": loc_qs.count()},
        {"k": "Movements (window)", "v": mv_qs_window.count()},
        {"k": "Maintenance (window)", "v": ms_qs_window.count()},
        {"k": "Control (window)", "v": ca_qs_window.count()},
        {"k": "SparePart orders (window)", "v": sp_qs_window.count()},
    ]

    # urls (custom AdminSite namespace!)
    ns = site.name or "admin"
    hub_url = reverse(f"{ns}:reports-hub")
    chart_url = reverse(f"{ns}:reports-chart-json")
    sums_url = reverse(f"{ns}:reports-sums-json")

    export_links = [
        {"label": "Devices CSV", "url": reverse(f"{ns}:reports-export-devices")},
        {"label": "Locations CSV", "url": reverse(f"{ns}:reports-export-locations")},
        {"label": "Movements CSV", "url": reverse(f"{ns}:reports-export-movements")},
        {"label": "Maintenance CSV", "url": reverse(f"{ns}:reports-export-maintenance")},
        {"label": "Control CSV", "url": reverse(f"{ns}:reports-export-control")},
        {"label": "Spareparts CSV", "url": reverse(f"{ns}:reports-export-spareparts")},
    ]

    ctx = {
        **site.each_context(request),
        "title": "Тайлан (Reports)",
        "hub_url": hub_url,
        "chart_url": chart_url,
        "sums_url": sums_url,
        "REPORT_CHOICES": REPORT_CHOICES,
        "METRIC_CHOICES": METRIC_CHOICES,
        "AIMAG_CHOICES": aimag_choices,
        "SUM_CHOICES": sums_choices,
        "KIND_CHOICES": kind_choices,
        "STATUS_CHOICES": status_choices,
        "LOCATION_TYPE_CHOICES": loc_type_choices,
        "EXPORT_LINKS": export_links,
        "CARDS": cards,
        "filter": flt,
        "is_scoped_user": is_scoped,
    }
    return render(request, "admin/inventory/reports/reports_hub.html", ctx)


# ============================================================
# API: sums by aimag (for dynamic dropdown)
# ============================================================

def reports_sums_json(request: HttpRequest) -> JsonResponse:
    aimag_id = _get_param(request, "aimag_id")
    qs = SumDuureg.objects.all().order_by("name")
    if aimag_id:
        qs = qs.filter(aimag_id=aimag_id)
    # If scoped user, enforce own aimag regardless of passed aimag_id
    if (not request.user.is_superuser) and _is_aimag_engineer(request):
        aid = _get_user_aimag_id(request)
        if aid:
            qs = qs.filter(aimag_id=aid)
        else:
            qs = qs.none()
    data = {"sums": [{"id": s.id, "name": s.name} for s in qs[:5000]]}
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})


# ============================================================
# Charts JSON (used by reports_hub.html JS)
# ============================================================

def _count_series_for_metric(request: HttpRequest, report: str, metric: str) -> List[Dict[str, Any]]:
    # devices base (scoped + filters)
    dev_qs: QuerySet[Device] = _scope_qs(request, Device.objects.select_related("location", "location__aimag_ref", "location__sum_ref"), "location__aimag_ref_id")
    dev_qs = _apply_device_filters(request, dev_qs)

    if report == "locations":
        loc_qs: QuerySet[Location] = _scope_qs(request, Location.objects.select_related("aimag_ref", "sum_ref"), "aimag_ref_id")
        loc_qs = _apply_location_filters(request, loc_qs)

        if metric == "count_by_location_type":
            rows = loc_qs.values_list("location_type").annotate(c=Count("id")).values_list("location_type", "c")
            return _series_from_kv([(_choice_label(Location.LOCATION_TYPES, k), c) for k, c in rows])
        if metric == "count_by_aimag":
            rows = loc_qs.values_list("aimag_ref__name").annotate(c=Count("id")).values_list("aimag_ref__name", "c")
            return _series_from_kv(rows)
        if metric == "count_by_sum":
            rows = loc_qs.values_list("sum_ref__name").annotate(c=Count("id")).values_list("sum_ref__name", "c")
            return _series_from_kv(rows)
        if metric == "count_by_district":
            rows = loc_qs.exclude(district_name="").values_list("district_name").annotate(c=Count("id")).values_list("district_name", "c")
            return _series_from_kv(rows)
        # default: location type
        rows = loc_qs.values_list("location_type").annotate(c=Count("id")).values_list("location_type", "c")
        return _series_from_kv([(_choice_label(Location.LOCATION_TYPES, k), c) for k, c in rows])

    # workflow and movements still use device scoping for breakdowns
    if metric == "count_by_status":
        rows = dev_qs.values_list("status").annotate(c=Count("id")).values_list("status", "c")
        return _series_from_kv([(_choice_label(Device.STATUS_CHOICES, k), c) for k, c in rows])

    if metric == "count_by_kind":
        rows = dev_qs.values_list("kind").annotate(c=Count("id")).values_list("kind", "c")
        return _series_from_kv([(_choice_label(Device.Kind.choices, k), c) for k, c in rows])

    if metric == "count_by_location_type":
        rows = dev_qs.values_list("location__location_type").annotate(c=Count("id")).values_list("location__location_type", "c")
        return _series_from_kv([(_choice_label(Location.LOCATION_TYPES, k), c) for k, c in rows])

    if metric == "count_by_aimag":
        rows = dev_qs.values_list("location__aimag_ref__name").annotate(c=Count("id")).values_list("location__aimag_ref__name", "c")
        return _series_from_kv(rows)

    if metric == "count_by_sum":
        # prefer sum name, fallback to district_name for UB when sum_ref null
        rows = (
            dev_qs.values_list("location__sum_ref__name")
            .annotate(c=Count("id"))
            .values_list("location__sum_ref__name", "c")
        )
        return _series_from_kv(rows)

    if metric == "count_by_district":
        rows = (
            dev_qs.exclude(location__district_name="")
            .values_list("location__district_name")
            .annotate(c=Count("id"))
            .values_list("location__district_name", "c")
        )
        return _series_from_kv(rows)

    # fallback
    rows = dev_qs.values_list("kind").annotate(c=Count("id")).values_list("kind", "c")
    return _series_from_kv([(_choice_label(Device.Kind.choices, k), c) for k, c in rows])


def reports_chart_json(request: HttpRequest) -> JsonResponse:
    report = _get_param(request, "report") or "devices"
    metric = _get_param(request, "metric") or "count_by_kind"

    # --- Counts series (bar chart) ---
    counts_series = _count_series_for_metric(request, report, metric)

    # --- Workflow per day (line chart) ---
    date_from, date_to = _date_window(request)
    start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())

    # base qs scoped
    ms_qs: QuerySet[MaintenanceService] = _scope_qs(request, MaintenanceService.objects.all(), "device__location__aimag_ref_id")
    ca_qs: QuerySet[ControlAdjustment] = _scope_qs(request, ControlAdjustment.objects.all(), "device__location__aimag_ref_id")

    # apply same filters (aimag/sum/location_type/kind/status) where possible
    flt = _current_filter(request)
    if flt["aimag"]:
        ms_qs = ms_qs.filter(device__location__aimag_ref_id=flt["aimag"])
        ca_qs = ca_qs.filter(device__location__aimag_ref_id=flt["aimag"])
    if flt["sum"]:
        ms_qs = ms_qs.filter(device__location__sum_ref_id=flt["sum"])
        ca_qs = ca_qs.filter(device__location__sum_ref_id=flt["sum"])
    if flt["location_type"]:
        ms_qs = ms_qs.filter(device__location__location_type=flt["location_type"])
        ca_qs = ca_qs.filter(device__location__location_type=flt["location_type"])
    if flt["kind"]:
        ms_qs = ms_qs.filter(device__kind=flt["kind"])
        ca_qs = ca_qs.filter(device__kind=flt["kind"])
    if flt["status"]:
        ms_qs = ms_qs.filter(device__status=flt["status"])
        ca_qs = ca_qs.filter(device__status=flt["status"])

    # IMPORTANT: do NOT restrict only SUBMITTED; show all to avoid "хоосон" feeling.
    ms_by_day = dict(
        ms_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )
    ca_by_day = dict(
        ca_qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )

    axis: List[str] = []
    ms: List[int] = []
    ca: List[int] = []
    d = date_from
    while d <= date_to:
        axis.append(d.strftime("%Y-%m-%d"))
        ms.append(int(ms_by_day.get(d, 0) or 0))
        ca.append(int(ca_by_day.get(d, 0) or 0))
        d += timedelta(days=1)

    payload = {
        "counts": {"status": counts_series},
        "workflow": {"axis": axis, "ms": ms, "ca": ca},
        # backward-compat keys (some older JS expects these)
        "status_series": counts_series,
    }
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


# ============================================================
# CSV Export helpers
# ============================================================

def _csv_response(filename: str) -> HttpResponse:
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    # Excel-friendly UTF-8 BOM
    resp.write("\ufeff")
    return resp


def _write_csv(resp: HttpResponse, header: List[str], rows: List[List[object]]) -> HttpResponse:
    w = csv.writer(resp)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return resp


# ============================================================
# CSV Exports (scoped + filters)
# ============================================================

def reports_export_devices_csv(request: HttpRequest) -> HttpResponse:
    qs: QuerySet[Device] = _scope_qs(request, Device.objects.select_related("location", "location__aimag_ref", "location__sum_ref"), "location__aimag_ref_id")
    qs = _apply_device_filters(request, qs)

    rows: List[List[object]] = []
    for d in qs.order_by("id")[:50000]:
        loc = getattr(d, "location", None)
        rows.append([
            d.id,
            getattr(d, "serial_number", "") or "",
            getattr(d, "kind", "") or "",
            getattr(d, "status", "") or "",
            getattr(loc, "name", "") or "",
            getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            getattr(loc, "district_name", "") or "",
        ])

    resp = _csv_response("devices.csv")
    return _write_csv(resp, ["id", "serial_number", "kind", "status", "location", "aimag", "sum", "district"], rows)


def reports_export_locations_csv(request: HttpRequest) -> HttpResponse:
    qs: QuerySet[Location] = _scope_qs(request, Location.objects.select_related("aimag_ref", "sum_ref"), "aimag_ref_id")
    qs = _apply_location_filters(request, qs)

    rows: List[List[object]] = []
    for l in qs.order_by("id")[:50000]:
        rows.append([
            l.id,
            getattr(l, "name", "") or "",
            getattr(l, "location_type", "") or "",
            getattr(getattr(l, "aimag_ref", None), "name", "") or "",
            getattr(getattr(l, "sum_ref", None), "name", "") or "",
            getattr(l, "district_name", "") or "",
            getattr(l, "latitude", "") or "",
            getattr(l, "longitude", "") or "",
        ])

    resp = _csv_response("locations.csv")
    return _write_csv(resp, ["id", "name", "type", "aimag", "sum", "district", "lat", "lon"], rows)


def reports_export_movements_csv(request: HttpRequest) -> HttpResponse:
    # DeviceMovement naming differs across versions: (from_location/to_location) vs (source_location/destination_location)
    rel_fields = ["device"]
    if _MV_FROM_FIELD:
        rel_fields.append(_MV_FROM_FIELD)
    if _MV_TO_FIELD:
        rel_fields.append(_MV_TO_FIELD)
    qs: QuerySet[DeviceMovement] = _scope_qs(
        request,
        DeviceMovement.objects.select_related(*rel_fields),
        f"{_MV_TO_FIELD}__aimag_ref_id",
    )

    # apply filters via destination (where the device is now)
    flt = _current_filter(request)
    if flt["aimag"]:
        qs = qs.filter(**{f"{_MV_TO_FIELD}__aimag_ref_id": flt["aimag"]})
    if flt["sum"]:
        qs = qs.filter(**{f"{_MV_TO_FIELD}__sum_ref_id": flt["sum"]})
    if flt["location_type"]:
        qs = qs.filter(**{f"{_MV_TO_FIELD}__location_type": flt["location_type"]})
    if flt["kind"]:
        qs = qs.filter(device__kind=flt["kind"])
    if flt["status"]:
        qs = qs.filter(device__status=flt["status"])

    date_from, date_to = _date_window(request)
    start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())
    if hasattr(DeviceMovement, "moved_at"):
        qs = qs.filter(moved_at__gte=start_dt, moved_at__lt=end_dt)

    rows: List[List[object]] = []
    for m in qs.order_by("-id")[:50000]:
        src = getattr(m, _MV_FROM_FIELD, None)
        dst = getattr(m, _MV_TO_FIELD, None)
        rows.append([
            m.id,
            getattr(getattr(m, "device", None), "serial_number", "") or "",
            getattr(src, "name", "") or "",
            getattr(dst, "name", "") or "",
            getattr(m, "moved_at", "") or "",
            getattr(m, "reason", "") or "",
        ])

    resp = _csv_response("movements.csv")
    return _write_csv(resp, ["id", "device_serial", "from", "to", "moved_at", "reason"], rows)


def reports_export_maintenance_csv(request: HttpRequest) -> HttpResponse:
    qs: QuerySet[MaintenanceService] = _scope_qs(
        request,
        MaintenanceService.objects.select_related("device", "device__location", "device__location__aimag_ref", "device__location__sum_ref"),
        "device__location__aimag_ref_id",
    )
    flt = _current_filter(request)
    if flt["aimag"]:
        qs = qs.filter(device__location__aimag_ref_id=flt["aimag"])
    if flt["sum"]:
        qs = qs.filter(device__location__sum_ref_id=flt["sum"])
    if flt["location_type"]:
        qs = qs.filter(device__location__location_type=flt["location_type"])
    if flt["kind"]:
        qs = qs.filter(device__kind=flt["kind"])
    if flt["status"]:
        qs = qs.filter(device__status=flt["status"])

    date_from, date_to = _date_window(request)
    qs = qs.filter(date__gte=date_from, date__lte=date_to)

    rows: List[List[object]] = []
    for ms in qs.order_by("-id")[:50000]:
        d = getattr(ms, "device", None)
        loc = getattr(d, "location", None) if d else None
        rows.append([
            ms.id,
            getattr(ms, "date", "") or "",
            getattr(d, "serial_number", "") or "",
            getattr(d, "kind", "") or "",
            getattr(loc, "name", "") or "",
            getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            getattr(ms, "reason", "") or "",
            getattr(ms, "performer_type", "") or "",
            getattr(ms, "performer_engineer_name", "") or "",
            getattr(ms, "performer_org_name", "") or "",
            getattr(ms, "workflow_status", "") or "",
        ])

    resp = _csv_response("maintenance.csv")
    return _write_csv(resp, ["id", "date", "device_serial", "kind", "location", "aimag", "sum", "reason", "performer_type", "engineer", "org", "workflow_status"], rows)


def reports_export_control_csv(request: HttpRequest) -> HttpResponse:
    qs: QuerySet[ControlAdjustment] = _scope_qs(
        request,
        ControlAdjustment.objects.select_related("device", "device__location", "device__location__aimag_ref", "device__location__sum_ref"),
        "device__location__aimag_ref_id",
    )
    flt = _current_filter(request)
    if flt["aimag"]:
        qs = qs.filter(device__location__aimag_ref_id=flt["aimag"])
    if flt["sum"]:
        qs = qs.filter(device__location__sum_ref_id=flt["sum"])
    if flt["location_type"]:
        qs = qs.filter(device__location__location_type=flt["location_type"])
    if flt["kind"]:
        qs = qs.filter(device__kind=flt["kind"])
    if flt["status"]:
        qs = qs.filter(device__status=flt["status"])

    date_from, date_to = _date_window(request)
    qs = qs.filter(date__gte=date_from, date__lte=date_to)

    rows: List[List[object]] = []
    for ca in qs.order_by("-id")[:50000]:
        d = getattr(ca, "device", None)
        loc = getattr(d, "location", None) if d else None
        rows.append([
            ca.id,
            getattr(ca, "date", "") or "",
            getattr(d, "serial_number", "") or "",
            getattr(d, "kind", "") or "",
            getattr(loc, "name", "") or "",
            getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            getattr(ca, "note", "") or "",
            getattr(ca, "workflow_status", "") or "",
        ])

    resp = _csv_response("control.csv")
    return _write_csv(resp, ["id", "date", "device_serial", "kind", "location", "aimag", "sum", "note", "workflow_status"], rows)


def reports_export_spareparts_csv(request: HttpRequest) -> HttpResponse:
    qs: QuerySet[SparePartOrder] = _scope_qs(request, SparePartOrder.objects.all(), "aimag_id")
    flt = _current_filter(request)
    if flt["aimag"]:
        qs = qs.filter(aimag_id=flt["aimag"])

    date_from, date_to = _date_window(request)
    if hasattr(SparePartOrder, "created_at"):
        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
        end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())
        qs = qs.filter(created_at__gte=start_dt, created_at__lt=end_dt)

    rows: List[List[object]] = []
    for o in qs.order_by("-id")[:50000]:
        rows.append([
            o.id,
            getattr(getattr(o, "aimag", None), "name", "") or "",
            getattr(o, "created_at", "") or "",
            getattr(o, "note", "") or "",
            getattr(o, "status", "") or "",
        ])

    resp = _csv_response("spareparts.csv")
    return _write_csv(resp, ["id", "aimag", "created_at", "note", "status"], rows)
