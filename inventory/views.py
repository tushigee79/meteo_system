from __future__ import annotations

import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Max
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, Max
from django.core.serializers.json import DjangoJSONEncoder
import json
from inventory.models import Location, SumDuureg, Device

# ---------------------------------------------------------------------
# 1. Admin Data Entry Redirection
# ---------------------------------------------------------------------

@staff_member_required(login_url="/django-admin/login/")
def admin_data_entry(request: HttpRequest) -> HttpResponse:
    """
    'Өгөгдөл бүртгэх (Админ)' entry point.
    Одоогоор хамгийн safe нь Django admin руу чиглүүлэх.
    """
    return redirect("/django-admin/", permanent=False)


# ---------------------------------------------------------------------
# 2. Map Visualization Views
# ---------------------------------------------------------------------

@staff_member_required
def station_map_view(request):
    """Compatibility alias for station map."""
    return location_map(request)


@staff_member_required
def location_map(request, location_id: int | None = None):
    """
    Байршлын газрын зураг.
    - /inventory/map/             -> бүх станцууд (cluster + filters)
    - /inventory/map/location/ID/ -> нэг станц (single marker)
    """
    # --- Helpers ---
    def _p(*keys: str) -> str:
        for k in keys:
            v = (request.GET.get(k) or "").strip()
            if v: return v
        return ""

    def _int(s: str) -> int | None:
        try: return int(s)
        except Exception: return None

    def _norm(s: str) -> str:
        return (s or "").strip()

    # --- 1) Single-location view ---
    if location_id is not None:
        loc = get_object_or_404(
            Location.objects.select_related("aimag_ref", "sum_ref", "owner_org"),
            pk=location_id,
        )
        item = {
            "id": loc.id,
            "name": loc.name,
            "lat": float(loc.latitude) if loc.latitude is not None else None,
            "lon": float(loc.longitude) if loc.longitude is not None else None,
            "location_type": loc.location_type,
            "aimag": getattr(getattr(loc, "aimag_ref", None), "name", None),
            "sum": getattr(getattr(loc, "sum_ref", None), "name", None),
            "district": getattr(loc, "district_name", None),
            "owner_org": getattr(getattr(loc, "owner_org", None), "name", None),
        }
        return render(request, "inventory/location_map_one.html", {"location_json": json.dumps(item, ensure_ascii=False)})

    # --- 2) Filtered queryset (multi) ---
    aimag = _int(_p("aimag", "aimag_ref__id__exact", "aimag_ref_id"))
    sum_id = _int(_p("sum", "sum_ref__id__exact", "sum_ref_id", "sumduureg"))
    district = _p("district", "district_name", "district_name__exact")
    location_type = _norm(_p("location_type", "location_type__exact", "loc_type"))
    kind = _norm(_p("kind", "device_kind"))
    status = _p("status", "device_status")

    qs = Location.objects.select_related("aimag_ref", "sum_ref", "owner_org").all()

    if aimag: qs = qs.filter(aimag_ref_id=aimag)
    if sum_id: qs = qs.filter(sum_ref_id=sum_id)
    if district: qs = qs.filter(district_name__iexact=district)
    if location_type: qs = qs.filter(location_type__iexact=location_type)

    # Device filters
    if kind: qs = qs.filter(devices__kind__iexact=kind)
    if status: qs = qs.filter(devices__status=status)

    # --- 3) Aggregations ---
    qs = qs.annotate(
        device_count=Count("devices", distinct=True),
        pending_maintenance=Count(
            "devices__maintenance_services",
            distinct=True,
            filter=Q(devices__maintenance_services__workflow_status="SUBMITTED"),
        ),
        pending_control=Count(
            "devices__control_adjustments",
            distinct=True,
            filter=Q(devices__control_adjustments__workflow_status="SUBMITTED"),
        ),
        last_maintenance_date=Max("devices__maintenance_services__date"),
        last_control_date=Max("devices__control_adjustments__date"),
        any_broken=Count(
            "devices",
            distinct=True,
            filter=Q(devices__status__in=["Broken", "Repair"]),
        ),
    ).distinct()

    rows = qs.values(
        "id", "name", "latitude", "longitude", "location_type", "district_name",
        "aimag_ref__name", "sum_ref__name", "owner_org__name",
        "device_count", "pending_maintenance", "pending_control",
        "last_maintenance_date", "last_control_date", "any_broken",
    )

    items = []
    for r in rows:
        lat = r.get("latitude")
        lon = r.get("longitude")
        
        # Status inference
        if (r.get("device_count") or 0) <= 0: st = "Багажгүй"
        elif (r.get("any_broken") or 0) > 0: st = "Эвдрэлтэй"
        else: st = "Хэвийн"

        pm = int(r.get("pending_maintenance") or 0)
        pc = int(r.get("pending_control") or 0)

        items.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "lat": float(lat) if lat is not None else None,
            "lon": float(lon) if lon is not None else None,
            "location_type": r.get("location_type"),
            "aimag": r.get("aimag_ref__name"),
            "sum": r.get("sum_ref__name"),
            "district": r.get("district_name"),
            "owner_org": r.get("owner_org__name"),
            "device_status": st,
            "device_count": int(r.get("device_count") or 0),
            "pending_maintenance": pm,
            "pending_control": pc,
            "pending_total": pm + pc,
            "last_maintenance_date": (r.get("last_maintenance_date") or "").__str__(),
            "last_control_date": (r.get("last_control_date") or "").__str__(),
        })

    return render(
        request,
        "inventory/location_map.html",
        {"locations_json": json.dumps(items, ensure_ascii=False, cls=DjangoJSONEncoder)},
    )


# ---------------------------------------------------------------------
# 3. QR Code Public & Private Views
# ---------------------------------------------------------------------

def _qr_get_device_or_404(token):
    return get_object_or_404(Device, qr_token=token)

def _qr_is_valid(device) -> tuple[bool, str]:
    now = timezone.now()
    if getattr(device, "qr_revoked_at", None):
        return False, "QR хүчингүй болсон байна."
    exp = getattr(device, "qr_expires_at", None)
    if exp and exp < now:
        return False, "QR хугацаа дууссан байна."
    return True, ""

@staff_member_required(login_url="/django-admin/login/")
def qr_device_lookup(request, token):
    """QR -> тухайн Device-ийн admin change page руу staff хэрэглэгчийг чиглүүлнэ."""
    device = _qr_get_device_or_404(token)
    ok, msg = _qr_is_valid(device)
    if not ok:
        return HttpResponse(msg, status=410)

    url = reverse("admin:inventory_device_change", args=[device.pk])
    return redirect(url, permanent=False)

def qr_device_public_view(request, token):
    """Public read-only view (HTML)."""
    device = _qr_get_device_or_404(token)
    ok, msg = _qr_is_valid(device)
    if not ok:
        return HttpResponse(msg, status=410)

    serial = getattr(device, "serial_number", "") or "-"
    kind = getattr(device, "kind", "") or "-"
    status = getattr(device, "status", "") or "-"
    loc = getattr(getattr(device, "location", None), "name", "") or "-"

    # PDF татах линк үүсгэх
    # Та urls.py дотроо 'qr_device_public_passport_pdf' гэж нэрлэсэн байх ёстой
    try:
        pdf_url = reverse('qr_device_public_passport_pdf', args=[token])
    except:
        # Хэрэв inventory namespace ашиглаж байгаа бол:
        try:
            pdf_url = reverse('inventory:qr_device_public_passport_pdf', args=[token])
        except:
            pdf_url = "#"
            
            # ---------------------------------------------------------------------
# 4. Dashboard Visualization View
# ---------------------------------------------------------------------

@staff_member_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Dashboard-ийн статистик болон графикуудыг харуулах view.
    """
    # KPI Тоонууд
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status='Active').count()
    broken_devices = Device.objects.filter(status__in=['Broken', 'Repair']).count()
    expired_count = Device.objects.filter(verification_status='expired').count()

    # Калибровкын нарийвчилсан тоонууд (Cards)
    calib_expired = Device.objects.filter(verification_status='expired').count()
    calib_due_30 = Device.objects.filter(verification_status='due_30').count()
    calib_due_90 = Device.objects.filter(verification_status='due_90').count()
    calib_unknown = Device.objects.filter(verification_status='unknown').count()

    # 1. Төлөвийн статистик (Doughnut Chart)
    status_stats = list(Device.objects.values('status').annotate(count=Count('id')))
    
    # 2. Аймгуудын эвдрэлийн статистик (Top 10 Bar Chart)
    aimag_stats = list(
        Location.objects.filter(devices__status__in=['Broken', 'Repair'])
        .values(name=F('aimag_ref__name'))
        .annotate(broken_count=Count('devices'))
        .order_by('-broken_count')[:10]
    )

    # 3. Калибровкын төлөвийн статистик (Шинэ Doughnut Chart - Баруун талын)
    # Энд 'valid' төлөвийг 'due_90' болон бусад хэвийн төлөвүүдийн нийлбэр гэж үзэв
    calib_valid = Device.objects.filter(verification_status__in=['due_90', 'valid']).count()
    
    calib_chart_data = [
        {'status': 'Expired', 'count': calib_expired},
        {'status': 'Due30', 'count': calib_due_30},
        {'status': 'Valid', 'count': calib_valid},
    ]

    context = {
        'title': 'Багаж хэрэгслийн хяналтын самбар',
        'total_devices': total_devices,
        'active_devices': active_devices,
        'broken_devices': broken_devices,
        'expired_count': expired_count,
        
        'calib_expired': calib_expired,
        'calib_due_30': calib_due_30,
        'calib_due_90': calib_due_90,
        'calib_unknown': calib_unknown,

        # JSON өгөгдлүүд (Charts)
        'status_stats_json': json.dumps(status_stats, cls=DjangoJSONEncoder),
        'aimag_stats_json': json.dumps(aimag_stats, cls=DjangoJSONEncoder),
        'calib_stats_json': json.dumps(calib_chart_data, cls=DjangoJSONEncoder),
    }

    return render(request, "inventory/dashboard.html", context)

    html = f"""<!doctype html>
<html lang="mn">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Device мэдээлэл</title>
  <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial; margin:24px;}}
    .card{{max-width:720px; padding:16px 18px; border:1px solid #e5e7eb; border-radius:14px;}}
    .row{{margin:8px 0;}}
    .k{{color:#6b7280; width:140px; display:inline-block;}}
    .btn{{display:inline-block; margin-top:14px; padding:10px 14px; border-radius:10px; border:1px solid #d1d5db; text-decoration:none; color: #333; background: #f3f4f6;}}
    .btn:hover{{background: #e5e7eb;}}
  </style>
</head>
<body>
  <div class="card">
    <h2 style="margin:0 0 8px 0;">Багаж (Read-only)</h2>
    <div class="row"><span class="k">Серийн №</span> {serial}</div>
    <div class="row"><span class="k">Төрөл</span> {kind}</div>
    <div class="row"><span class="k">Төлөв</span> {status}</div>
    <div class="row"><span class="k">Байршил</span> {loc}</div>
    <a class="btn" href="{pdf_url}">📄 Техник паспорт (PDF)</a>
  </div>
</body>
</html>"""
    return HttpResponse(html)


def qr_device_public_passport_pdf(request, token):
    """Public readonly PDF download."""
    device = _qr_get_device_or_404(token)
    ok, msg = _qr_is_valid(device)
    if not ok:
        return HttpResponse(msg, status=410)

    # Бидний дөнгөж сая үүсгэсэн pdf_passport файлаас дуудна
    from inventory.pdf_passport import generate_device_passport_pdf_bytes
    
    pdf_bytes = generate_device_passport_pdf_bytes(device)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    # inline: хөтөч дээр шууд нээгдэнэ (attachment бол татагдана)
    resp["Content-Disposition"] = f'inline; filename="device_passport_{device.pk}.pdf"'
    return resp