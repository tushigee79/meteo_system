from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Max, F
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from inventory.models import Location, SumDuureg, Device, Aimag, InstrumentCatalog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# 0. Helpers (Scope & Logic)
# ---------------------------------------------------------------------

def _get_scope(request: HttpRequest) -> dict:
    """Хэрэглэгчийн эрх мэдлийн хүрээг тодорхойлох"""
    u = getattr(request, "user", None)
    if not u or getattr(u, "is_superuser", False):
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)
    sum_id = (
        getattr(prof, "sumduureg_id", None)
        or getattr(prof, "sum_ref_id", None)
        or getattr(prof, "district_id", None)
    )
    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}

def _scope_location_qs(request: HttpRequest):
    """Хэрэглэгчийн харьяаллын дагуу Байршлын жагсаалтыг шүүх"""
    qs = Location.objects.all()
    scope = _get_scope(request)
    if scope["all"]:
        return qs
    if not scope["aimag_id"]:
        return qs.none()
    
    qs = qs.filter(aimag_ref_id=scope["aimag_id"])
    if scope["aimag_id"] == 1 and scope["sum_id"]:
        qs = qs.filter(sum_ref_id=scope["sum_id"])
    return qs

# ---------------------------------------------------------------------
# 1. Admin Data Entry Redirection
# ---------------------------------------------------------------------

@staff_member_required(login_url="/django-admin/login/")
def admin_data_entry(request: HttpRequest) -> HttpResponse:
    """'Өгөгдөл бүртгэх (Админ)' entry point."""
    return redirect("/django-admin/", permanent=False)

# ---------------------------------------------------------------------
# 2. Map Visualization Views
# ---------------------------------------------------------------------

@staff_member_required
def station_map_view(request):
    """urls.py-д ашиглагдах alias функц"""
    return location_map(request)

@staff_member_required
def location_map(request, location_id: int | None = None):
    """Байршлын газрын зураг (Бүх станц эсвэл нэг станц)"""
    
    def _p(*keys: str) -> str:
        for k in keys:
            v = (request.GET.get(k) or "").strip()
            if v: return v
        return ""

    def _int(s: str) -> int | None:
        try: return int(s)
        except: return None

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
            "aimag": getattr(loc.aimag_ref, "name", None),
            "sum": getattr(loc.sum_ref, "name", None),
            "district": getattr(loc, "district_name", None),
            "owner_org": getattr(loc.owner_org, "name", None),
        }
        return render(request, "inventory/location_map_one.html", {"location_json": json.dumps(item, ensure_ascii=False)})

    # --- 2) Filtered queryset (multi) ---
    aimag_val = _int(_p("aimag", "aimag_ref_id"))
    sum_val = _int(_p("sum", "sum_ref_id"))
    kind_val = _p("kind", "device_kind")
    status_val = _p("status", "device_status")

    qs = Location.objects.select_related("aimag_ref", "sum_ref", "owner_org").all()

    if aimag_val: qs = qs.filter(aimag_ref_id=aimag_val)
    if sum_val: qs = qs.filter(sum_ref_id=sum_val)
    if kind_val: qs = qs.filter(devices__kind__iexact=kind_val)
    if status_val: qs = qs.filter(devices__status=status_val)

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
        any_broken=Count("devices", distinct=True, filter=Q(devices__status__in=["Broken", "Repair"])),
    ).distinct()

    rows = qs.values(
        "id", "name", "latitude", "longitude", "location_type", "district_name",
        "aimag_ref__name", "sum_ref__name", "owner_org__name",
        "device_count", "pending_maintenance", "pending_control", "last_maintenance_date", "any_broken",
    )

    items = []
    for r in rows:
        lat, lon = r.get("latitude"), r.get("longitude")
        if lat and lon:
            # Status inference
            if (r.get("device_count") or 0) <= 0: st = "Багажгүй"
            elif (r.get("any_broken") or 0) > 0: st = "Эвдрэлтэй"
            else: st = "Хэвийн"

            pm = int(r.get("pending_maintenance") or 0)
            pc = int(r.get("pending_control") or 0)

            items.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "lat": float(lat),
                "lon": float(lon),
                "location_type": r.get("location_type"),
                "aimag": r.get("aimag_ref__name"),
                "sum": r.get("sum_ref__name"),
                "device_status": st,
                "device_count": r.get("device_count") or 0,
                "pending_maintenance": pm,
                "pending_control": pc,
                "pending_total": pm + pc,
                "last_maintenance_date": str(r.get("last_maintenance_date") or ""),
            })

    # Dropdown dropdown data
    aimags = Aimag.objects.all().order_by('name')
    sums = SumDuureg.objects.filter(aimag_id=aimag_val).order_by('name') if aimag_val else []
    kinds = [c[0] for c in InstrumentCatalog.Kind.choices]

    context = {
        "locations_json": json.dumps(items, ensure_ascii=False, cls=DjangoJSONEncoder),
        "aimags": aimags,
        "sums": sums,
        "kinds": kinds,
    }
    return render(request, "inventory/location_map.html", context)

# ---------------------------------------------------------------------
# 3. AJAX Data Views
# ---------------------------------------------------------------------

@staff_member_required
def load_sums(request):
    """AJAX-аар сум/дүүргийн жагсаалт авах"""
    # 1. Аймаг ID-г авах
    aimag_id = request.GET.get("aimag_id")

    # 2. Шүүлтүүр хийх
    if aimag_id and aimag_id.isdigit():
        # ТАНЫ МОДЕЛ ДЭЭР aimag_ref ГЭСЭН НЭРТЭЙ ТУЛ ҮҮНИЙГ АШИГЛАНА
        qs = SumDuureg.objects.filter(aimag_ref_id=int(aimag_id)).order_by("name")
    else:
        # Аймаг сонгогдоогүй бол хоосон жагсаалт буцаана
        return JsonResponse([], safe=False)

    # 3. Өгөгдлийг бэлтгэх (Зөвхөн id ба name)
    # Таны __str__ функц self.name буцааж байгаа тул 'code -' гэсэн бичиг арилна.
    data = [{"id": s.id, "name": s.name} for s in qs]
    
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})

@staff_member_required
@require_GET
def location_by_sum(request):
    """Сум сонгогдоход харьяа байршлуудыг JSON-оор буцаах"""
    sum_id = request.GET.get("sum_id")
    if not sum_id:
        return JsonResponse({"results": []})

    qs = _scope_location_qs(request).filter(sum_ref_id=sum_id).order_by("name")
    return JsonResponse({
        "results": [{"id": l.id, "text": l.name} for l in qs]
    })

# ---------------------------------------------------------------------
# 4. QR Code Public & Private Views
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
    """QR -> Staff хэрэглэгчийг Admin change page рүү чиглүүлнэ."""
    device = _qr_get_device_or_404(token)
    ok, msg = _qr_is_valid(device)
    if not ok:
        return HttpResponse(msg, status=410)

    url = reverse("admin:inventory_device_change", args=[device.pk])
    return redirect(url, permanent=False)

def qr_device_public_view(request, token):
    """Public read-only HTML view."""
    device = _qr_get_device_or_404(token)
    ok, msg = _qr_is_valid(device)
    if not ok:
        return HttpResponse(msg, status=410)

    serial = getattr(device, "serial_number", "") or "-"
    kind = getattr(device, "kind", "") or "-"
    status = getattr(device, "status", "") or "-"
    loc = getattr(getattr(device, "location", None), "name", "") or "-"

    try:
        pdf_url = reverse('qr_device_public_passport_pdf', args=[token])
    except:
        try:
            pdf_url = reverse('inventory:qr_device_public_passport_pdf', args=[token])
        except:
            pdf_url = "#"

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

    from inventory.pdf_passport import generate_device_passport_pdf_bytes
    pdf_bytes = generate_device_passport_pdf_bytes(device)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="device_passport_{device.pk}.pdf"'
    return resp

# ---------------------------------------------------------------------
# 5. Dashboard Visualization View
# ---------------------------------------------------------------------

@staff_member_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Dashboard-ийн статистик болон графикууд."""
    today = timezone.localdate()
    d30 = today + timedelta(days=30)
    d90 = today + timedelta(days=90)

    expired_q = Q(next_verification_date__lt=today)
    due_30_q = Q(next_verification_date__gte=today, next_verification_date__lte=d30)
    due_90_q = Q(next_verification_date__gt=d30, next_verification_date__lte=d90)
    unknown_q = Q(next_verification_date__isnull=True)
    valid_q = Q(next_verification_date__gt=d90)

    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status='Active').count()
    broken_devices = Device.objects.filter(status__in=['Broken', 'Repair']).count()
    
    calib_expired = Device.objects.filter(expired_q).count()
    calib_due_30 = Device.objects.filter(due_30_q).count()
    calib_due_90 = Device.objects.filter(due_90_q).count()
    calib_unknown = Device.objects.filter(unknown_q).count()
    calib_valid = Device.objects.filter(valid_q).count()

    status_stats = list(Device.objects.values('status').annotate(count=Count('id')))
    
    aimag_stats = list(
        Location.objects.filter(devices__status__in=['Broken', 'Repair'])
        .values(aimag_name=F('aimag_ref__name'))
        .annotate(broken_count=Count('devices'))
        .order_by('-broken_count')[:10]
    )

    calib_chart_data = [
        {'status': 'Expired', 'count': calib_expired},
        {'status': 'Due30', 'count': calib_due_30},
        {'status': 'Due90', 'count': calib_due_90},
        {'status': 'Valid', 'count': calib_valid},
        {'status': 'Unknown', 'count': calib_unknown},
    ]

    context = {
        'title': 'Багаж хэрэгслийн хяналтын самбар',
        'total_devices': total_devices,
        'active_devices': active_devices,
        'broken_devices': broken_devices,
        'calib_expired': calib_expired,
        'calib_due_30': calib_due_30,
        'calib_due_90': calib_due_90,
        'calib_unknown': calib_unknown,
        'calib_valid': calib_valid,
        'status_stats_json': json.dumps(status_stats, cls=DjangoJSONEncoder),
        'aimag_stats_json': json.dumps(aimag_stats, cls=DjangoJSONEncoder),
        'calib_stats_json': json.dumps(calib_chart_data, cls=DjangoJSONEncoder),
    }

    return render(request, "admin/dashboard_general.html", context)