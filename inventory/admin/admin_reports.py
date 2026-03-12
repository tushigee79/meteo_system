import csv

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils.dateparse import parse_date

from inventory.models import (
    Aimag,
    ControlAdjustment,
    Device,
    DeviceMovement,
    Location,
    MaintenanceService,
)
from .admin_site import inventory_admin_site


def reports_hub_view(request):
    filter_data = {
        "kind": request.GET.get("kind", ""),
        "aimag": request.GET.get("aimag", ""),
        "status": request.GET.get("status", ""),
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    }

    context = {
        **inventory_admin_site.each_context(request),
        "title": "Тайлан",
        "hub_url": request.path,
        "device_count": Device.objects.count(),
        "location_count": Location.objects.count(),
        "filter": filter_data,
        "KIND_CHOICES": getattr(Device, "KIND_CHOICES", []),
        "STATUS_CHOICES": getattr(Device, "STATUS_CHOICES", []),
        "AIMAG_CHOICES": list(
            Aimag.objects.all().order_by("name").values_list("id", "name")
        ),
        "EXPORT_LINKS": [
            {"label": "Devices CSV", "url": "/admin/reports/export/devices.csv"},
            {"label": "Locations CSV", "url": "/admin/reports/export/locations.csv"},
        ],
    }
    return TemplateResponse(request, "admin/reports_hub.html", context)


def reports_table_json(request):
    report = request.GET.get("report", "movements")
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    location_type = (request.GET.get("location_type") or "").strip()
    q = (request.GET.get("q") or "").strip()

    rows = []

    if report == "movements":
        qs = DeviceMovement.objects.select_related(
            "device", "source_location", "destination_location"
        ).order_by("-movement_date")

        if date_from:
            qs = qs.filter(movement_date__date__gte=date_from)
        if date_to:
            qs = qs.filter(movement_date__date__lte=date_to)
        if location_type:
            qs = qs.filter(destination_location__location_type=location_type)
        if q:
            qs = qs.filter(
                Q(device__name__icontains=q)
                | Q(device__serial_number__icontains=q)
                | Q(reason__icontains=q)
            )

        for obj in qs[:300]:
            rows.append(
                {
                    "c1": obj.movement_date.strftime("%Y-%m-%d")
                    if getattr(obj, "movement_date", None)
                    else "",
                    "c2": str(getattr(obj, "device", "") or ""),
                    "c3": str(getattr(obj, "source_location", "") or ""),
                    "c4": str(getattr(obj, "destination_location", "") or ""),
                    "c5": getattr(obj, "reason", "") or "",
                    "c6": str(getattr(obj, "approved_by", "") or ""),
                }
            )

    elif report == "maintenance":
        qs = MaintenanceService.objects.select_related("device").order_by("-service_date")

        if date_from:
            qs = qs.filter(service_date__gte=date_from)
        if date_to:
            qs = qs.filter(service_date__lte=date_to)
        if location_type:
            qs = qs.filter(device__location__location_type=location_type)
        if q:
            qs = qs.filter(
                Q(device__name__icontains=q)
                | Q(device__serial_number__icontains=q)
                | Q(description__icontains=q)
            )

        for obj in qs[:300]:
            rows.append(
                {
                    "c1": str(getattr(obj, "service_date", "") or ""),
                    "c2": str(getattr(obj, "device", "") or ""),
                    "c3": str(getattr(obj, "workflow_status", "") or ""),
                    "c4": str(getattr(obj, "performed_by", "") or ""),
                    "c5": str(getattr(obj, "description", "") or ""),
                    "c6": "",
                }
            )

    elif report == "control":
        qs = ControlAdjustment.objects.select_related("device").order_by("-control_date")

        if date_from:
            qs = qs.filter(control_date__gte=date_from)
        if date_to:
            qs = qs.filter(control_date__lte=date_to)
        if location_type:
            qs = qs.filter(device__location__location_type=location_type)
        if q:
            qs = qs.filter(
                Q(device__name__icontains=q)
                | Q(device__serial_number__icontains=q)
                | Q(result__icontains=q)
            )

        for obj in qs[:300]:
            rows.append(
                {
                    "c1": str(getattr(obj, "control_date", "") or ""),
                    "c2": str(getattr(obj, "device", "") or ""),
                    "c3": str(getattr(obj, "workflow_status", "") or ""),
                    "c4": str(getattr(obj, "result", "") or ""),
                    "c5": str(getattr(obj, "performed_by", "") or ""),
                    "c6": "",
                }
            )

    return JsonResponse(rows, safe=False)


def reports_export_devices_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="devices.csv"'
    writer = csv.writer(response)

    writer.writerow(
        ["ID", "Нэр", "Серийн дугаар", "Төрөл", "Төлөв", "Байршил", "Дараагийн калибровка"]
    )

    for d in Device.objects.select_related("location").all().order_by("id"):
        writer.writerow(
            [
                d.id,
                getattr(d, "name", ""),
                getattr(d, "serial_number", ""),
                getattr(d, "kind", ""),
                getattr(d, "status", ""),
                str(getattr(d, "location", "")),
                getattr(d, "next_verification_date", ""),
            ]
        )

    return response


def reports_export_locations_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="locations.csv"'
    writer = csv.writer(response)

    writer.writerow(["ID", "Нэр", "Код", "Төрөл", "Аймаг", "Сум", "Өргөрөг", "Уртраг"])

    for loc in Location.objects.all().order_by("id"):
        writer.writerow(
            [
                loc.id,
                getattr(loc, "name", ""),
                getattr(loc, "code", ""),
                getattr(loc, "location_type", ""),
                str(getattr(loc, "aimag", "")),
                str(getattr(loc, "sum", "")),
                getattr(loc, "latitude", ""),
                getattr(loc, "longitude", ""),
            ]
        )

    return response