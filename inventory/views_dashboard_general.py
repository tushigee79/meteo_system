# inventory/views_dashboard_general.py
from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Max
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

# --- Readiness Helpers ---

def _score_pct(ok_count, total_count, weight):
    if not total_count:
        return 0.0
    return round((ok_count / total_count) * weight, 1)


def _readiness_payload(devices_qs, locations_qs, label, today, verif_field):
    total_devices = devices_qs.count()
    total_locations = locations_qs.count()

    serial_ok = devices_qs.exclude(Q(serial_number__isnull=True) | Q(serial_number="")).count()

    qr_ok = 0
    if hasattr(Device, "qr_token"):
        qr_ok = devices_qs.exclude(qr_token__isnull=True).count()

    passport_ok = qr_ok

    if verif_field:
        verif_ok = devices_qs.exclude(**{f"{verif_field}__isnull": True}).exclude(**{f"{verif_field}__lt": today}).count()
    else:
        verif_ok = 0

    op_ok = locations_qs.exclude(devices__status__in=["Broken", "Repair"]).distinct().count()

    metadata_score = _score_pct(serial_ok, total_devices, 25)
    qr_score = _score_pct(qr_ok, total_devices, 15)
    passport_score = _score_pct(passport_ok, total_devices, 15)
    verif_score = _score_pct(verif_ok, total_devices, 25)
    ops_score = _score_pct(op_ok, total_locations, 20)

    total_score = round(metadata_score + qr_score + passport_score + verif_score + ops_score, 1)

    if total_score < 60:
        risk = "HIGH"
        color = "danger"
    elif total_score < 85:
        risk = "MEDIUM"
        color = "warning"
    else:
        risk = "LOW"
        color = "success"

    return {
        "label": label,
        "total_devices": int(total_devices),
        "total_locations": int(total_locations),
        "metadata_score": metadata_score,
        "qr_score": qr_score,
        "passport_score": passport_score,
        "verif_score": verif_score,
        "ops_score": ops_score,
        "score": total_score,
        "risk": risk,
        "color": color,
    }


@staff_member_required
def general_dashboard_view(request: HttpRequest) -> HttpResponse:
    from .admin import inventory_admin_site

    # --- date range
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
        workflow_status="SUBMITTED", date__gte=d_from, date__lte=d_to, device__in=dev_qs,
    )
    ca_sub_qs = ControlAdjustment.objects.filter(
        workflow_status="SUBMITTED", date__gte=d_from, date__lte=d_to, device__in=dev_qs,
    )
    pending_total_items = ms_sub_qs.count() + ca_sub_qs.count()
    broken_locations = loc_qs.filter(devices__status="Broken").distinct().count()

    # --- National monitoring metrics ---
    stations_no_device = loc_qs.filter(devices__isnull=True).count()
    stations_with_device = loc_qs.filter(devices__isnull=False).distinct().count()
    devices_no_serial = dev_qs.filter(Q(serial_number__isnull=True) | Q(serial_number="")).count()
    devices_no_location = Device.objects.filter(location__isnull=True).count()
    devices_no_verif = dev_qs.filter(Q(next_verification_date__isnull=True)).count()

    device_kind_stats = list(dev_qs.values("kind").annotate(n=Count("id")).order_by("-n"))
    device_kind_json = json.dumps(device_kind_stats, ensure_ascii=False)

    # --- verification settings
    today = timezone.localdate()
    due30_days = _verif_days("VERIF_DUE_30_DAYS", 30)
    due90_days = _verif_days("VERIF_DUE_90_DAYS", 90)
    verif_field = _device_next_verif_field()

    # --- Special systems monitoring payload function ---
    def _system_panel_payload(loc_subset, label):
        loc_ids = list(loc_subset.values_list("id", flat=True))
        dev_subset = dev_qs.filter(location_id__in=loc_ids)
        
        total_sites = loc_subset.count()
        total_devices_in_sites = dev_subset.count()
        broken_devices = dev_subset.filter(status__in=["Broken", "Repair"]).count()

        if verif_field:
            verif_expired = dev_subset.filter(**{f"{verif_field}__lt": today}).count()
            verif_missing = dev_subset.filter(**{f"{verif_field}__isnull": True}).count()
        else:
            verif_expired = 0
            verif_missing = dev_subset.count()

        qr_missing = 0
        if hasattr(Device, "qr_token"):
            qr_missing = dev_subset.filter(qr_token__isnull=True).count()

        serial_missing = dev_subset.filter(Q(serial_number__isnull=True) | Q(serial_number="")).count()
        
        # Operational site logic
        broken_sites = loc_subset.filter(devices__status__in=["Broken", "Repair"]).distinct().count()
        empty_sites = loc_subset.filter(devices__isnull=True).distinct().count()
        operational_sites = max(total_sites - broken_sites - empty_sites, 0)

        return {
            "label": label,
            "total_sites": int(total_sites),
            "total_devices": int(total_devices_in_sites),
            "operational_sites": int(operational_sites),
            "broken_sites": int(broken_sites),
            "empty_sites": int(empty_sites),
            "broken_devices": int(broken_devices),
            "verif_expired": int(verif_expired),
            "verif_missing": int(verif_missing),
            "qr_missing": int(qr_missing),
            "serial_missing": int(serial_missing),
        }

    def _safe_loc_type_filter(qs, values):
        if hasattr(Location, "location_type"):
            return qs.filter(location_type__in=values)
        return qs.none()

    radar_locs = _safe_loc_type_filter(loc_qs, ["RADAR"])
    aws_locs = _safe_loc_type_filter(loc_qs, ["AWS"])
    aero_locs = _safe_loc_type_filter(loc_qs, ["AEROLOGY", "AER", "UPPERAIR"])

    systems_summary = [
        _system_panel_payload(radar_locs, "RADAR"),
        _system_panel_payload(aws_locs, "AWS"),
        _system_panel_payload(aero_locs, "AEROLOGY"),
    ]
    systems_summary_json = json.dumps(systems_summary, ensure_ascii=False)

    # --- Status Pie & Workflow Trend ---
    site = inventory_admin_site.name
    device_changelist = reverse(f"{site}:inventory_device_changelist")
    status_counts = dev_qs.values("status").annotate(n=Count("id")).order_by()
    echarts_status = [{"name": (r.get("status") or "").strip(), "value": int(r.get("n") or 0), 
                       "url": f"{device_changelist}?status__exact={r.get('status')}"} for r in status_counts if r.get("status")]
    echarts_status_json = json.dumps(echarts_status, ensure_ascii=False)

    ms_by_day = dict(ms_sub_qs.annotate(d=TruncDate("date")).values("d").annotate(n=Count("id")).values_list("d", "n"))
try:
    ca_by_day = dict(
        ca_sub_qs
        .exclude(date__isnull=True)
        .values("date")
        .annotate(n=Count("id"))
        .values_list("date", "n")
    )
except Exception:
    ca_by_day = {}
    wf_payload = {
        "axis": [d.isoformat() for d in axis_days],
        "ms": [int(ms_by_day.get(d, 0) or 0) for d in axis_days],
        "ca": [int(ca_by_day.get(d, 0) or 0) for d in axis_days],
    }
    echarts_workflow_json = json.dumps(wf_payload, ensure_ascii=False)

    # --- Verification Trend ---
    if verif_field:
        buckets = _verification_buckets(dev_qs, field=verif_field, today=today, due30_days=due30_days, due90_days=due90_days)
        verif_trend = _verification_trend(dev_qs, field=verif_field, today=today, days=90, due30_days=due30_days, due90_days=due90_days)
    else:
        buckets = {"expired": 0, "due30": 0, "due90": 0}
        verif_trend = {"axis": [], "expired": [], "due30": [], "due90": []}

    # --- Lifecycle & Maintenance ---
    recent_cutoff = today - timedelta(days=180)
    maintained_ids = MaintenanceService.objects.filter(device__in=dev_qs).values_list("device_id", flat=True).distinct()
    controlled_ids = ControlAdjustment.objects.filter(device__in=dev_qs).values_list("device_id", flat=True).distinct()
    
    maintenance_overdue_count = dev_qs.exclude(id__in=maintained_ids).count()
    control_overdue_count = dev_qs.exclude(id__in=controlled_ids).count()

    last_ms = MaintenanceService.objects.filter(device__in=dev_qs).values("device_id").annotate(ld=Max("date"))
    fresh_maintenance = sum(1 for r in last_ms if r["ld"] and r["ld"] >= recent_cutoff)
    stale_maintenance = total_devices - fresh_maintenance

    last_ca = ControlAdjustment.objects.filter(device__in=dev_qs).values("device_id").annotate(ld=Max("date"))
    fresh_control = sum(1 for r in last_ca if r["ld"] and r["ld"] >= recent_cutoff)
    stale_control = total_devices - fresh_control

    # QR / Movement
    qr_ready_count = dev_qs.exclude(qr_token__isnull=True).count() 
    if hasattr(Device, "qr_token"):
        qr_ready_count = dev_qs.exclude(qr_token__isnull=True).count()
        qr_missing_count = dev_qs.filter(qr_token__isnull=True).count()
    else:
        qr_ready_count = 0
        qr_missing_count = 0
    qr_missing = dev_qs.filter(qr_token__isnull=True).count()
    
    movement_count = 0
    recent_movement_count = 0
    try:
        from .models import DeviceMovement
        mv_qs = DeviceMovement.objects.filter(device__in=dev_qs)
        movement_count = mv_qs.count()
        recent_movement_count = mv_qs.filter(date__gte=today-timedelta(days=30)).count()
    except Exception: pass

    # --- Risk Matrix ---
    risk_matrix = []
    for s in systems_summary:
        risk_matrix.append({
            "label": s["label"], "score": 0, "risk_level": "N/A", "verif_expired": s["verif_expired"],
            "qr_missing": s["qr_missing"], "broken_devices": s["broken_devices"], "serial_missing": s["serial_missing"]
        })

    # --- National Compliance & Readiness Index (New) ---
    national_readiness = _readiness_payload(dev_qs, loc_qs, "MONGOLIA", today, verif_field)

    aimag_readiness = []
    aimag_rows = loc_qs.values("aimag_ref_id", "aimag_ref__name").annotate(n=Count("id")).order_by("aimag_ref__name")
    for row in aimag_rows:
        a_id = row.get("aimag_ref_id")
        if not a_id: continue
        a_loc = loc_qs.filter(aimag_ref_id=a_id)
        a_dev = dev_qs.filter(location__aimag_ref_id=a_id)
        p = _readiness_payload(a_dev, a_loc, row.get("aimag_ref__name") or "Unknown", today, verif_field)
        p.update({"reports_url": f"/django-admin/reports/?aimag={a_id}", "map_url": f"/inventory/map/?aimag={a_id}"})
        aimag_readiness.append(p)

    org_readiness = []
    org_rows = loc_qs.values("owner_org_id", "owner_org__name").annotate(n=Count("id")).order_by("owner_org__name")
    for row in org_rows:
        o_id = row.get("owner_org_id")
        if not o_id: continue
        o_loc = loc_qs.filter(owner_org_id=o_id)
        o_dev = dev_qs.filter(location__owner_org_id=o_id)
        p = _readiness_payload(o_dev, o_loc, row.get("owner_org__name") or "Unknown", today, verif_field)
        p.update({"reports_url": f"/django-admin/reports/?owner_org={o_id}", "map_url": f"/inventory/map/?owner_org={o_id}"})
        org_readiness.append(p)

    # --- Map Points ---
    loc_annot = loc_qs.annotate(dc=Count("devices", distinct=True), 
                                bd=Count("devices", filter=Q(devices__status="Broken"), distinct=True))
    points = [{"id": o.id, "name": o.name, "lat": float(o.latitude), "lon": float(o.longitude), "status": "OK" if o.bd == 0 else "BROKEN"} 
              for o in loc_annot[:5000] if o.latitude and o.longitude]

    # --- Context assembly ---
    ctx = dict(
        inventory_admin_site.each_context(request),
        title="Ерөнхий мэдээлэл",
        date_from=d_from, date_to=d_to,
        total_locations=total_locations, total_devices=total_devices,
        pending_total_items=pending_total_items, broken_locations=broken_locations,
        stations_no_device=stations_no_device, stations_with_device=stations_with_device,
        devices_no_serial=devices_no_serial, devices_no_location=devices_no_location,
        devices_no_verif=devices_no_verif,
        verif_buckets_json=json.dumps(buckets), expired_count=buckets["expired"],
        maintenance_overdue_count=maintenance_overdue_count, control_overdue_count=control_overdue_count,
        fresh_maintenance=fresh_maintenance, stale_maintenance=stale_maintenance,
        fresh_control=fresh_control, stale_control=stale_control,
        qr_ready_count=qr_ready_count, qr_missing_count=qr_missing_count,
        movement_count=movement_count, recent_movement_count=recent_movement_count,
        echarts_status_json=echarts_status_json, echarts_workflow_json=echarts_workflow_json,
        echarts_verif_trend_json=json.dumps(verif_trend), locations_json=json.dumps(points),
        systems_summary=systems_summary, systems_summary_json=systems_summary_json,
        risk_matrix=risk_matrix,
        # Readiness Index Context
        national_readiness=national_readiness,
        national_readiness_json=json.dumps(national_readiness, ensure_ascii=False),
        aimag_readiness=aimag_readiness,
        aimag_readiness_json=json.dumps(aimag_readiness, ensure_ascii=False),
        org_readiness=org_readiness,
        org_readiness_json=json.dumps(org_readiness, ensure_ascii=False),
        verif_field=verif_field or "next_verification_date",
    )

    return render(request, "admin/dashboard_unified.html", ctx)