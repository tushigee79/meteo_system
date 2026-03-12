# inventory/admin_dashboard.py
from __future__ import annotations

import json
import csv
from datetime import date, timedelta, datetime

try:
    import openpyxl
except ImportError:
    openpyxl = None

from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Device, Location, MaintenanceService, ControlAdjustment, DeviceMovement

# ---------------------------------------------------------
# 1. Helpers & Setup
# ---------------------------------------------------------
try:
    from .dashboard import build_dashboard_context
except ImportError:
    def build_dashboard_context(user):
        return {}

try:
    from .dashboard_metrics import (
        build_calibration_counts,
        build_dashboard_spec,
    )
except ImportError:
    build_calibration_counts = None
    build_dashboard_spec = None

def _safe_float(v):
    if v is None or v == "": return None
    try:
        if isinstance(v, str): v = v.replace(",", ".")
        return float(v)
    except: return None

def _get_attr_any(obj, *names):
    for name in names:
        val = getattr(obj, name, None)
        if val is not None and val != "": return val
    return None

def _parse_date(s: str | None) -> date | None:
    if not s: return None
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except: return None

def _get_device_location(device: Device):
    for fname in ("location", "location_ref", "current_location", "station", "site"):
        loc = getattr(device, fname, None)
        if loc: return loc
    return None

def _get_str(request, key):
    """ GET параметрээс утга авах helper """
    val = request.GET.get(key, "").strip()
    return val if val else None

def _get_int(request, key):
    val = request.GET.get(key, "").strip()
    if val.isdigit():
        return int(val)
    return None

def _apply_aimag_scope(qs, request, field_name):
    """ Хэрэглэгчийн аймгаар шүүх helper """
    user = request.user
    if user.is_superuser:
        return qs
    
    prof = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if not prof:
        return qs 
    
    aimag_id = getattr(prof, "aimag_id", None)
    if aimag_id:
        return qs.filter(**{field_name: aimag_id})
    
    return qs

# ---------------------------------------------------------
# 2. Chart Builders
# ---------------------------------------------------------

def _build_workflow_counts_for_range(user, devices_qs, date_from: date, date_to: date):
    ms_qs = MaintenanceService.objects.filter(device__in=devices_qs, date__gte=date_from, date__lte=date_to)
    ca_qs = ControlAdjustment.objects.filter(device__in=devices_qs, date__gte=date_from, date__lte=date_to)

    ms_dates = ms_qs.values_list("date", flat=True)
    ca_dates = ca_qs.values_list("date", flat=True)

    ms_counts = {}
    for d_val in ms_dates:
        if not d_val: continue
        real_date = d_val.date() if isinstance(d_val, datetime) else d_val
        ms_counts[real_date] = ms_counts.get(real_date, 0) + 1

    ca_counts = {}
    for d_val in ca_dates:
        if not d_val: continue
        real_date = d_val.date() if isinstance(d_val, datetime) else d_val
        ca_counts[real_date] = ca_counts.get(real_date, 0) + 1

    axis, ms, ca = [], [], []
    d = date_from
    while d <= date_to:
        axis.append(d.strftime("%Y-%m-%d"))
        ms.append(int(ms_counts.get(d, 0)))
        ca.append(int(ca_counts.get(d, 0)))
        d += timedelta(days=1)

    return {"axis": axis, "ms": ms, "ca": ca}

def _build_status_timeline(user, devices_qs, date_from: date, date_to: date):
    qs = devices_qs.filter(installation_date__gte=date_from, installation_date__lte=date_to)
    data = qs.values_list("installation_date", "status")
    counts = {}
    
    for dt_val, status_val in data:
        if not dt_val: continue
        real_date = dt_val.date() if isinstance(dt_val, datetime) else dt_val
        d_str = real_date.strftime("%Y-%m-%d")
        st = str(status_val or "UNKNOWN")
        
        if d_str not in counts:
            counts[d_str] = {"Active": 0, "Broken": 0, "Repair": 0, "Stored": 0, "Other": 0}
            
        if st in ["Active", "Broken", "Repair", "Stored"]:
            counts[d_str][st] += 1
        else:
            counts[d_str]["Other"] += 1

    axis = []
    series = {"Active": [], "Broken": [], "Repair": [], "Stored": []}
    
    curr = date_from
    while curr <= date_to:
        d_str = curr.strftime("%Y-%m-%d")
        axis.append(d_str)
        day_data = counts.get(d_str, {})
        series["Active"].append(day_data.get("Active", 0))
        series["Broken"].append(day_data.get("Broken", 0))
        series["Repair"].append(day_data.get("Repair", 0))
        series["Stored"].append(day_data.get("Stored", 0))
        curr += timedelta(days=1)
        
    return {"axis": axis, "series": series}


# ---------------------------------------------------------
# 3. Main Views (Graphs & Dashboard)
# ---------------------------------------------------------

@staff_member_required(login_url="/django-admin/login/")
def dashboard_graph_view(request: HttpRequest):
    user = request.user
    ctx = build_dashboard_context(user)

    today = timezone.localdate()
    date_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = _parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    devices_qs = Device.objects.all()

    # Filters
    f_status = request.GET.get("status")
    f_kind = request.GET.get("kind")
    f_loc_type = request.GET.get("location_type")

    if f_status: devices_qs = devices_qs.filter(status=f_status)
    if f_kind: devices_qs = devices_qs.filter(kind=f_kind)
    if f_loc_type: devices_qs = devices_qs.filter(location__type=f_loc_type)

    if build_calibration_counts:
        cal = build_calibration_counts(user) or {}
        ctx.update(cal)

    # 1. Status Chart
    status_timeline = _build_status_timeline(user, devices_qs, date_from, date_to)
    ctx["devices_by_status_json"] = json.dumps(status_timeline, ensure_ascii=False, cls=DjangoJSONEncoder)

    # 2. Workflow Chart
    wf = _build_workflow_counts_for_range(user, devices_qs, date_from, date_to)
    ctx["workflow_json"] = json.dumps(wf, ensure_ascii=False, cls=DjangoJSONEncoder)

    # 3. Map Points Logic
    points = []
    for d in devices_qs.select_related("location"):
        loc = _get_device_location(d)
        if not loc: continue
        
        raw_lat = _get_attr_any(loc, "latitude", "lat", "gps_latitude", "y", "geo_lat", "north")
        raw_lon = _get_attr_any(loc, "longitude", "lon", "lng", "gps_longitude", "x", "geo_lon", "east")
        lat = _safe_float(raw_lat)
        lon = _safe_float(raw_lon)

        if lat is None or lon is None or (lat == 0 and lon == 0): continue
        
        p_type = getattr(d, "kind", None) or "OTHER"
        p_status = getattr(d, "status", None) or "Active"
        p_pending = 1 if str(p_status) in ["Broken", "Repair"] else 0

        points.append({
            "id": d.pk,
            "name": getattr(d, "serial_number", None) or str(d),
            "lat": lat, "lon": lon,
            "type": str(p_type), "status": str(p_status),
            "pending_total": int(p_pending),
        })
    
    ctx["locations_json"] = json.dumps(points, ensure_ascii=False, cls=DjangoJSONEncoder)
    ctx.setdefault("dashboard_spec_json", "{}")

    # AJAX Response
    if request.GET.get("ajax") == "1":
        return JsonResponse({
            "devices_by_status": status_timeline,
            "workflow": wf,
            "locations": points,
        }, json_dumps_params={"ensure_ascii": False, "cls": DjangoJSONEncoder})
    
    ctx.update({
        "filter_date_from": date_from.isoformat(),
        "filter_date_to": date_to.isoformat(),
        "filter_status": f_status or "",
        "filter_kind": f_kind or "",
        "filter_location_type": f_loc_type or "",
    })

    return render(request, "admin/inventory/reports/dashboard_graph.html", ctx)

@staff_member_required(login_url="/django-admin/login/")
def dashboard_table_view(request: HttpRequest):
    user = request.user
    ctx = build_dashboard_context(user)
    return render(request, "admin/inventory/reports/dashboard_table.html", ctx)


# ---------------------------------------------------------
# 4. Reports Table API (ReportsHub) - ШҮҮЛТҮҮР НЭМСЭН
# ---------------------------------------------------------

@staff_member_required(login_url="/django-admin/login/")
def reports_table_json(request: HttpRequest):
    """
    ReportsHub-ийн хүснэгтийн өгөгдлийг AJAX-аар буцаана.
    Шүүлтүүрүүд: report_type, location_type, date_from, date_to
    """
    report = _get_str(request, "report")
    
    # Алхам 1️⃣ — request-ээс параметрүүдийг авах (1 удаа)
    loc_type = _get_str(request, "location_type")
    date_from = _get_str(request, "date_from")
    date_to = _get_str(request, "date_to")
    
    # Бусад параметрүүд
    aimag_id = _get_int(request, "aimag")
    sum_id = _get_int(request, "sum")
    kind = _get_str(request, "kind")
    status = _get_str(request, "status")
    q = _get_str(request, "q")

    rows = []

    # ==========================
    # DEVICES
    # ==========================
    if report == "devices":
        qs = Device.objects.select_related("location", "instrument")
        qs = _apply_aimag_scope(qs, request, "location__aimag_ref_id") # Note: using ref_id

        if aimag_id: qs = qs.filter(location__aimag_ref_id=aimag_id)
        if sum_id: qs = qs.filter(location__sum_ref_id=sum_id)
        if kind: qs = qs.filter(kind=kind)
        if status: qs = qs.filter(status=status)
        if loc_type: qs = qs.filter(location__location_type=loc_type)
        if q:
            qs = qs.filter(Q(serial_number__icontains=q) | Q(location__name__icontains=q))

        for d in qs.order_by("-id")[:500]:
            rows.append({
                "c1": d.id,
                "c2": d.serial_number or "",
                "c3": str(d.location or ""),
                "c4": d.kind,
                "c5": d.status,
                "c6": str(d.updated_at) if hasattr(d, 'updated_at') else ""
            })
            
    # ==========================
    # LOCATIONS
    # ==========================
    elif report == "locations":
        qs = Location.objects.select_related("aimag_ref", "sum_ref")
        qs = _apply_aimag_scope(qs, request, "aimag_ref_id")

        if aimag_id: qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id: qs = qs.filter(sum_ref_id=sum_id)
        if loc_type: qs = qs.filter(location_type=loc_type)
        if q: qs = qs.filter(name__icontains=q)

        for l in qs.order_by("-id")[:500]:
            rows.append({
                "c1": l.id,
                "c2": l.name,
                "c3": l.location_type,
                "c4": str(l.aimag_ref or ""),
                "c5": str(l.sum_ref or ""),
                "c6": l.code or ""
            })

    # ==========================
    # MOVEMENTS (DeviceMovement)
    # ==========================
    elif report == "movements":
        qs = DeviceMovement.objects.select_related("device", "from_location", "to_location")
        qs = _apply_aimag_scope(qs, request, "to_location__aimag_ref_id")

        # ⬇⬇⬇ ШҮҮЛТҮҮРҮҮД ⬇⬇⬇
        if date_from:
            qs = qs.filter(moved_at__gte=date_from)
        if date_to:
            qs = qs.filter(moved_at__lte=date_to)

        if loc_type:
            qs = qs.filter(
                Q(to_location__location_type=loc_type) |
                Q(device__location__location_type=loc_type)
            )
        
        if aimag_id: qs = qs.filter(to_location__aimag_ref_id=aimag_id)
        if q: qs = qs.filter(device__serial_number__icontains=q)
        # ⬆⬆⬆ 

        for m in qs.order_by("-moved_at", "-id")[:500]:
            rows.append({
                "c1": m.moved_at.strftime("%Y-%m-%d") if m.moved_at else "-",
                "c2": str(m.device),
                "c3": str(m.from_location or "-"),
                "c4": str(m.to_location or "-"),
                "c5": m.reason or "",
                "c6": str(m.moved_by or "")
            })

    # ==========================
    # MAINTENANCE (MaintenanceService)
    # ==========================
    elif report == "maintenance":
        qs = MaintenanceService.objects.select_related("device", "device__location")
        qs = _apply_aimag_scope(qs, request, "device__location__aimag_ref_id")

        # ⬇⬇⬇ ШҮҮЛТҮҮРҮҮД ⬇⬇⬇
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        if loc_type:
            qs = qs.filter(device__location__location_type=loc_type)
        
        if aimag_id: qs = qs.filter(device__location__aimag_ref_id=aimag_id)
        if status: qs = qs.filter(workflow_status=status)
        if q: qs = qs.filter(device__serial_number__icontains=q)
        # ⬆⬆⬆ 

        for x in qs.order_by("-date", "-id")[:500]:
            rows.append({
                "c1": x.date.strftime("%Y-%m-%d") if x.date else "-",
                "c2": str(x.device),
                "c3": x.workflow_status,
                "c4": x.performer_type,
                "c5": x.reason or ""
            })

    # ==========================
    # CONTROL (ControlAdjustment)
    # ==========================
    elif report == "control":
        qs = ControlAdjustment.objects.select_related("device", "device__location")
        qs = _apply_aimag_scope(qs, request, "device__location__aimag_ref_id")

        # ⬇⬇⬇ ШҮҮЛТҮҮРҮҮД ⬇⬇⬇
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        if loc_type:
            qs = qs.filter(device__location__location_type=loc_type)
        
        if aimag_id: qs = qs.filter(device__location__aimag_ref_id=aimag_id)
        if status: qs = qs.filter(workflow_status=status)
        if q: qs = qs.filter(device__serial_number__icontains=q)
        # ⬆⬆⬆ 

        for x in qs.order_by("-date", "-id")[:500]:
            rows.append({
                "c1": x.date.strftime("%Y-%m-%d") if x.date else "-",
                "c2": str(x.device),
                "c3": x.workflow_status,
                "c4": x.result,
                "c5": x.performer_type
            })

    return JsonResponse(rows, safe=False)


# --- EXPORTS & API (Legacy) ---
@staff_member_required(login_url="/django-admin/login/")
def export_devices_csv(request: HttpRequest):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="devices.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Serial Number', 'Status', 'Location', 'Type', 'Updated'])
    for d in Device.objects.all().select_related('location'):
        writer.writerow([d.id, d.serial_number, d.status, d.location.name if d.location else "", getattr(d,'kind',''), d.updated_at if hasattr(d,'updated_at') else ''])
    return response

@staff_member_required(login_url="/django-admin/login/")
def export_devices_xlsx(request: HttpRequest):
    if not openpyxl: return HttpResponse("No openpyxl", status=500)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="devices.xlsx"'
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(['ID', 'Serial', 'Status', 'Location'])
    for d in Device.objects.all().select_related('location'):
        ws.append([d.id, d.serial_number, d.status, d.location.name if d.location else ""])
    wb.save(response)
    return response

@staff_member_required(login_url="/django-admin/login/")
def export_maintenance_csv(request: HttpRequest):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Date', 'Device', 'Status'])
    for ms in MaintenanceService.objects.all():
        writer.writerow([ms.id, ms.date, str(ms.device), getattr(ms,'workflow_status','')])
    return response

@staff_member_required(login_url="/django-admin/login/")
def export_movements_csv(request: HttpRequest):
    return HttpResponse("Not implemented", content_type='text/csv')

@staff_member_required(login_url="/django-admin/login/")
def chart_status_json(request: HttpRequest):
    devices_qs = Device.objects.all()
    if request.GET.get("kind"): devices_qs = devices_qs.filter(kind=request.GET.get("kind"))
    status_counts = list(devices_qs.values("status").annotate(c=Count("id")).order_by("status"))
    return JsonResponse([{"name": (r["status"] or "UNKNOWN"), "value": int(r["c"] or 0)} for r in status_counts], safe=False)

@staff_member_required(login_url="/django-admin/login/")
def chart_workflow_json(request: HttpRequest):
    user = request.user
    today = timezone.localdate()
    date_from = _parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = _parse_date(request.GET.get("date_to")) or today
    devices_qs = Device.objects.all()
    wf_data = _build_workflow_counts_for_range(user, devices_qs, date_from, date_to)
    return JsonResponse(wf_data, safe=False, json_dumps_params={"ensure_ascii": False})