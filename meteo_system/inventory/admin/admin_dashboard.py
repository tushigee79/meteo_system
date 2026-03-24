from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.db.models import Count, Q
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.utils import timezone

from inventory.models import Aimag, Device, Location
from .admin_site import inventory_admin_site


def has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def get_workflow_model(model_name: str):
    try:
        return apps.get_model("inventory", model_name)
    except Exception:
        return None


def apply_device_filters(qs, request):
    aimag = (request.GET.get("aimag") or "").strip()
    kind = (request.GET.get("kind") or "").strip()
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    if aimag:
        if has_field(Device, "aimag"):
            qs = qs.filter(aimag_id=aimag)
        elif has_field(Device, "location") and has_field(Location, "aimag"):
            qs = qs.filter(location__aimag_id=aimag)

    if kind and has_field(Device, "kind"):
        qs = qs.filter(kind=kind)

    if status and has_field(Device, "status"):
        qs = qs.filter(status=status)

    if q:
        cond = Q()
        if has_field(Device, "name"):
            cond |= Q(name__icontains=q)
        if has_field(Device, "serial_number"):
            cond |= Q(serial_number__icontains=q)
        if has_field(Device, "inventory_code"):
            cond |= Q(inventory_code__icontains=q)
        qs = qs.filter(cond)

    return qs


def apply_location_filters(qs, request):
    aimag = (request.GET.get("aimag") or "").strip()
    location_type = (request.GET.get("location_type") or "").strip()
    q = (request.GET.get("q") or "").strip()

    if aimag and has_field(Location, "aimag"):
        qs = qs.filter(aimag_id=aimag)

    if location_type and has_field(Location, "location_type"):
        qs = qs.filter(location_type=location_type)

    if q:
        cond = Q()
        if has_field(Location, "name"):
            cond |= Q(name__icontains=q)
        if has_field(Location, "code"):
            cond |= Q(code__icontains=q)
        qs = qs.filter(cond)

    return qs


def safe_group_count(qs, field_name: str):
    if not field_name:
        return []
    return list(qs.values(field_name).annotate(total=Count("id")).order_by(field_name))


def get_due_counts(device_qs):
    result = {
        "expired": 0,
        "due_30": 0,
        "due_90": 0,
        "ok": 0,
        "empty": 0,
    }

    if not has_field(Device, "next_verification_date"):
        return result

    today = timezone.now().date()
    d30 = today + timedelta(days=30)
    d90 = today + timedelta(days=90)

    result["expired"] = device_qs.filter(next_verification_date__lt=today).count()
    result["due_30"] = device_qs.filter(
        next_verification_date__gte=today,
        next_verification_date__lte=d30,
    ).count()
    result["due_90"] = device_qs.filter(
        next_verification_date__gt=d30,
        next_verification_date__lte=d90,
    ).count()
    result["ok"] = device_qs.filter(next_verification_date__gt=d90).count()
    result["empty"] = device_qs.filter(next_verification_date__isnull=True).count()

    return result


def get_due_table(device_qs, limit: int = 12):
    if not has_field(Device, "next_verification_date"):
        return []

    rows = []
    today = timezone.now().date()

    qs = (
        device_qs.select_related("location")
        .filter(next_verification_date__isnull=False)
        .order_by("next_verification_date")[:limit]
    )

    for obj in qs:
        due_date = getattr(obj, "next_verification_date", None)
        delta = (due_date - today).days if due_date else None

        if delta is None:
            bucket = "empty"
        elif delta < 0:
            bucket = "expired"
        elif delta <= 30:
            bucket = "30"
        elif delta <= 90:
            bucket = "90"
        else:
            bucket = "ok"

        rows.append(
            {
                "id": obj.id,
                "name": getattr(obj, "name", "") or str(obj),
                "serial_number": getattr(obj, "serial_number", "") or "",
                "location": str(getattr(obj, "location", "") or ""),
                "next_verification_date": due_date,
                "days_left": delta,
                "bucket": bucket,
            }
        )
    return rows


def get_workflow_pending_counts():
    counts = {
        "maintenance_pending": 0,
        "control_pending": 0,
        "movement_pending": 0,
        "total": 0,
    }

    MaintenanceService = get_workflow_model("MaintenanceService")
    ControlAdjustment = get_workflow_model("ControlAdjustment")
    DeviceMovement = get_workflow_model("DeviceMovement")

    if MaintenanceService and has_field(MaintenanceService, "workflow_status"):
        counts["maintenance_pending"] = MaintenanceService.objects.filter(
            workflow_status__in=["PENDING", "pending", "draft", "DRAFT"]
        ).count()

    if ControlAdjustment and has_field(ControlAdjustment, "workflow_status"):
        counts["control_pending"] = ControlAdjustment.objects.filter(
            workflow_status__in=["PENDING", "pending", "draft", "DRAFT"]
        ).count()

    if DeviceMovement and has_field(DeviceMovement, "workflow_status"):
        counts["movement_pending"] = DeviceMovement.objects.filter(
            workflow_status__in=["PENDING", "pending", "draft", "DRAFT"]
        ).count()

    counts["total"] = (
        counts["maintenance_pending"]
        + counts["control_pending"]
        + counts["movement_pending"]
    )
    return counts


def get_recent_devices(device_qs, limit: int = 12):
    qs = device_qs
    if has_field(Device, "created_at"):
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-id")

    rows = []
    for obj in qs.select_related("location")[:limit]:
        rows.append(
            {
                "id": obj.id,
                "name": getattr(obj, "name", "") or str(obj),
                "serial_number": getattr(obj, "serial_number", "") or "",
                "kind": getattr(obj, "kind", "") or "",
                "status": getattr(obj, "status", "") or "",
                "location": str(getattr(obj, "location", "") or ""),
            }
        )
    return rows


def get_locations_by_aimag(location_qs, limit: int = 15):
    if not has_field(Location, "aimag"):
        return []

    rows = (
        location_qs.values("aimag__name")
        .annotate(total=Count("id"))
        .order_by("-total", "aimag__name")[:limit]
    )
    return [{"name": r["aimag__name"] or "—", "total": r["total"]} for r in rows]


def dashboard_home_view(request):
    device_qs = apply_device_filters(Device.objects.all(), request)
    location_qs = apply_location_filters(Location.objects.all(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    devices_by_status = (
        safe_group_count(device_qs, "status") if has_field(Device, "status") else []
    )
    devices_by_kind = (
        safe_group_count(device_qs, "kind") if has_field(Device, "kind") else []
    )
    locations_by_type = (
        safe_group_count(location_qs, "location_type")
        if has_field(Location, "location_type")
        else []
    )

    context = {
        **inventory_admin_site.each_context(request),
        "title": "Dashboard v3",
        "device_count": device_qs.count(),
        "location_count": location_qs.count(),
        "devices_by_status": devices_by_status,
        "devices_by_kind": devices_by_kind,
        "locations_by_type": locations_by_type,
        "due_counts": due,
        "workflow_counts": workflow,
        "recent_devices": get_recent_devices(device_qs, 12),
        "locations_by_aimag": get_locations_by_aimag(location_qs, 15),
        "due_table": get_due_table(device_qs, 12),
        "aimag_choices": list(
            Aimag.objects.all().order_by("name").values_list("id", "name")
        ),
        "filter": {
            "aimag": request.GET.get("aimag", ""),
            "kind": request.GET.get("kind", ""),
            "status": request.GET.get("status", ""),
            "location_type": request.GET.get("location_type", ""),
            "q": request.GET.get("q", ""),
        },
        "kind_choices": getattr(Device, "KIND_CHOICES", []),
        "status_choices": getattr(Device, "STATUS_CHOICES", []),
    }
    return TemplateResponse(request, "admin/dashboard_home.html", context)


def dashboard_legacy_view(request):
    device_qs = apply_device_filters(Device.objects.all(), request)
    location_qs = apply_location_filters(Location.objects.all(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    context = {
        **inventory_admin_site.each_context(request),
        "title": "Хуучин Dashboard",
        "device_count": device_qs.count(),
        "location_count": location_qs.count(),
        "devices_by_status": (
            safe_group_count(device_qs, "status") if has_field(Device, "status") else []
        ),
        "devices_by_kind": (
            safe_group_count(device_qs, "kind") if has_field(Device, "kind") else []
        ),
        "locations_by_type": (
            safe_group_count(location_qs, "location_type")
            if has_field(Location, "location_type")
            else []
        ),
        "due_counts": due,
        "workflow_counts": workflow,
        "recent_devices": get_recent_devices(device_qs, 12),
        "locations_by_aimag": get_locations_by_aimag(location_qs, 15),
        "due_table": get_due_table(device_qs, 12),
        "aimag_choices": list(
            Aimag.objects.all().order_by("name").values_list("id", "name")
        ),
        "filter": {
            "aimag": request.GET.get("aimag", ""),
            "kind": request.GET.get("kind", ""),
            "status": request.GET.get("status", ""),
            "location_type": request.GET.get("location_type", ""),
            "q": request.GET.get("q", ""),
        },
        "kind_choices": getattr(Device, "KIND_CHOICES", []),
        "status_choices": getattr(Device, "STATUS_CHOICES", []),
    }
    return TemplateResponse(request, "admin/dashboard_unified.html", context)


def dashboard_table_view(request):
    devices = (
        apply_device_filters(Device.objects.select_related("location").all(), request)
        .order_by("-id")[:200]
    )
    context = {
        **inventory_admin_site.each_context(request),
        "title": "Dashboard хүснэгт",
        "devices": devices,
    }
    return TemplateResponse(request, "admin/dashboard_table.html", context)


def dashboard_general_view(request):
    device_qs = apply_device_filters(Device.objects.all(), request)
    location_qs = apply_location_filters(Location.objects.all(), request)

    context = {
        **inventory_admin_site.each_context(request),
        "title": "Ерөнхий dashboard",
        "devices_by_kind": (
            safe_group_count(device_qs, "kind") if has_field(Device, "kind") else []
        ),
        "locations_by_type": (
            safe_group_count(location_qs, "location_type")
            if has_field(Location, "location_type")
            else []
        ),
    }
    return TemplateResponse(request, "admin/dashboard_general.html", context)


def workflow_pending_dashboard(request):
    context = {
        **inventory_admin_site.each_context(request),
        "title": "Pending Workflow",
        "workflow_counts": get_workflow_pending_counts(),
    }
    return TemplateResponse(request, "admin/workflow_pending_dashboard.html", context)


def workflow_pending_counts_json(request):
    return JsonResponse(get_workflow_pending_counts())


def dashboard_summary_json(request):
    device_qs = apply_device_filters(Device.objects.all(), request)
    location_qs = apply_location_filters(Location.objects.all(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    status_rows = (
        safe_group_count(device_qs, "status") if has_field(Device, "status") else []
    )
    kind_rows = (
        safe_group_count(device_qs, "kind") if has_field(Device, "kind") else []
    )
    location_rows = (
        safe_group_count(location_qs, "location_type")
        if has_field(Location, "location_type")
        else []
    )
    aimag_rows = get_locations_by_aimag(location_qs, 20)

    payload = {
        "kpis": {
            "device_count": device_qs.count(),
            "location_count": location_qs.count(),
            "expired_count": due["expired"],
            "workflow_pending": workflow["total"],
        },
        "due_counts": due,
        "workflow_counts": workflow,
        "charts": {
            "status": [
                {"name": r.get("status") or "—", "value": r["total"]}
                for r in status_rows
            ],
            "kind": [
                {"name": r.get("kind") or "—", "value": r["total"]}
                for r in kind_rows
            ],
            "location_type": [
                {"name": r.get("location_type") or "—", "value": r["total"]}
                for r in location_rows
            ],
            "aimag": [
                {"name": r["name"], "value": r["total"]}
                for r in aimag_rows
            ],
        },
        "recent_devices": get_recent_devices(device_qs, 12),
        "due_table": get_due_table(device_qs, 12),
    }
    return JsonResponse(payload)


def dashboard_map_json(request):
    location_qs = apply_location_filters(Location.objects.all(), request)

    if not has_field(Location, "latitude") or not has_field(Location, "longitude"):
        return JsonResponse({"points": []})

    qs = location_qs.exclude(
        Q(latitude__isnull=True) | Q(longitude__isnull=True)
    ).order_by("id")

    points = []
    for loc in qs[:1200]:
        points.append(
            {
                "id": loc.id,
                "name": getattr(loc, "name", "") or f"Location #{loc.id}",
                "lat": float(loc.latitude),
                "lng": float(loc.longitude),
                "location_type": getattr(loc, "location_type", "") or "",
                "aimag": str(getattr(loc, "aimag", "") or ""),
                "sum": str(getattr(loc, "sum", "") or ""),
                "elevation_m": getattr(loc, "elevation_m", None),
                "code": getattr(loc, "code", "") or "",
            }
        )

    return JsonResponse({"points": points})