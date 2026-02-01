from __future__ import annotations

import csv
from datetime import timedelta

try:
    import openpyxl  # pip install openpyxl
except ImportError:
    openpyxl = None

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse

from .models import Device, Location, MaintenanceService, ControlAdjustment

# Optional: your existing dashboard context
try:
    from .dashboard import build_dashboard_context
except Exception:
    def build_dashboard_context(user):
        return {}

from .dashboards.selectors import scoped_devices_qs
from .dashboards.services import (
    parse_date,
    resolve_location_type_field,
    build_status_timeline,
    build_workflow_timeline,
    build_map_points,
    dumps,
)


TEMPLATE_GRAPH = "admin/inventory/reports/dashboard_graph.html"
TEMPLATE_TABLE = "admin/inventory/reports/dashboard_table.html"


def _choices_from_model(model, attr_names: list[str]):
    for a in attr_names:
        v = getattr(model, a, None)
        if v:
            return v
    return []


def _get_param(request: HttpRequest, name: str) -> str | None:
    v = request.GET.get(name)
    return v if v not in ("", None) else None


import csv
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required(login_url="/django-admin/login/")
def export_movements_csv(request):
    """
    DeviceMovement model байвал movements.csv гаргана.
    Model хараахан байхгүй/импорт болохгүй бол server унахгүй 501 буцаана.
    """
    try:
        from .models import DeviceMovement
    except Exception:
        return HttpResponse("Not implemented: DeviceMovement model not found", status=501)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="movements.csv"'
    writer = csv.writer(response)

    writer.writerow(["ID", "Device", "From", "To", "Date", "Reason", "Approved By"])

    # FK нэршил өөр байж магадгүй тул getattr-оор safe
    qs = DeviceMovement.objects.all()

    for m in qs:
        writer.writerow([
            getattr(m, "id", ""),
            str(getattr(m, "device", "") or ""),
            str(getattr(m, "source", "") or getattr(m, "from_location", "") or ""),
            str(getattr(m, "destination", "") or getattr(m, "to_location", "") or ""),
            getattr(m, "date", "") or getattr(m, "moved_at", "") or "",
            getattr(m, "reason", "") or "",
            str(getattr(m, "approved_by", "") or ""),
        ])

    return response
@staff_member_required(login_url="/django-admin/login/")
def dashboard_graph_view(request: HttpRequest):
    user = request.user
    ctx = build_dashboard_context(user)

    today = timezone.localdate()
    date_from = parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    # scoped
    devices_qs = scoped_devices_qs(user).select_related("location")

    if f_status:
        devices_qs = devices_qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        devices_qs = devices_qs.filter(kind=f_kind)

    # location_type field (location_type vs type)
    loc_type_field = resolve_location_type_field()
    if f_loc_type and loc_type_field:
        devices_qs = devices_qs.filter(**{f"location__{loc_type_field}": f_loc_type})

    status_timeline = build_status_timeline(devices_qs, date_from, date_to)
    wf = build_workflow_timeline(devices_qs, date_from, date_to)
    points = build_map_points(devices_qs)

    ctx["devices_by_status_json"] = dumps(status_timeline)
    ctx["workflow_json"] = dumps(wf)
    ctx["locations_json"] = dumps(points)

    # UI state
    ctx.update({
        "filter_date_from": date_from.isoformat(),
        "filter_date_to": date_to.isoformat(),
        "filter_status": f_status or "",
        "filter_kind": f_kind or "",
        "filter_location_type": f_loc_type or "",
    })

    if request.GET.get("ajax") == "1":
        return JsonResponse(
            {"devices_by_status": status_timeline, "workflow": wf, "locations": points},
            json_dumps_params={"ensure_ascii": False},
        )

    return render(request, TEMPLATE_GRAPH, ctx)


    # ---- ui state
    ctx.update({
        "filter_date_from": date_from.isoformat(),
        "filter_date_to": date_to.isoformat(),
        "filter_status": f_status or "",
        "filter_kind": f_kind or "",
        "filter_location_type": f_loc_type or "",
    })

    # ---- ajax mode
    if request.GET.get("ajax") == "1":
        return JsonResponse(
            {"devices_by_status": status_timeline, "workflow": wf, "locations": points},
            json_dumps_params={"ensure_ascii": False},
        )

    return render(request, TEMPLATE_GRAPH, ctx)


@staff_member_required(login_url="/django-admin/login/")
def dashboard_table_view(request: HttpRequest):
    user = request.user
    ctx = build_dashboard_context(user)
    return render(request, TEMPLATE_TABLE, ctx)

@staff_member_required(login_url="/django-admin/login/")
def chart_status_json(request: HttpRequest):
    """
    Status timeline JSON (dashboard_graph.html template-тэй нийцтэй)
    """
    user = request.user
    today = timezone.localdate()
    date_from = parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    devices_qs = scoped_devices_qs(user).select_related("location")
    if f_status:
        devices_qs = devices_qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        devices_qs = devices_qs.filter(kind=f_kind)

    loc_type_field = resolve_location_type_field(Location)
    if f_loc_type and loc_type_field:
        devices_qs = devices_qs.filter(**{f"location__{loc_type_field}": f_loc_type})

    data = build_status_timeline(devices_qs, date_from, date_to)
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

from inventory.dashboards.services import build_verification_buckets
# ...

buckets = build_verification_buckets(devices_qs, Device)
ctx["verif_buckets"] = buckets
ctx["verif_buckets_json"] = dumps(buckets)  # dumps чинь танайд байгаа helper



@staff_member_required(login_url="/django-admin/login/")
def chart_workflow_json(request: HttpRequest):
    """
    Workflow timeline JSON (maintenance vs control)
    """
    user = request.user
    today = timezone.localdate()
    date_from = parse_date(request.GET.get("date_from")) or (today - timedelta(days=30))
    date_to = parse_date(request.GET.get("date_to")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    f_status = _get_param(request, "status")
    f_kind = _get_param(request, "kind")
    f_loc_type = _get_param(request, "location_type")

    devices_qs = scoped_devices_qs(user).select_related("location")
    if f_status:
        devices_qs = devices_qs.filter(status=f_status)
    if f_kind and hasattr(Device, "kind"):
        devices_qs = devices_qs.filter(kind=f_kind)

    loc_type_field = resolve_location_type_field(Location)
    if f_loc_type and loc_type_field:
        devices_qs = devices_qs.filter(**{f"location__{loc_type_field}": f_loc_type})

    data = build_workflow_timeline(devices_qs, date_from, date_to)
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False})

# -------------------------
# EXPORTS
# -------------------------

@staff_member_required(login_url="/django-admin/login/")
def export_devices_csv(request: HttpRequest):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="devices.csv"'
    w = csv.writer(response)
    w.writerow(["ID", "Serial Number", "Status", "Location", "Kind"])
    for d in scoped_devices_qs(request.user).select_related("location"):
        w.writerow([d.id, getattr(d, "serial_number", ""), getattr(d, "status", ""), getattr(getattr(d, "location", None), "name", ""), getattr(d, "kind", "")])
    return response


@staff_member_required(login_url="/django-admin/login/")
def export_devices_xlsx(request: HttpRequest):
    if not openpyxl:
        return HttpResponse("Server Error: openpyxl not installed", status=500)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="devices.xlsx"'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Serial", "Status", "Location", "Kind"])
    for d in scoped_devices_qs(request.user).select_related("location"):
        ws.append([d.id, getattr(d, "serial_number", ""), getattr(d, "status", ""), getattr(getattr(d, "location", None), "name", ""), getattr(d, "kind", "")])
    wb.save(response)
    return response


@staff_member_required(login_url="/django-admin/login/")
def export_maintenance_csv(request: HttpRequest):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="maintenance.csv"'
    w = csv.writer(response)
    w.writerow(["ID", "Date", "Device", "Workflow Status"])
    for ms in MaintenanceService.objects.all().select_related("device"):
        w.writerow([ms.id, getattr(ms, "date", ""), str(getattr(ms, "device", "")), getattr(ms, "workflow_status", "")])
    return response


@staff_member_required(login_url="/django-admin/login/")
def export_control_csv(request: HttpRequest):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="control.csv"'
    w = csv.writer(response)
    w.writerow(["ID", "Date", "Device", "Workflow Status"])
    for ca in ControlAdjustment.objects.all().select_related("device"):
        w.writerow([ca.id, getattr(ca, "date", ""), str(getattr(ca, "device", "")), getattr(ca, "workflow_status", "")])
    return response

# --- BACKWARD-COMPAT ALIASES (urls.py imports) ---
# Зарим хуучин urls.py dashboard_graph_view/dashboard_table_view гэж импортлодог.
# Шинэ файлд нэр өөр болсон байж магадгүй тул alias хийж өгнө.

try:
    dashboard_graph_view
except NameError:
    # хэрвээ танайд шинэ нэр нь dashboard_graph бол:
    try:
        dashboard_graph_view = dashboard_graph  # type: ignore
    except Exception:
        pass

try:
    dashboard_table_view
except NameError:
    # хэрвээ шинэ нэр нь dashboard_table бол:
    try:
        dashboard_table_view = dashboard_table  # type: ignore
    except Exception:
        pass
