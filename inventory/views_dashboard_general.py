# inventory/views_dashboard_general.py
from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import ControlAdjustment, Device, Location, MaintenanceService


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _date_range_default() -> Tuple[date, date]:
    """Default: last 30 days (inclusive)."""
    today = timezone.localdate()
    return today - timedelta(days=29), today


def _daterange_list(d1: date, d2: date) -> List[date]:
    if d2 < d1:
        d1, d2 = d2, d1
    out: List[date] = []
    cur = d1
    while cur <= d2:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _scope_location_qs(request: HttpRequest):
    """Scope locations to current user's aimag (if applicable)."""
    qs = Location.objects.all()

    u = getattr(request, "user", None)
    if not u or getattr(u, "is_superuser", False):
        return qs

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)
    if not aimag_id:
        return qs.none()

    # (UB district-level scope хэрэгтэй бол admin.py дээрх шиг өргөтгөж болно)
    return qs.filter(aimag_ref_id=aimag_id)


def _scope_device_qs(request: HttpRequest):
    """Scope devices by scoped locations."""
    locs = _scope_location_qs(request).values_list("id", flat=True)
    return Device.objects.filter(location_id__in=locs)


def _verif_days(name: str, default: int) -> int:
    v = getattr(settings, name, default)
    try:
        return int(v)
    except Exception:
        return default


def _device_next_verif_field() -> Optional[str]:
    """Find best available next verification date field on Device."""
    candidates = ("next_verification_date", "next_calibration_date", "next_due_date", "next_verif_date")
    try:
        names = {f.name for f in Device._meta.get_fields() if hasattr(f, "name")}
    except Exception:
        names = set()
    for c in candidates:
        if c in names:
            return c
    return None


def _verification_buckets(dev_qs, *, field: str, today: date, due30_days: int, due90_days: int) -> Dict[str, int]:
    """Return counts: expired / due30 / due90 (due90 excludes due30)."""
    d30 = today + timedelta(days=due30_days)
    d90 = today + timedelta(days=due90_days)

    expired = dev_qs.filter(**{f"{field}__lt": today}).count()
    due30 = dev_qs.filter(**{f"{field}__range": (today, d30)}).count()
    due90 = dev_qs.filter(**{f"{field}__range": (d30 + timedelta(days=1), d90)}).count()
    return {"expired": int(expired), "due30": int(due30), "due90": int(due90)}


def _verification_trend(dev_qs, *, field: str, today: date, days: int, due30_days: int, due90_days: int) -> Dict[str, Any]:
    """
    Trend series for last N days:
    - expired_at_t: < t
    - due30_at_t  : [t, t+30]
    - due90_at_t  : [t+31, t+90]
    Efficient using bisect on sorted dates.
    """
    start = today - timedelta(days=days - 1)
    axis_days = [start + timedelta(days=i) for i in range(days)]

    dates = list(dev_qs.exclude(**{f"{field}__isnull": True}).values_list(field, flat=True))
    dates.sort()

    expired_series: List[int] = []
    due30_series: List[int] = []
    due90_series: List[int] = []

    for t in axis_days:
        expired = bisect_left(dates, t)

        t30 = t + timedelta(days=due30_days)
        t90 = t + timedelta(days=due90_days)

        due30 = bisect_right(dates, t30) - bisect_left(dates, t)
        due90 = bisect_right(dates, t90) - bisect_left(dates, t30 + timedelta(days=1))

        expired_series.append(int(expired))
        due30_series.append(int(due30))
        due90_series.append(int(due90))

    return {
        "axis": [d.isoformat() for d in axis_days],
        "expired": expired_series,
        "due30": due30_series,
        "due90": due90_series,
    }


@staff_member_required
def general_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Template: templates/admin/dashboard_unified.html
    KPI + status pie + workflow trend + map + verification pie/trend.
    """
    # runtime import to avoid circular import with admin.py
    from .admin import inventory_admin_site  # type: ignore

    # --- date range (workflow chart)
    d_from = _parse_date(request.GET.get("date_from"))
    d_to = _parse_date(request.GET.get("date_to"))
    if not d_from or not d_to:
        d_from, d_to = _date_range_default()
    if d_to < d_from:
        d_from, d_to = d_to, d_from
    axis_days = _daterange_list(d_from, d_to)

    # --- scoped QS
    loc_qs = _scope_location_qs(request)
    dev_qs = _scope_device_qs(request)

    # KPI
    total_locations = loc_qs.count()
    total_devices = dev_qs.count()

    ms_sub_qs = MaintenanceService.objects.filter(
        workflow_status="SUBMITTED",
        date__gte=d_from,
        date__lte=d_to,
        device__in=dev_qs,
    )
    ca_sub_qs = ControlAdjustment.objects.filter(
        workflow_status="SUBMITTED",
        date__gte=d_from,
        date__lte=d_to,
        device__in=dev_qs,
    )
    pending_total_items = ms_sub_qs.count() + ca_sub_qs.count()
    broken_locations = loc_qs.filter(devices__status="Broken").distinct().count()

    # --- verification (dynamic field + settings thresholds)
    today = timezone.localdate()
    due30_days = _verif_days("VERIF_DUE_30_DAYS", 30)
    due90_days = _verif_days("VERIF_DUE_90_DAYS", 90)
    verif_field = _device_next_verif_field()

    if verif_field:
        buckets = _verification_buckets(dev_qs, field=verif_field, today=today, due30_days=due30_days, due90_days=due90_days)
        verif_trend = _verification_trend(dev_qs, field=verif_field, today=today, days=90, due30_days=due30_days, due90_days=due90_days)
    else:
        buckets = {"expired": 0, "due30": 0, "due90": 0}
        verif_trend = {"axis": [], "expired": [], "due30": [], "due90": []}

    # --- status pie
    site = inventory_admin_site.name
    device_changelist = reverse(f"{site}:inventory_device_changelist")

    status_counts = dev_qs.values("status").annotate(n=Count("id")).order_by()
    echarts_status: List[Dict[str, Any]] = []
    for r in status_counts:
        st = (r.get("status") or "").strip()
        n = int(r.get("n") or 0)
        if not st:
            continue
        echarts_status.append({"name": st, "value": n, "url": f"{device_changelist}?status__exact={st}"})
    echarts_status_json = json.dumps(echarts_status, ensure_ascii=False)

    # --- workflow trend
    ms_by_day = dict(ms_sub_qs.annotate(d=TruncDate("date")).values("d").annotate(n=Count("id")).values_list("d", "n"))
    ca_by_day = dict(ca_sub_qs.annotate(d=TruncDate("date")).values("d").annotate(n=Count("id")).values_list("d", "n"))

    wf_payload = {
        "axis": [d.isoformat() for d in axis_days],
        "ms": [int(ms_by_day.get(d, 0) or 0) for d in axis_days],
        "ca": [int(ca_by_day.get(d, 0) or 0) for d in axis_days],
    }
    echarts_workflow_json = json.dumps(wf_payload, ensure_ascii=False)

    # --- map points
    location_change = lambda pk: reverse(f"{site}:inventory_location_change", args=[pk])
    device_list_for_loc = lambda pk: f"{device_changelist}?location__id__exact={pk}"

    loc_annot = loc_qs.annotate(
        device_count=Count("devices", distinct=True),
        pending_maintenance=Count(
            "devices__maintenance_services",
            filter=Q(devices__maintenance_services__workflow_status="SUBMITTED")
            & Q(devices__maintenance_services__date__gte=d_from)
            & Q(devices__maintenance_services__date__lte=d_to),
            distinct=True,
        ),
        pending_control=Count(
            "devices__control_adjustments",
            filter=Q(devices__control_adjustments__workflow_status="SUBMITTED")
            & Q(devices__control_adjustments__date__gte=d_from)
            & Q(devices__control_adjustments__date__lte=d_to),
            distinct=True,
        ),
        broken_devices=Count("devices", filter=Q(devices__status="Broken"), distinct=True),
    )

    points: List[Dict[str, Any]] = []
    for o in loc_annot[:5000]:
        if o.latitude is None or o.longitude is None:
            continue

        pending_total = int(getattr(o, "pending_maintenance", 0) or 0) + int(getattr(o, "pending_control", 0) or 0)
        dc = int(getattr(o, "device_count", 0) or 0)
        broken_dev = int(getattr(o, "broken_devices", 0) or 0)

        if pending_total > 0:
            status = "PENDING"
        elif dc == 0:
            status = "EMPTY"
        elif broken_dev > 0:
            status = "BROKEN"
        else:
            status = "OK"

        points.append(
            {
                "id": o.id,
                "name": o.name,
                "lat": float(o.latitude),
                "lon": float(o.longitude),
                "pending_total": pending_total,
                "status": status,
                "loc_admin_url": location_change(o.id),
                "device_list_url": device_list_for_loc(o.id),
            }
        )

    ctx = dict(
        inventory_admin_site.each_context(request),
        title="Ерөнхий мэдээлэл",
        date_from=d_from,
        date_to=d_to,
        total_locations=total_locations,
        total_devices=total_devices,
        pending_total_items=pending_total_items,
        broken_locations=broken_locations,
        echarts_status_json=echarts_status_json,
        echarts_workflow_json=echarts_workflow_json,
        locations_json=json.dumps(points, ensure_ascii=False),
        # verification
        verif_buckets_json=json.dumps(buckets, ensure_ascii=False),
        expired_count=buckets["expired"],
        echarts_verif_trend_json=json.dumps(verif_trend, ensure_ascii=False),
        # click→filter
        device_changelist_url=device_changelist,
        verif_field=verif_field or "next_verification_date",
        today_iso=today.isoformat(),
        due30_iso=(today + timedelta(days=due30_days)).isoformat(),
        due90_iso=(today + timedelta(days=due90_days)).isoformat(),
        due30_plus1_iso=(today + timedelta(days=due30_days + 1)).isoformat(),
    )
    return render(request, "admin/dashboard_unified.html", ctx)
