from __future__ import annotations

import json
from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from .models import (
    Aimag,
    Device,
    Location,
    MaintenanceService,
    ControlAdjustment,
    WorkflowStatus,
)

CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_user_aimag(user):
    prof = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    return getattr(prof, "aimag", None)


def _scope_locations(user, qs):
    if user.is_superuser:
        return qs
    aimag = _get_user_aimag(user)
    if aimag:
        return qs.filter(aimag_ref=aimag)
    return qs.none()


def _scope_workflow_qs(user, qs):
    if user.is_superuser:
        return qs
    aimag = _get_user_aimag(user)
    if aimag:
        return qs.filter(device__location__aimag_ref=aimag)
    return qs.none()


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _axis_trunc(axis: str):
    axis = (axis or "day").lower()
    if axis == "week":
        return TruncWeek("date"), "%Y-W%W"
    if axis == "month":
        return TruncMonth("date"), "%Y-%m"
    return TruncDay("date"), "%Y-%m-%d"


def _cache_key(user, params: dict) -> str:
    aimag = _get_user_aimag(user)
    scope = f"su:{int(user.is_superuser)}|a:{getattr(aimag,'id',0)}"
    parts = [scope] + [f"{k}={params.get(k,'')}" for k in sorted(params.keys())]
    return "wf_graph:" + "|".join(parts)


def _build_workflow_stacked(user, *, axis: str, date_from: date | None, date_to: date | None,
                            filter_status: str, filter_kind: str, filter_location_type: str):
    """
    Pending/Approved/Rejected stacked series (MS+CA нийлбэр).
    Pending = SUBMITTED.
    """
    trunc, fmt = _axis_trunc(axis)

    ms = _scope_workflow_qs(user, MaintenanceService.objects.all())
    ca = _scope_workflow_qs(user, ControlAdjustment.objects.all())

    # device filters
    if filter_kind:
        ms = ms.filter(device__kind=filter_kind)
        ca = ca.filter(device__kind=filter_kind)
    if filter_location_type:
        ms = ms.filter(device__location__location_type=filter_location_type)
        ca = ca.filter(device__location__location_type=filter_location_type)

    # NOTE: filter_status affects other charts; stacked chart is inherently status-based.
    # If user set filter_status, we still compute stacked but can optionally highlight.
    if date_from:
        ms = ms.filter(date__gte=date_from)
        ca = ca.filter(date__gte=date_from)
    if date_to:
        ms = ms.filter(date__lte=date_to)
        ca = ca.filter(date__lte=date_to)

    def agg(qs, status_value: str):
        return (
            qs.filter(workflow_status=status_value)
              .annotate(t=trunc)
              .values("t")
              .annotate(c=Count("id"))
              .order_by("t")
        )

    pending = {}
    approved = {}
    rejected = {}

    for r in list(agg(ms, WorkflowStatus.SUBMITTED)) + list(agg(ca, WorkflowStatus.SUBMITTED)):
        k = r["t"].strftime(fmt)
        pending[k] = pending.get(k, 0) + r["c"]

    for r in list(agg(ms, WorkflowStatus.APPROVED)) + list(agg(ca, WorkflowStatus.APPROVED)):
        k = r["t"].strftime(fmt)
        approved[k] = approved.get(k, 0) + r["c"]

    for r in list(agg(ms, WorkflowStatus.REJECTED)) + list(agg(ca, WorkflowStatus.REJECTED)):
        k = r["t"].strftime(fmt)
        rejected[k] = rejected.get(k, 0) + r["c"]

    axis_keys = sorted(set(pending.keys()) | set(approved.keys()) | set(rejected.keys()))
    return {
        "axis": axis_keys,
        "pending": [pending.get(k, 0) for k in axis_keys],
        "approved": [approved.get(k, 0) for k in axis_keys],
        "rejected": [rejected.get(k, 0) for k in axis_keys],
        "filter_status": filter_status or "",
    }


def _build_breakdowns(user, *, date_from: date | None, date_to: date | None,
                      filter_status: str, filter_kind: str, filter_location_type: str):
    """
    - aimag breakdown: MS+CA counts grouped by aimag
    - device kind breakdown: MS+CA counts grouped by device.kind
    Applies current filters.
    """
    ms = _scope_workflow_qs(user, MaintenanceService.objects.select_related("device", "device__location", "device__location__aimag_ref"))
    ca = _scope_workflow_qs(user, ControlAdjustment.objects.select_related("device", "device__location", "device__location__aimag_ref"))

    if filter_status:
        ms = ms.filter(workflow_status=filter_status)
        ca = ca.filter(workflow_status=filter_status)

    if filter_kind:
        ms = ms.filter(device__kind=filter_kind)
        ca = ca.filter(device__kind=filter_kind)

    if filter_location_type:
        ms = ms.filter(device__location__location_type=filter_location_type)
        ca = ca.filter(device__location__location_type=filter_location_type)

    if date_from:
        ms = ms.filter(date__gte=date_from)
        ca = ca.filter(date__gte=date_from)
    if date_to:
        ms = ms.filter(date__lte=date_to)
        ca = ca.filter(date__lte=date_to)

    # Aimag breakdown
    aimag_counts = {}
    for r in ms.values("device__location__aimag_ref__name").annotate(c=Count("id")):
        k = r["device__location__aimag_ref__name"] or "-"
        aimag_counts[k] = aimag_counts.get(k, 0) + r["c"]
    for r in ca.values("device__location__aimag_ref__name").annotate(c=Count("id")):
        k = r["device__location__aimag_ref__name"] or "-"
        aimag_counts[k] = aimag_counts.get(k, 0) + r["c"]

    aimag_axis = sorted(aimag_counts.keys(), key=lambda x: (-aimag_counts[x], x))[:20]
    aimag_series = [{"name": k, "value": aimag_counts[k]} for k in aimag_axis]

    # Kind breakdown
    kind_counts = {}
    for r in ms.values("device__kind").annotate(c=Count("id")):
        k = r["device__kind"] or "OTHER"
        kind_counts[k] = kind_counts.get(k, 0) + r["c"]
    for r in ca.values("device__kind").annotate(c=Count("id")):
        k = r["device__kind"] or "OTHER"
        kind_counts[k] = kind_counts.get(k, 0) + r["c"]

    kind_axis = sorted(kind_counts.keys(), key=lambda x: (-kind_counts[x], x))
    kind_series = [{"name": k, "value": kind_counts[k]} for k in kind_axis]

    return aimag_series, kind_series


def _build_sla_trend(user, *, axis: str, date_from: date | None, date_to: date | None,
                     filter_kind: str, filter_location_type: str):
    """
    SLA trend: avg hours from submitted_at -> approved_at (approved records only), MS+CA.
    Grouped by axis using approved_at date.
    """
    trunc, fmt = _axis_trunc(axis)

    ms = _scope_workflow_qs(user, MaintenanceService.objects.all()).filter(workflow_status=WorkflowStatus.APPROVED)
    ca = _scope_workflow_qs(user, ControlAdjustment.objects.all()).filter(workflow_status=WorkflowStatus.APPROVED)

    if filter_kind:
        ms = ms.filter(device__kind=filter_kind)
        ca = ca.filter(device__kind=filter_kind)
    if filter_location_type:
        ms = ms.filter(device__location__location_type=filter_location_type)
        ca = ca.filter(device__location__location_type=filter_location_type)

    if date_from:
        ms = ms.filter(date__gte=date_from)
        ca = ca.filter(date__gte=date_from)
    if date_to:
        ms = ms.filter(date__lte=date_to)
        ca = ca.filter(date__lte=date_to)

    # Use approved_at for grouping; if missing, fallback to date
    def _qs(qs):
        dur = ExpressionWrapper(F("approved_at") - F("submitted_at"), output_field=DurationField())
        return (
            qs.exclude(approved_at__isnull=True).exclude(submitted_at__isnull=True)
              .annotate(t=trunc)
              .values("t")
              .annotate(avg_dur=Avg(dur))
              .order_by("t")
        )

    tmp = {}
    # merge ms and ca by weighted average (count-weighted)
    def add_rows(rows, base_qs):
        for r in rows:
            k = r["t"].strftime(fmt)
            # compute count for weighting
            cnt = base_qs.filter(approved_at__date=r["t"].date()).count() if hasattr(r["t"], "date") else 0
            # if count calc is too slow, use 1 as fallback
            if cnt <= 0:
                cnt = 1
            hours = 0.0
            if r["avg_dur"] is not None:
                hours = (r["avg_dur"].total_seconds() or 0.0) / 3600.0
            cur = tmp.get(k, {"sum": 0.0, "n": 0})
            cur["sum"] += hours * cnt
            cur["n"] += cnt
            tmp[k] = cur

    add_rows(_qs(ms), ms)
    add_rows(_qs(ca), ca)

    axis_keys = sorted(tmp.keys())
    vals = []
    for k in axis_keys:
        n = tmp[k]["n"] or 1
        vals.append(round(tmp[k]["sum"] / n, 2))

    return {"axis": axis_keys, "sla_hours": vals}


def _build_locations_points(user, *, filter_kind: str, filter_location_type: str):
    """
    Map points:
      - type = location.location_type
      - status bucket: BROKEN/EMPTY/OK based on devices in location
      - pending_total: workflow SUBMITTED count for devices at this location (MS+CA)
    """
    locs = _scope_locations(user, Location.objects.select_related("aimag_ref", "owner_org"))
    if filter_location_type:
        locs = locs.filter(location_type=filter_location_type)

    # Prefetch devices counts
    locs = locs.annotate(
        device_total=Count("devices", distinct=True),
        broken_total=Count("devices", filter=Q(devices__status__in=["Broken", "Repair"]), distinct=True),
    )

    # pending workflow counts by location
    # Note: this can be heavy; keep it simple with two aggregated queries and merge in python.
    pending_ms = dict(
        MaintenanceService.objects.filter(workflow_status=WorkflowStatus.SUBMITTED)
        .values_list("device__location_id")
        .annotate(c=Count("id"))
    )
    pending_ca = dict(
        ControlAdjustment.objects.filter(workflow_status=WorkflowStatus.SUBMITTED)
        .values_list("device__location_id")
        .annotate(c=Count("id"))
    )

    points = []
    for l in locs:
        if l.latitude is None or l.longitude is None:
            continue
        device_total = int(getattr(l, "device_total", 0) or 0)
        broken_total = int(getattr(l, "broken_total", 0) or 0)

        if device_total <= 0:
            st = "EMPTY"
        elif broken_total > 0:
            st = "BROKEN"
        else:
            st = "OK"

        pid = int(l.id)
        pending_total = int(pending_ms.get(pid, 0) or 0) + int(pending_ca.get(pid, 0) or 0)

        points.append({
            "id": pid,
            "name": l.name,
            "lat": float(l.latitude),
            "lon": float(l.longitude),
            "type": l.location_type or "OTHER",
            "status": st,
            "pending_total": pending_total,
            "aimag": getattr(l.aimag_ref, "name", "") if getattr(l, "aimag_ref", None) else "",
        })

    return points


@staff_member_required
def dashboard_graph(request: HttpRequest) -> HttpResponse:
    """
    Enterprise Dashboard Graph endpoint.
    Supports:
      - axis: day|week|month
      - filters: date_from/date_to/status/kind/location_type
      - ajax=1: returns JSON payload for charts+map
    """
    user = request.user

    axis = (request.GET.get("axis") or "day").lower()
    filter_status = (request.GET.get("status") or "").strip()
    filter_kind = (request.GET.get("kind") or "").strip()
    filter_location_type = (request.GET.get("location_type") or "").strip()
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))

    params = {
        "axis": axis,
        "status": filter_status,
        "kind": filter_kind,
        "location_type": filter_location_type,
        "date_from": date_from.isoformat() if date_from else "",
        "date_to": date_to.isoformat() if date_to else "",
    }

    key = _cache_key(user, params)
    payload = cache.get(key)

    if payload is None:
        # Stacked workflow series
        wf_stacked = _build_workflow_stacked(
            user,
            axis=axis, date_from=date_from, date_to=date_to,
            filter_status=filter_status, filter_kind=filter_kind, filter_location_type=filter_location_type,
        )

        # Aimags + kinds breakdown
        aimag_series, kind_series = _build_breakdowns(
            user,
            date_from=date_from, date_to=date_to,
            filter_status=filter_status,
            filter_kind=filter_kind, filter_location_type=filter_location_type,
        )

        # SLA trend
        sla = _build_sla_trend(
            user, axis=axis, date_from=date_from, date_to=date_to,
            filter_kind=filter_kind, filter_location_type=filter_location_type,
        )

        # Map points
        points = _build_locations_points(
            user, filter_kind=filter_kind, filter_location_type=filter_location_type
        )

        payload = {
            "echarts_workflow_stacked": wf_stacked,
            "echarts_aimag": aimag_series,
            "echarts_kind": kind_series,
            "echarts_sla": sla,
            "locations": points,
        }
        cache.set(key, payload, CACHE_TTL_SECONDS)

    # Ajax response
    if (request.GET.get("ajax") or "").strip() == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})

    # Choices for filters
    status_choices = list(WorkflowStatus.choices)
    kind_choices = list(Device.Kind.choices)
    location_type_choices = list(Location.LOCATION_TYPES)

    ctx = {
        "title": "График тайлан",
        "status_choices": status_choices,
        "kind_choices": kind_choices,
        "location_type_choices": location_type_choices,
        "filter_axis": axis,
        "filter_status": filter_status,
        "filter_kind": filter_kind,
        "filter_location_type": filter_location_type,
        "filter_date_from": request.GET.get("date_from") or "",
        "filter_date_to": request.GET.get("date_to") or "",
        # JSON blobs (initial render)
        "echarts_workflow_json": json.dumps(payload.get("echarts_workflow_stacked") or {"axis": [], "pending": [], "approved": [], "rejected": []}, cls=DjangoJSONEncoder, ensure_ascii=False),
        "echarts_aimag_json": json.dumps(payload.get("echarts_aimag") or [], cls=DjangoJSONEncoder, ensure_ascii=False),
        "echarts_kind_json": json.dumps(payload.get("echarts_kind") or [], cls=DjangoJSONEncoder, ensure_ascii=False),
        "echarts_sla_json": json.dumps(payload.get("echarts_sla") or {"axis": [], "sla_hours": []}, cls=DjangoJSONEncoder, ensure_ascii=False),
        "locations_json": json.dumps(payload.get("locations") or [], cls=DjangoJSONEncoder, ensure_ascii=False),
    }
    return render(request, "admin/inventory/dashboard_graph.html", ctx)
