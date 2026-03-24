from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils import timezone

from inventory.models import Aimag, Device, Location

logger = logging.getLogger(__name__)

DB_SAFE_EXCEPTIONS = (OperationalError, DatabaseError, ProgrammingError)


# =========================================================
# BASIC SAFE HELPERS
# =========================================================
def reports_hub_view(request):
    return HttpResponse("Reports Hub (coming soon)")

def get_today():
    return timezone.now().date()


def safe_count(qs) -> int:
    try:
        return qs.count()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_count fallback due to DB issue: %s", exc)
        return 0
    except Exception as exc:
        logger.exception("Unexpected safe_count error: %s", exc)
        return 0


def _safe_each_context(request: HttpRequest) -> dict[str, Any]:
    try:
        from inventory.admin import inventory_admin_site

        return inventory_admin_site.each_context(request)
    except Exception as exc:
        logger.warning("Could not load inventory_admin_site.each_context: %s", exc)
        return {
            "site_header": "БҮРТГЭЛ систем",
            "site_title": "БҮРТГЭЛ систем",
            "title": "Dashboard",
        }


def _safe_device_queryset() -> QuerySet:
    try:
        return Device.objects.all()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("Device queryset failed: %s", exc)
        return Device.objects.none()
    except Exception as exc:
        logger.exception("Unexpected device queryset error: %s", exc)
        return Device.objects.none()


def _safe_location_queryset() -> QuerySet:
    try:
        return Location.objects.all()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("Location queryset failed: %s", exc)
        return Location.objects.none()
    except Exception as exc:
        logger.exception("Unexpected location queryset error: %s", exc)
        return Location.objects.none()


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


# =========================================================
# FILTERS
# =========================================================
def apply_device_filters(qs: QuerySet, request: HttpRequest) -> QuerySet:
    aimag = (request.GET.get("aimag") or "").strip()
    kind = (request.GET.get("kind") or "").strip()
    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    try:
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

            if cond:
                qs = qs.filter(cond)

        return qs
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("apply_device_filters fallback due to DB issue: %s", exc)
        return Device.objects.none()
    except Exception as exc:
        logger.exception("Unexpected apply_device_filters error: %s", exc)
        return Device.objects.none()


def apply_location_filters(qs: QuerySet, request: HttpRequest) -> QuerySet:
    aimag = (request.GET.get("aimag") or "").strip()
    location_type = (request.GET.get("location_type") or "").strip()
    q = (request.GET.get("q") or "").strip()

    try:
        if aimag:
            if has_field(Location, "aimag"):
                qs = qs.filter(aimag_id=aimag)
            elif has_field(Location, "aimag_ref"):
                qs = qs.filter(aimag_ref_id=aimag)

        if location_type and has_field(Location, "location_type"):
            qs = qs.filter(location_type=location_type)

        if q:
            cond = Q()
            if has_field(Location, "name"):
                cond |= Q(name__icontains=q)
            if has_field(Location, "code"):
                cond |= Q(code__icontains=q)

            if cond:
                qs = qs.filter(cond)

        return qs
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("apply_location_filters fallback due to DB issue: %s", exc)
        return Location.objects.none()
    except Exception as exc:
        logger.exception("Unexpected apply_location_filters error: %s", exc)
        return Location.objects.none()


# =========================================================
# AGGREGATIONS / SUMMARY HELPERS
# =========================================================
def safe_group_count(qs: QuerySet, field_name: str) -> list[dict[str, Any]]:
    if not field_name:
        return []

    try:
        return list(qs.values(field_name).annotate(total=Count("id")).order_by(field_name))
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_group_count fallback for %s: %s", field_name, exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected safe_group_count error for %s: %s", field_name, exc)
        return []


def get_recent_devices(device_qs: QuerySet, limit: int = 12) -> list[dict[str, Any]]:
    try:
        qs = device_qs
        if has_field(Device, "created_at"):
            qs = qs.order_by("-created_at")
        else:
            qs = qs.order_by("-id")

        if has_field(Device, "location"):
            qs = qs.select_related("location")

        rows = []
        for obj in qs[:limit]:
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
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_recent_devices fallback due to DB issue: %s", exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected get_recent_devices error: %s", exc)
        return []


def get_recent_locations(location_qs: QuerySet, limit: int = 12) -> list[Any]:
    try:
        return list(location_qs.order_by("-id")[:limit])
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_recent_locations fallback due to DB issue: %s", exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected get_recent_locations error: %s", exc)
        return []


def get_status_summary(device_qs: QuerySet) -> dict[str, int]:
    out = {
        "active": 0,
        "broken": 0,
        "repair": 0,
        "spare": 0,
        "retired": 0,
        "other": 0,
    }

    try:
        if not has_field(Device, "status"):
            return out

        for obj in device_qs.only("status"):
            status = (getattr(obj, "status", "") or "").lower()
            if status in out:
                out[status] += 1
            else:
                out["other"] += 1
        return out
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_status_summary fallback: %s", exc)
        return out
    except Exception as exc:
        logger.exception("Unexpected get_status_summary error: %s", exc)
        return out


def get_kind_summary(device_qs: QuerySet) -> dict[str, int]:
    out: dict[str, int] = {}

    try:
        if not has_field(Device, "kind"):
            return out

        for obj in device_qs.only("kind"):
            kind = (getattr(obj, "kind", None) or "OTHER")
            out[kind] = out.get(kind, 0) + 1
        return out
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_kind_summary fallback: %s", exc)
        return out
    except Exception as exc:
        logger.exception("Unexpected get_kind_summary error: %s", exc)
        return out


def get_dashboard_alerts(device_qs: QuerySet, location_qs: QuerySet) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    try:
        devices_no_serial = 0
        if has_field(Device, "serial_number"):
            devices_no_serial = safe_count(device_qs.filter(serial_number__isnull=True)) + safe_count(
                device_qs.filter(serial_number="")
            )
        if devices_no_serial:
            alerts.append(
                {
                    "level": "warning",
                    "title": "Серийн дугааргүй багаж",
                    "count": devices_no_serial,
                }
            )
    except Exception as exc:
        logger.warning("Alert devices_no_serial failed: %s", exc)

    try:
        devices_no_location = 0
        if has_field(Device, "location"):
            devices_no_location = safe_count(device_qs.filter(location__isnull=True))
        if devices_no_location:
            alerts.append(
                {
                    "level": "warning",
                    "title": "Байршилгүй багаж",
                    "count": devices_no_location,
                }
            )
    except Exception as exc:
        logger.warning("Alert devices_no_location failed: %s", exc)

    try:
        locations_without_devices = 0
        if has_field(Location, "devices"):
            locations_without_devices = safe_count(location_qs.filter(devices__isnull=True).distinct())
        if locations_without_devices:
            alerts.append(
                {
                    "level": "info",
                    "title": "Багажгүй байршил",
                    "count": locations_without_devices,
                }
            )
    except Exception as exc:
        logger.warning("Alert locations_without_devices failed: %s", exc)

    return alerts


def get_due_counts(device_qs: QuerySet) -> dict[str, int]:
    result = {
        "expired": 0,
        "due_30": 0,
        "due_90": 0,
        "ok": 0,
        "empty": 0,
    }

    if not has_field(Device, "next_verification_date"):
        return result

    try:
        today = get_today()
        d30 = today + timedelta(days=30)
        d90 = today + timedelta(days=90)

        result["expired"] = safe_count(device_qs.filter(next_verification_date__lt=today))
        result["due_30"] = safe_count(
            device_qs.filter(
                next_verification_date__gte=today,
                next_verification_date__lte=d30,
            )
        )
        result["due_90"] = safe_count(
            device_qs.filter(
                next_verification_date__gt=d30,
                next_verification_date__lte=d90,
            )
        )
        result["ok"] = safe_count(device_qs.filter(next_verification_date__gt=d90))
        result["empty"] = safe_count(device_qs.filter(next_verification_date__isnull=True))
        return result
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_due_counts fallback due to DB issue: %s", exc)
        return result
    except Exception as exc:
        logger.exception("Unexpected get_due_counts error: %s", exc)
        return result


def get_due_table(device_qs: QuerySet, limit: int = 12) -> list[dict[str, Any]]:
    if not has_field(Device, "next_verification_date"):
        return []

    try:
        rows: list[dict[str, Any]] = []
        today = get_today()

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
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_due_table fallback due to DB issue: %s", exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected get_due_table error: %s", exc)
        return []


def get_workflow_pending_counts() -> dict[str, int]:
    counts = {
        "maintenance_pending": 0,
        "control_pending": 0,
        "movement_pending": 0,
        "total": 0,
    }

    try:
        MaintenanceService = get_workflow_model("MaintenanceService")
        ControlAdjustment = get_workflow_model("ControlAdjustment")
        DeviceMovement = get_workflow_model("DeviceMovement")

        pending_values = ["PENDING", "pending", "draft", "DRAFT"]

        if MaintenanceService and has_field(MaintenanceService, "workflow_status"):
            counts["maintenance_pending"] = MaintenanceService.objects.filter(
                workflow_status__in=pending_values
            ).count()

        if ControlAdjustment and has_field(ControlAdjustment, "workflow_status"):
            counts["control_pending"] = ControlAdjustment.objects.filter(
                workflow_status__in=pending_values
            ).count()

        if DeviceMovement and has_field(DeviceMovement, "workflow_status"):
            counts["movement_pending"] = DeviceMovement.objects.filter(
                workflow_status__in=pending_values
            ).count()

        counts["total"] = (
            counts["maintenance_pending"]
            + counts["control_pending"]
            + counts["movement_pending"]
        )
        return counts
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_workflow_pending_counts fallback due to DB issue: %s", exc)
        return counts
    except Exception as exc:
        logger.exception("Unexpected get_workflow_pending_counts error: %s", exc)
        return counts


def get_locations_by_aimag(location_qs: QuerySet, limit: int = 15) -> list[dict[str, Any]]:
    try:
        if has_field(Location, "aimag"):
            rows = (
                location_qs.values("aimag__name")
                .annotate(total=Count("id"))
                .order_by("-total", "aimag__name")[:limit]
            )
            return [{"name": r["aimag__name"] or "—", "total": r["total"]} for r in rows]

        if has_field(Location, "aimag_ref"):
            rows = (
                location_qs.values("aimag_ref__name")
                .annotate(total=Count("id"))
                .order_by("-total", "aimag_ref__name")[:limit]
            )
            return [{"name": r["aimag_ref__name"] or "—", "total": r["total"]} for r in rows]

        return []
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_locations_by_aimag fallback due to DB issue: %s", exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected get_locations_by_aimag error: %s", exc)
        return []


def get_aimag_choices() -> list[tuple[Any, Any]]:
    try:
        return list(Aimag.objects.all().order_by("name").values_list("id", "name"))
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("get_aimag_choices fallback due to DB issue: %s", exc)
        return []
    except Exception as exc:
        logger.exception("Unexpected get_aimag_choices error: %s", exc)
        return []


# =========================================================
# TEMPLATE VIEWS
# =========================================================
@staff_member_required
def dashboard_home_view(request: HttpRequest) -> HttpResponse:
    device_qs = apply_device_filters(_safe_device_queryset(), request)
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    context = {
        **_safe_each_context(request),
        "title": "Dashboard",
        "device_count": safe_count(device_qs),
        "location_count": safe_count(location_qs),
        "total_devices": safe_count(device_qs),
        "total_locations": safe_count(location_qs),
        "devices_by_status": safe_group_count(device_qs, "status") if has_field(Device, "status") else [],
        "devices_by_kind": safe_group_count(device_qs, "kind") if has_field(Device, "kind") else [],
        "locations_by_type": (
            safe_group_count(location_qs, "location_type")
            if has_field(Location, "location_type")
            else []
        ),
        "status_summary": get_status_summary(device_qs),
        "kind_summary": get_kind_summary(device_qs),
        "due_counts": due,
        "workflow_counts": workflow,
        "recent_devices": get_recent_devices(device_qs, 12),
        "recent_locations": get_recent_locations(location_qs, 12),
        "locations_by_aimag": get_locations_by_aimag(location_qs, 15),
        "due_table": get_due_table(device_qs, 12),
        "dashboard_alerts": get_dashboard_alerts(device_qs, location_qs),
        "aimag_choices": get_aimag_choices(),
        "filter": {
            "aimag": request.GET.get("aimag", ""),
            "kind": request.GET.get("kind", ""),
            "status": request.GET.get("status", ""),
            "location_type": request.GET.get("location_type", ""),
            "q": request.GET.get("q", ""),
        },
        "kind_choices": getattr(Device, "KIND_CHOICES", []),
        "status_choices": getattr(Device, "STATUS_CHOICES", []),
        "schema_warning": (
            "Schema зөрүү байж магадгүй. makemigrations + migrate шалгана уу."
        ),
    }
    return TemplateResponse(request, "admin/dashboard_home.html", context)


@staff_member_required
def dashboard_legacy_view(request: HttpRequest) -> HttpResponse:
    device_qs = apply_device_filters(_safe_device_queryset(), request)
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    context = {
        **_safe_each_context(request),
        "title": "Хуучин Dashboard",
        "device_count": safe_count(device_qs),
        "location_count": safe_count(location_qs),
        "devices_by_status": safe_group_count(device_qs, "status") if has_field(Device, "status") else [],
        "devices_by_kind": safe_group_count(device_qs, "kind") if has_field(Device, "kind") else [],
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
        "aimag_choices": get_aimag_choices(),
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


@staff_member_required
def dashboard_general_view(request: HttpRequest) -> HttpResponse:
    device_qs = apply_device_filters(_safe_device_queryset(), request)
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    context = {
        **_safe_each_context(request),
        "title": "Ерөнхий мэдээлэл",
        "total_devices": safe_count(device_qs),
        "total_locations": safe_count(location_qs),
        "devices_by_kind": safe_group_count(device_qs, "kind") if has_field(Device, "kind") else [],
        "locations_by_type": (
            safe_group_count(location_qs, "location_type")
            if has_field(Location, "location_type")
            else []
        ),
        "recent_devices": get_recent_devices(device_qs, 10),
        "status_summary": get_status_summary(device_qs),
        "kind_summary": get_kind_summary(device_qs),
        "dashboard_alerts": get_dashboard_alerts(device_qs, location_qs),
    }
    return TemplateResponse(request, "admin/dashboard_general.html", context)


@staff_member_required
def dashboard_table_view(request: HttpRequest) -> HttpResponse:
    try:
        devices = (
            apply_device_filters(_safe_device_queryset().select_related("location"), request)
            .order_by("-id")[:200]
        )
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("dashboard_table_view fallback: %s", exc)
        devices = []
    except Exception as exc:
        logger.exception("Unexpected dashboard_table_view error: %s", exc)
        devices = []

    context = {
        **_safe_each_context(request),
        "title": "Хүснэгтэн тайлан",
        "devices": devices,
    }
    return TemplateResponse(request, "admin/dashboard_table.html", context)


@staff_member_required
def dashboard_graph_view(request: HttpRequest) -> HttpResponse:
    device_qs = apply_device_filters(_safe_device_queryset(), request)
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    context = {
        **_safe_each_context(request),
        "title": "График тайлан",
        "total_devices": safe_count(device_qs),
        "total_locations": safe_count(location_qs),
        "status_summary": get_status_summary(device_qs),
        "kind_summary": get_kind_summary(device_qs),
        "devices_by_status": safe_group_count(device_qs, "status") if has_field(Device, "status") else [],
        "devices_by_kind": safe_group_count(device_qs, "kind") if has_field(Device, "kind") else [],
        "locations_by_type": (
            safe_group_count(location_qs, "location_type")
            if has_field(Location, "location_type")
            else []
        ),
    }
    return TemplateResponse(request, "admin/dashboard_graph.html", context)


@staff_member_required
def workflow_pending_dashboard(request: HttpRequest) -> HttpResponse:
    context = {
        **_safe_each_context(request),
        "title": "Pending Workflow",
        "workflow_counts": get_workflow_pending_counts(),
    }
    return TemplateResponse(request, "admin/workflow_pending_dashboard.html", context)


# =========================================================
# JSON VIEWS
# =========================================================
@staff_member_required
def workflow_pending_counts_json(request: HttpRequest) -> JsonResponse:
    return JsonResponse(get_workflow_pending_counts())


@staff_member_required
def dashboard_summary_json(request: HttpRequest) -> JsonResponse:
    device_qs = apply_device_filters(_safe_device_queryset(), request)
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    due = get_due_counts(device_qs)
    workflow = get_workflow_pending_counts()

    status_rows = safe_group_count(device_qs, "status") if has_field(Device, "status") else []
    kind_rows = safe_group_count(device_qs, "kind") if has_field(Device, "kind") else []
    location_rows = (
        safe_group_count(location_qs, "location_type")
        if has_field(Location, "location_type")
        else []
    )
    aimag_rows = get_locations_by_aimag(location_qs, 20)

    payload = {
        "kpis": {
            "device_count": safe_count(device_qs),
            "location_count": safe_count(location_qs),
            "expired_count": due["expired"],
            "workflow_pending": workflow["total"],
        },
        "due_counts": due,
        "workflow_counts": workflow,
        "charts": {
            "status": [{"name": r.get("status") or "—", "value": r["total"]} for r in status_rows],
            "kind": [{"name": r.get("kind") or "—", "value": r["total"]} for r in kind_rows],
            "location_type": [
                {"name": r.get("location_type") or "—", "value": r["total"]}
                for r in location_rows
            ],
            "aimag": [{"name": r["name"], "value": r["total"]} for r in aimag_rows],
        },
        "recent_devices": get_recent_devices(device_qs, 12),
        "due_table": get_due_table(device_qs, 12),
    }
    return JsonResponse(payload)


@staff_member_required
def dashboard_map_json(request: HttpRequest) -> JsonResponse:
    location_qs = apply_location_filters(_safe_location_queryset(), request)

    if not has_field(Location, "latitude") or not has_field(Location, "longitude"):
        return JsonResponse({"points": []})

    try:
        qs = location_qs.exclude(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        ).order_by("id")

        points = []
        for loc in qs[:1200]:
            try:
                lat = float(loc.latitude)
                lng = float(loc.longitude)
            except (TypeError, ValueError):
                continue

            points.append(
                {
                    "id": loc.id,
                    "name": getattr(loc, "name", "") or f"Location #{loc.id}",
                    "lat": lat,
                    "lng": lng,
                    "location_type": getattr(loc, "location_type", "") or "",
                    "aimag": str(getattr(loc, "aimag", "") or getattr(loc, "aimag_ref", "") or ""),
                    "sum": str(getattr(loc, "sum", "") or getattr(loc, "sum_ref", "") or ""),
                    "elevation_m": getattr(loc, "elevation_m", None),
                    "code": getattr(loc, "code", "") or "",
                }
            )

        return JsonResponse({"points": points})
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("dashboard_map_json fallback due to DB issue: %s", exc)
        return JsonResponse({"points": []})
    except Exception as exc:
        logger.exception("Unexpected dashboard_map_json error: %s", exc)
        return JsonResponse({"points": []})