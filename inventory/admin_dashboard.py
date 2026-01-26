# inventory/admin_dashboard.py
# -*- coding: utf-8 -*-

import csv
import json
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch
from django.utils import timezone

from .dashboard import build_dashboard_context, scoped_devices_qs
from .models import Location, Device, MaintenanceService, ControlAdjustment


# ============================================================
# 8 төрөл — Location.location_type
# (JS чинь typeColors-оо өөр дээрээ тодорхойлсон тул өнгийг заавал ашиглахгүй,
#  гэхдээ popup/шүүлтүүр/ирээдүйн UI-д хэрэгтэй гэж type_color дамжуулна.)
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


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


@staff_member_required(login_url="/django-admin/login/")
def dashboard_table_view(request):
    """
    Хүснэгт/KPI dashboard
    Template: templates/admin/dashboard.html
    """
    ctx = build_dashboard_context(request.user)
    return render(request, "admin/dashboard.html", ctx)


@staff_member_required(login_url="/django-admin/login/")
def dashboard_graph_view(request):
    """
    График + Газрын зурагтай Dashboard
    Template: templates/inventory/dashboard.html

    ✅ Legacy compatibility:
      - p.color MUST be 'red'/'green'/'gray' (location_map.html эхний блок үүнийг шууд ашигладаг)
        :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3}

    ✅ New fields (break хийхгүйгээр нэмэгдэнэ):
      - type/type_color (8 төрөл)
      - status/status_color (нарийн төлөв)
      - counts/pending/last dates (popup-д ашиглах боломжтой)
    """
    ctx = build_dashboard_context(request.user)

    # ✅ scope: зөвхөн хэрэглэгчийн харж болох device-үүд
    scoped_qs = scoped_devices_qs(request.user).select_related("location")

    loc_ids = (
        scoped_qs.exclude(location__isnull=True)
        .values_list("location_id", flat=True)
        .distinct()
    )

    devices_prefetch = Prefetch(
        "devices",
        queryset=(
            Device.objects.filter(location_id__in=loc_ids)
            .only("id", "location_id", "status", "serial_number")
            .prefetch_related(
                Prefetch(
                    "maintenance_services",
                    queryset=MaintenanceService.objects.only("id", "device_id", "date", "workflow_status"),
                ),
                Prefetch(
                    "control_adjustments",
                    queryset=ControlAdjustment.objects.only("id", "device_id", "date", "workflow_status"),
                ),
            )
        ),
    )

    locations = (
        Location.objects.filter(id__in=loc_ids)
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .only("id", "name", "latitude", "longitude", "location_type")
        .prefetch_related(devices_prefetch)
    )

    now = timezone.now()
    recent_window = now.date() - timedelta(days=90)

    points = []
    for loc in locations:
        lat = _safe_float(loc.latitude)
        lon = _safe_float(loc.longitude)
        if lat is None or lon is None:
            continue

        devs = list(loc.devices.all())

        # --- device status counts ---
        counts = {"Active": 0, "Broken": 0, "Repair": 0, "Spare": 0, "Retired": 0, "Other": 0}
        for d in devs:
            s = getattr(d, "status", None) or "Other"
            counts[s] = counts.get(s, 0) + 1

        device_count = len(devs)

        # --- workflow pending + last dates ---
        pending = 0
        last_ms = None
        last_ca = None

        for d in devs:
            for ms in getattr(d, "maintenance_services", []).all():
                if ms.workflow_status == "SUBMITTED":
                    pending += 1
                if ms.date and (last_ms is None or ms.date > last_ms):
                    last_ms = ms.date

            for ca in getattr(d, "control_adjustments", []).all():
                if ca.workflow_status == "SUBMITTED":
                    pending += 1
                if ca.date and (last_ca is None or ca.date > last_ca):
                    last_ca = ca.date

        # ============================================================
        # ✅ New “нарийн төлөв”
        # ============================================================
        status = "OK"
        status_color = "green"

        if counts.get("Broken", 0) > 0 or counts.get("Repair", 0) > 0:
            status = "CRITICAL"
            status_color = "red"
        elif pending > 0:
            status = "NEED_APPROVAL"
            status_color = "orange"
        elif device_count == 0:
            status = "NO_DEVICE"
            status_color = "gray"
        else:
            has_any_history = (last_ms is not None) or (last_ca is not None)
            if not has_any_history:
                status = "NO_HISTORY"
                status_color = "yellow"
            else:
                recent_ok = False
                if last_ms and last_ms >= recent_window:
                    recent_ok = True
                if last_ca and last_ca >= recent_window:
                    recent_ok = True
                status = "OK_RECENT" if recent_ok else "OK"
                status_color = "green"

        # ============================================================
        # ✅ Legacy “color” (location_map.html эхний блок эвдэхгүй)
        #   - red: Broken/Repair байвал
        #   - gray: багажгүй
        #   - green: бусад
        # ============================================================
        legacy_color = "green"
        if counts.get("Broken", 0) > 0 or counts.get("Repair", 0) > 0:
            legacy_color = "red"
        elif device_count == 0:
            legacy_color = "gray"

        loc_type = (getattr(loc, "location_type", None) or "OTHER").strip().upper()
        if loc_type not in LOCATION_TYPE_COLOR:
            loc_type = "OTHER"

        points.append(
            {
                "id": loc.id,
                "name": loc.name,
                "lat": lat,
                "lon": lon,

                # 8 төрөл
                "type": loc_type,
                "location_type": loc_type,  # JS-д аль аль нь байхад гэмгүй
                "type_color": LOCATION_TYPE_COLOR.get(loc_type, LOCATION_TYPE_COLOR["OTHER"]),
                "type_label": loc.get_location_type_display() if hasattr(loc, "get_location_type_display") else loc_type,

                # шинэ төлөв
                "status": status,
                "status_color": status_color,

                # хуучин JS эвдэхгүй талбар
                "color": legacy_color,

                # нэмэлт мэдээлэл
                "device_count": device_count,
                "counts": counts,
                "pending_workflow_count": pending,
                "last_maintenance_date": last_ms.isoformat() if last_ms else None,
                "last_control_date": last_ca.isoformat() if last_ca else None,
            }
        )

    ctx["locations_json"] = json.dumps(points, cls=DjangoJSONEncoder)
    return render(request, "inventory/dashboard.html", ctx)


@staff_member_required(login_url="/django-admin/login/")
def export_devices_csv(request):
    """
    Багажуудыг CSV хэлбэрээр экспортлох (scope мөрдөнө)
    """
    qs = scoped_devices_qs(request.user).select_related("catalog_item", "location")

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="devices_export.csv"'
    resp.write("\ufeff")  # Excel-д UTF-8 BOM

    w = csv.writer(resp)
    w.writerow(
        [
            "ID",
            "Төрөл(kind)",
            "Каталогийн нэр",
            "Бусад нэр",
            "Байршил",
            "Серийн дугаар",
            "Төлөв(status)",
        ]
    )

    for d in qs:
        kind = d.catalog_item.get_kind_display() if getattr(d, "catalog_item", None) else "-"
        cat_name = d.catalog_item.name_mn if getattr(d, "catalog_item", None) else "-"
        loc_name = str(d.location) if getattr(d, "location", None) else "-"
        w.writerow(
            [
                d.id,
                kind,
                cat_name,
                getattr(d, "other_name", "") or "",
                loc_name,
                getattr(d, "serial_number", "-"),
                getattr(d, "status", "-"),
            ]
        )

    return resp
