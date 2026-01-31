# inventory/admin_dashboard.py
# -*- coding: utf-8 -*-
"""
Enterprise dashboard backend (cards + ECharts + map + exports)
- Keeps legacy fields (locations_json + p.color) to avoid breaking older JS/templates.
- Adds unified template context:
    echarts_status_json, echarts_workflow_json, date_from/date_to,
    totals for cards, and per-point admin URLs.
"""

import csv
import json
from datetime import date, datetime, timedelta

from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Prefetch
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from openpyxl import Workbook

from .dashboard import build_dashboard_context, scoped_devices_qs
from .models import Location, Device, InstrumentCatalog, MaintenanceService, ControlAdjustment, DeviceMovement



def _calibration_counts(user):
    """Return counts for verification buckets for the user's scoped devices."""
    qs = scoped_devices_qs(user).only("id", "next_verification_date")
    today = timezone.localdate()
    expired = qs.filter(next_verification_date__lt=today).count()
    due_30 = qs.filter(next_verification_date__gte=today, next_verification_date__lte=today + timedelta(days=30)).count()
    due_90 = qs.filter(next_verification_date__gt=today + timedelta(days=30), next_verification_date__lte=today + timedelta(days=90)).count()
    unknown = qs.filter(next_verification_date__isnull=True).count()
    ok = qs.filter(next_verification_date__gt=today + timedelta(days=90)).count()
    return {
        "calib_expired": expired,
        "calib_due_30": due_30,
        "calib_due_90": due_90,
        "calib_unknown": unknown,
        "calib_ok": ok,
        "calib_today": today,
    }

# ============================================================
# 8 төрөл — Location.location_type
# ============================================================
LOCATION_TYPE_COLOR = {
    "WEATHER": "#4b3bff",
    "AWS": "#f2b233",
    "HYDRO": "#1f8f3a",
    "AEROLOGY": "#a000c8",
    "AGRO": "#6a5a2a",
    "ETALON": "#c0392b",
    "RADAR": "#ff3b30",
    "OTHER": "#7f8c8d",
}


def _get_param(request, key: str) -> str:
    return (request.GET.get(key) or "").strip()

def _choices_from_model(model, attr_names):
    for a in attr_names:
        ch = getattr(model, a, None)
        if ch:
            return list(ch)
    return []

def _append_query(base_url: str, params: dict) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "", [])}
    if not clean:
        return base_url
    joiner = "&" if ("?" in base_url) else "?"
    return base_url + joiner + urlencode(clean)

def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _get_admin_namespace(request: HttpRequest) -> str:
    # Prefer current resolver namespace (works for both /admin/ and /django-admin/)
    ns = getattr(getattr(request, "resolver_match", None), "namespace", None)
    return ns or "admin"


def _admin_url(request: HttpRequest, viewname_suffix: str, *args, **kwargs) -> str:
    ns = _get_admin_namespace(request)
    try:
        return reverse(f"{ns}:{viewname_suffix}", args=args, kwargs=kwargs)
    except Exception:
        # Fallback to default admin namespace
        return reverse(f"admin:{viewname_suffix}", args=args, kwargs=kwargs)


@staff_member_required(login_url="/django-admin/login/")
def dashboard_table_view(request: HttpRequest):
    """
    KPI/table dashboard (legacy).
    """
    ctx = build_dashboard_context(request.user)
    ctx.update(_calibration_counts(request.user))
    ctx.update(_calibration_counts(request.user))
    return render(request, "admin/dashboard.html", ctx)


@staff_member_required(login_url="/django-admin/login/")
def dashboard_graph_view(request: HttpRequest):
    """
    Unified dashboard page:
    - cards
    - ECharts (status bar + workflow stacked)
    - Leaflet map (pending/status)

    Template:
        admin/inventory/reports/dashboard_graph.html

    NOTE: that template is the "dashboard_unified.html" content, but saved under the
          expected path so /admin/dashboard/graph/ won't crash.
    """
    user = request.user
    # --------------------
    # GET filters (enterprise)
    # --------------------
    f_status = _get_param(request, "status")           # Device.status
    f_kind = _get_param(request, "kind")               # Device.kind (if exists)
    f_loc_type = _get_param(request, "location_type")  # Location.location_type / kind

    # choices for UI
    kind_choices = _choices_from_model(Device, ["KIND_CHOICES"]) or _choices_from_model(InstrumentCatalog, ["KIND_CHOICES"])
    loc_type_choices = _choices_from_model(Location, ["LOCATION_TYPE_CHOICES", "TYPE_CHOICES"])
    status_choices = [("Active", "Active"), ("Broken", "Broken"), ("Repair", "Repair"), ("Retired", "Retired")]


    # --------------------
    # Date range (for workflow chart)
    # --------------------
    today = timezone.localdate()
    date_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = _parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # --------------------
    # Scope
    # --------------------
    devices_qs = scoped_devices_qs(user).select_related("location", "catalog_item", "location__aimag_ref")
    # Apply device filters
    if f_status:
        devices_qs = devices_qs.filter(status=f_status)

    # Device дээр kind талбар байвал
    if f_kind and hasattr(Device, "kind"):
        devices_qs = devices_qs.filter(kind=f_kind)

    loc_ids = (
        devices_qs.exclude(location__isnull=True)
        .values_list("location_id", flat=True)
        .distinct()
    )
    loc_qs = Location.objects.filter(id__in=loc_ids).select_related("aimag_ref", "sum_ref", "owner_org")
    # Apply location filters
    if f_loc_type:
        if hasattr(Location, "location_type"):
            loc_qs = loc_qs.filter(location_type=f_loc_type)
        elif hasattr(Location, "kind"):
            loc_qs = loc_qs.filter(kind=f_loc_type)


    # --------------------
    # Cards (location/device/pending)
    # --------------------
    total_locations = loc_qs.count()
    total_devices = devices_qs.count()

    empty_locations = loc_qs.filter(devices__isnull=True).distinct().count()
    broken_locations = loc_qs.filter(devices__status__in=["Broken", "Repair"]).distinct().count()
    ok_locations = max(total_locations - empty_locations - broken_locations, 0)

    pending_ms = MaintenanceService.objects.filter(workflow_status="SUBMITTED", device__location_id__in=loc_ids)
    pending_ca = ControlAdjustment.objects.filter(workflow_status="SUBMITTED", device__location_id__in=loc_ids)
    pending_total_items = pending_ms.count() + pending_ca.count()
    pending_location_ids = set(pending_ms.values_list("device__location_id", flat=True)) | set(
        pending_ca.values_list("device__location_id", flat=True)
    )
    pending_locations = len([x for x in pending_location_ids if x])


    # --------------------
    # ECharts: Status series (click -> admin list filter)
    # --------------------
    status_counts = list(
        devices_qs.values("status").annotate(c=Count("id")).order_by("-c")
    )

    dev_changelist = _admin_url(request, "inventory_device_changelist")

    # Build common params that keep current filter state
    common_params = {}
    if f_kind:
        common_params["kind__exact"] = f_kind

    if f_loc_type:
        if hasattr(Location, "location_type"):
            common_params["location__location_type__exact"] = f_loc_type
        elif hasattr(Location, "kind"):
            common_params["location__kind__exact"] = f_loc_type

    status_series = []
    for row in status_counts:
        st = (row.get("status") or "UNKNOWN")
        cnt = int(row.get("c") or 0)
        url = _append_query(dev_changelist, {"status__exact": st, **common_params})
        status_series.append({"name": st, "value": cnt, "url": url})

    # --------------------
    # ECharts: Workflow series (SUBMITTED per day)
    # --------------------
    start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())

    ms_by_day = dict(
        MaintenanceService.objects.filter(
            workflow_status="SUBMITTED",
            device__location_id__in=loc_ids,
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        )
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )
    ca_by_day = dict(
        ControlAdjustment.objects.filter(
            workflow_status="SUBMITTED",
            device__location_id__in=loc_ids,
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        )
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )

    axis = []
    ms = []
    ca = []
    d = date_from
    while d <= date_to:
        axis.append(d.strftime("%Y-%m-%d"))
        ms.append(int(ms_by_day.get(d, 0) or 0))
        ca.append(int(ca_by_day.get(d, 0) or 0))
        d += timedelta(days=1)

    wf = {"axis": axis, "ms": ms, "ca": ca}

    # --------------------
    # Map points (legacy + enriched)
    # --------------------
    devices_prefetch = Prefetch(
        "devices",
        queryset=(
            Device.objects.filter(location_id__in=loc_ids)
            .only("id", "status", "serial_number", "location_id")
        ),
    )
    points = []
    recent_window = timezone.now() - timedelta(days=30)

    for loc in loc_qs.prefetch_related(devices_prefetch):
        lat = _safe_float(getattr(loc, "latitude", None) or getattr(loc, "lat", None))
        lon = _safe_float(getattr(loc, "longitude", None) or getattr(loc, "lon", None))
        if lat is None or lon is None:
            continue

        # status counts
        counts = {}
        devs = list(getattr(loc, "devices", []).all()) if hasattr(getattr(loc, "devices", None), "all") else list(getattr(loc, "devices", []) or [])
        for dvc in devs:
            s = getattr(dvc, "status", None) or "UNKNOWN"
            counts[s] = counts.get(s, 0) + 1

        device_count = sum(counts.values())

        # pending per location
        pending = 0
        if loc.id in pending_location_ids:
            pending = (
                pending_ms.filter(device__location_id=loc.id).count()
                + pending_ca.filter(device__location_id=loc.id).count()
            )

        # last activity dates (for coloring)
        last_ms = (
            MaintenanceService.objects.filter(device__location_id=loc.id)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        last_ca = (
            ControlAdjustment.objects.filter(device__location_id=loc.id)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )

        # derived location status (for map)
        status = "OK"
        status_color = "green"
        if device_count == 0:
            status = "EMPTY"
            status_color = "gray"
        elif counts.get("Broken", 0) > 0 or counts.get("Repair", 0) > 0:
            status = "BROKEN"
            status_color = "red"
        else:
            recent_ok = False
            if last_ms and last_ms >= recent_window:
                recent_ok = True
            if last_ca and last_ca >= recent_window:
                recent_ok = True
            status = "OK_RECENT" if recent_ok else "OK"
            status_color = "green"

        # legacy color for older JS
        legacy_color = "green"
        if counts.get("Broken", 0) > 0 or counts.get("Repair", 0) > 0:
            legacy_color = "red"
        elif device_count == 0:
            legacy_color = "gray"

        loc_type = (getattr(loc, "location_type", None) or "OTHER").strip().upper()
        if loc_type not in LOCATION_TYPE_COLOR:
            loc_type = "OTHER"

        loc_change_url = _admin_url(request, "inventory_location_change", loc.id)
        dev_list_url = _admin_url(request, "inventory_device_changelist") + f"?location__id__exact={loc.id}"

        points.append(
            {
                "id": loc.id,
                "name": getattr(loc, "name", "") or str(loc),
                "lat": lat,
                "lon": lon,

                # 8 төрөл
                "type": loc_type,
                "location_type": loc_type,
                "type_color": LOCATION_TYPE_COLOR.get(loc_type, LOCATION_TYPE_COLOR["OTHER"]),
                "type_label": loc.get_location_type_display() if hasattr(loc, "get_location_type_display") else loc_type,

                # status
                "status": status,
                "status_color": status_color,
                "color": legacy_color,  # legacy

                # popup links
                "loc_admin_url": loc_change_url,
                "device_list_url": dev_list_url,

                # misc for future UI
                "device_count": device_count,
                "counts": counts,
                "pending_total": pending,  # dashboard_unified.html expects pending_total
                "pending_workflow_count": pending,
                "last_maintenance_date": last_ms.isoformat() if last_ms else None,
                "last_control_date": last_ca.isoformat() if last_ca else None,
            }
        )

    ctx = {
        **(_admin_each_context(request)),
        "title": "Dashboard (График)",
        # UI filters (keep state in template + export links)
        "filter_status": f_status,
        "filter_kind": f_kind,
        "filter_location_type": f_loc_type,
        "kind_choices": kind_choices,
        "location_type_choices": loc_type_choices,
        "status_choices": status_choices,

        "date_from": date_from,
        "date_to": date_to,

        # cards
        "total_locations": total_locations,
        "total_devices": total_devices,
        "pending_total_items": pending_total_items,
        "pending_locations": pending_locations,
        "broken_locations": broken_locations,
        "empty_locations": empty_locations,
        "ok_locations": ok_locations,

        # charts + map data
        "echarts_status_json": json.dumps(status_series, ensure_ascii=False, cls=DjangoJSONEncoder),
        "echarts_workflow_json": json.dumps(wf, ensure_ascii=False, cls=DjangoJSONEncoder),
        "locations_json": json.dumps(points, ensure_ascii=False, cls=DjangoJSONEncoder),
    }

    return render(request, "admin/inventory/reports/dashboard_graph.html", ctx)


def _admin_each_context(request: HttpRequest) -> dict:
    """
    Provide admin context for both default AdminSite and custom AdminSite.
    """
    from django.contrib import admin as dj_admin

    # If a custom AdminSite is in play, Django will set it on request.current_app;
    # but safest is to use the global site context.
    try:
        return dj_admin.site.each_context(request)
    except Exception:
        return {}


@staff_member_required(login_url="/django-admin/login/")
def export_devices_csv(request: HttpRequest):
    """
    CSV export (scope мөрдөнө). Optional: reuse current GET params.
    """
    qs = scoped_devices_qs(request.user).select_related("catalog_item", "location")
    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    if f_status:
        qs = qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        qs = qs.filter(kind=f_kind)

    # location_type filter (location дээр ямар field байгаагаас хамаарна)
    if f_loc_type:
        if hasattr(Location, "location_type"):
            qs = qs.filter(location__location_type=f_loc_type)
        elif hasattr(Location, "kind"):
            qs = qs.filter(location__kind=f_loc_type)


    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="devices_export.csv"'
    resp.write("\ufeff")  # Excel UTF-8 BOM

    w = csv.writer(resp)
    w.writerow(["ID", "Төрөл(kind)", "Каталогийн нэр", "Бусад нэр", "Байршил", "Серийн дугаар", "Төлөв(status)"])

    for d in qs:
        kind = d.catalog_item.get_kind_display() if getattr(d, "catalog_item", None) else "-"
        cat_name = getattr(getattr(d, "catalog_item", None), "name_mn", None) or "-"
        loc_name = str(getattr(d, "location", "")) if getattr(d, "location", None) else "-"
        w.writerow([d.id, kind, cat_name, getattr(d, "other_name", "") or "", loc_name, getattr(d, "serial_number", "-"), getattr(d, "status", "-")])

    return resp


@staff_member_required(login_url="/django-admin/login/")
def export_devices_xlsx(request: HttpRequest):
    """
    Excel export (scope мөрдөнө).
    """
    qs = scoped_devices_qs(request.user).select_related("catalog_item", "location").order_by("id")
    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    if f_status:
        qs = qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        qs = qs.filter(kind=f_kind)

    # location_type filter (location дээр ямар field байгаагаас хамаарна)
    if f_loc_type:
        if hasattr(Location, "location_type"):
            qs = qs.filter(location__location_type=f_loc_type)
        elif hasattr(Location, "kind"):
            qs = qs.filter(location__kind=f_loc_type)


    wb = Workbook()
    ws = wb.active
    ws.title = "Devices"
    ws.append(["ID", "Төрөл(kind)", "Каталогийн нэр", "Бусад нэр", "Байршил", "Серийн дугаар", "Төлөв(status)"])

    for d in qs:
        kind = d.catalog_item.get_kind_display() if getattr(d, "catalog_item", None) else "-"
        cat_name = getattr(getattr(d, "catalog_item", None), "name_mn", None) or "-"
        loc_name = str(getattr(d, "location", "")) if getattr(d, "location", None) else "-"
        ws.append([d.id, kind, cat_name, getattr(d, "other_name", "") or "", loc_name, getattr(d, "serial_number", "-"), getattr(d, "status", "-")])

    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="devices_export.xlsx"'
    wb.save(resp)
    return resp


# ============================================================
# ✅ ReportsHub: additional exports + chart JSON
# ============================================================

@staff_member_required(login_url="/django-admin/login/")
def export_maintenance_csv(request: HttpRequest):
    """Maintenance CSV export.

    Default:
      - last 30 days (date__gte=today-30)
      - only device.status = Active
      - respects current scope (scoped_devices_qs)

    Optional GET params:
      - date_from=YYYY-MM-DD
      - date_to=YYYY-MM-DD
      - workflow_status=APPROVED|SUBMITTED|...
      - device_status=Active|Broken|Repair|Retired
    """
    today = timezone.localdate()
    d_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    d_to = _parse_date(request.GET.get("date_to")) or today
    if d_from > d_to:
        d_from, d_to = d_to, d_from

    wf = _get_param(request, "workflow_status")
    dev_status = _get_param(request, "device_status") or "Active"

    # scope: device ids
    device_ids = scoped_devices_qs(request.user).values_list("id", flat=True)

    qs = (
        MaintenanceService.objects
        .filter(device_id__in=device_ids, date__gte=d_from, date__lte=d_to)
        .select_related("device", "device__location", "device__location__aimag_ref", "device__location__sum_ref")
        .order_by("-date", "-id")
    )
    if wf:
        qs = qs.filter(workflow_status=wf)
    if dev_status:
        qs = qs.filter(device__status=dev_status)

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="maintenance_export.csv"'
    resp.write("\ufeff")  # Excel UTF-8 BOM

    w = csv.writer(resp)
    w.writerow([
        "ID", "Огноо", "Workflow", "DeviceID", "Төрөл(kind)", "Серийн дугаар",
        "Байршил", "Аймаг", "Сум/Дүүрэг", "Шалтгаан", "Гүйцэтгэсэн төрөл",
        "Инженер", "Байгууллага", "Тайлбар"
    ])

    for m in qs:
        d = m.device
        loc = getattr(d, "location", None)
        aimag = getattr(getattr(loc, "aimag_ref", None), "name", "") if loc else ""
        ssum = getattr(getattr(loc, "sum_ref", None), "name", "") if loc else ""
        kind = getattr(d, "kind", "") or ""
        w.writerow([
            m.id,
            getattr(m, "date", ""),
            getattr(m, "workflow_status", ""),
            getattr(d, "id", ""),
            kind,
            getattr(d, "serial_number", ""),
            str(loc) if loc else "",
            aimag,
            ssum,
            getattr(m, "reason", ""),
            getattr(m, "performer_type", ""),
            getattr(m, "performer_engineer_name", ""),
            getattr(m, "performer_org_name", ""),
            getattr(m, "note", ""),
        ])

    return resp


@staff_member_required(login_url="/django-admin/login/")
def export_movements_csv(request: HttpRequest):
    """Device movements CSV export (date range).

    GET params:
      - date_from=YYYY-MM-DD (optional, default=today-30)
      - date_to=YYYY-MM-DD   (optional, default=today)
      - kind=DEVICE_KIND (optional)
    """
    today = timezone.localdate()
    d_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    d_to = _parse_date(request.GET.get("date_to")) or today
    if d_from > d_to:
        d_from, d_to = d_to, d_from

    f_kind = _get_param(request, "kind")

    # scope: device ids
    device_ids = scoped_devices_qs(request.user).values_list("id", flat=True)

    start_dt = datetime.combine(d_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(d_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())

    qs = (
        DeviceMovement.objects
        .filter(device_id__in=device_ids, moved_at__gte=start_dt, moved_at__lt=end_dt)
        .select_related("device", "from_location", "to_location", "to_location__aimag_ref", "moved_by")
        .order_by("-moved_at", "-id")
    )
    if f_kind:
        qs = qs.filter(device__kind=f_kind)

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="movements_export.csv"'
    resp.write("\ufeff")  # Excel UTF-8 BOM

    w = csv.writer(resp)
    w.writerow([
        "ID", "MovedAt", "DeviceID", "Төрөл(kind)", "Серийн дугаар",
        "From", "To", "To-Aimag", "Шалтгаан", "MovedBy"
    ])

    for mv in qs:
        d = mv.device
        to_loc = mv.to_location
        to_aimag = getattr(getattr(to_loc, "aimag_ref", None), "name", "") if to_loc else ""
        moved_by = ""
        try:
            moved_by = str(mv.moved_by) if mv.moved_by else ""
        except Exception:
            moved_by = ""

        w.writerow([
            mv.id,
            mv.moved_at.isoformat() if mv.moved_at else "",
            getattr(d, "id", ""),
            getattr(d, "kind", "") or "",
            getattr(d, "serial_number", "") or "",
            str(mv.from_location) if mv.from_location else "",
            str(mv.to_location) if mv.to_location else "",
            to_aimag,
            getattr(mv, "reason", "") or "",
            moved_by,
        ])

    return resp


@staff_member_required(login_url="/django-admin/login/")
def reports_chart_json(request: HttpRequest):
    """Return ECharts payload as JSON.

    Reuses the same filters as dashboard_graph_view:
      - status, kind, location_type, date_from, date_to

    Response:
      {
        "status_series": [...],
        "workflow": {"axis":[...],"ms":[...],"ca":[...]}
      }
    """
    # Run the same computation as dashboard_graph_view but return only charts.
    user = request.user
    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    today = timezone.localdate()
    date_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = _parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    devices_qs = scoped_devices_qs(user).select_related("location", "catalog_item", "location__aimag_ref")
    if f_status:
        devices_qs = devices_qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        devices_qs = devices_qs.filter(kind=f_kind)

    loc_ids = (
        devices_qs.exclude(location__isnull=True)
        .values_list("location_id", flat=True)
        .distinct()
    )
    loc_qs = Location.objects.filter(id__in=loc_ids)
    if f_loc_type:
        if hasattr(Location, "location_type"):
            loc_qs = loc_qs.filter(location_type=f_loc_type)
        elif hasattr(Location, "kind"):
            loc_qs = loc_qs.filter(kind=f_loc_type)

    # constrain devices to filtered locations
    devices_qs = devices_qs.filter(location_id__in=loc_qs.values_list("id", flat=True))

    status_counts = list(devices_qs.values("status").annotate(c=Count("id")).order_by("-c"))
    status_series = [{"name": (r.get("status") or "UNKNOWN"), "value": int(r.get("c") or 0)} for r in status_counts]

    start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.get_current_timezone())

    ms_by_day = dict(
        MaintenanceService.objects.filter(
            workflow_status="SUBMITTED",
            device__location_id__in=loc_qs.values_list("id", flat=True),
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        )
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )
    ca_by_day = dict(
        ControlAdjustment.objects.filter(
            workflow_status="SUBMITTED",
            device__location_id__in=loc_qs.values_list("id", flat=True),
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        )
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .values_list("d", "c")
    )

    axis, ms, ca = [], [], []
    d = date_from
    while d <= date_to:
        axis.append(d.strftime("%Y-%m-%d"))
        ms.append(int(ms_by_day.get(d, 0) or 0))
        ca.append(int(ca_by_day.get(d, 0) or 0))
        d += timedelta(days=1)

    payload = {
        "counts": {"status": status_series},
        "workflow": {"axis": axis, "ms": ms, "ca": ca},
        # backward-compat keys
        "status_series": status_series,
    }
    return HttpResponse(json.dumps(payload, ensure_ascii=False, cls=DjangoJSONEncoder), content_type="application/json; charset=utf-8")


# ============================================================
# Compatibility endpoints (older urls.py expects these names)
# ============================================================

@staff_member_required(login_url="/django-admin/login/")
def chart_status_json(request: HttpRequest):
    """Backward-compatible: return only status series."""
    resp = reports_chart_json(request)
    try:
        data = json.loads(resp.content.decode("utf-8"))
    except Exception:
        data = {}
    return JsonResponse({"status_series": data.get("status_series") or data.get("counts") or []}, json_dumps_params={"ensure_ascii": False})

@staff_member_required(login_url="/django-admin/login/")
def chart_workflow_json(request: HttpRequest):
    """Backward-compatible: return only workflow series."""
    resp = reports_chart_json(request)
    try:
        data = json.loads(resp.content.decode("utf-8"))
    except Exception:
        data = {}
    wf = data.get("workflow") or {}
    return JsonResponse({"workflow": wf, "axis": wf.get("axis", []), "ms": wf.get("ms", []), "ca": wf.get("ca", [])}, json_dumps_params={"ensure_ascii": False})
