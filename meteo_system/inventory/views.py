from __future__ import annotations

import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Max, F
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.utils import timezone

from .models import SumDuureg, Location, InstrumentCatalog

from inventory.models import Location, SumDuureg, Device


def _json_ok(payload):
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


def _get_int_param(request, *keys):
    for key in keys:
        raw = (request.GET.get(key) or "").strip()
        if raw:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
    return None


def _get_str_param(request, *keys):
    for key in keys:
        raw = (request.GET.get(key) or "").strip()
        if raw:
            return raw
    return ""


@staff_member_required
def admin_data_entry(request: HttpRequest) -> HttpResponse:
    return redirect("/django-admin/", permanent=False)


@staff_member_required
def station_map_view(request):
    return location_map(request)


@staff_member_required
def location_map(request, location_id: int | None = None):
    def _p(*keys: str) -> str:
        for k in keys:
            v = (request.GET.get(k) or "").strip()
            if v:
                return v
        return ""

    def _int(s: str) -> int | None:
        try:
            return int(s)
        except Exception:
            return None

    def _norm(s: str) -> str:
        return (s or "").strip()

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

    aimag = _int(_p("aimag", "aimag_ref__id__exact", "aimag_ref_id"))
    sum_id = _int(_p("sum", "sum_ref__id__exact", "sum_ref_id", "sumduureg"))
    district = _p("district", "district_name", "district_name__exact")
    location_type = _norm(_p("location_type", "location_type__exact", "loc_type"))
    kind = _norm(_p("kind", "device_kind"))
    status = _p("status", "device_status")

    qs = Location.objects.select_related("aimag_ref", "sum_ref", "owner_org").all()

    if aimag:
        qs = qs.filter(aimag_ref_id=aimag)
    if sum_id:
        qs = qs.filter(sum_ref_id=sum_id)
    if district:
        qs = qs.filter(district_name__iexact=district)
    if location_type:
        qs = qs.filter(location_type__iexact=location_type)
    if kind:
        qs = qs.filter(devices__kind__iexact=kind)
    if status:
        qs = qs.filter(devices__status=status)

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
        if (r.get("device_count") or 0) <= 0:
            st = "Багажгүй"
        elif (r.get("any_broken") or 0) > 0:
            st = "Эвдрэлтэй"
        else:
            st = "Хэвийн"
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


@staff_member_required
def load_sums(request):
    """Аймгийн ID-аар сумдын жагсаалтыг JSON-оор буцаана."""
    # GET хүсэлтээс ирж болох бүх боломжит түлхүүр үгсийг шалгах
    aimag_id = (
        request.GET.get("aimag_id")
        or request.GET.get("aimag")
        or request.GET.get("aimag_ref")
        or ""
    ).strip()

    # Сумдыг нэрээр нь эрэмбэлж авах
    qs = SumDuureg.objects.all().order_by("name")
    
    # Хэрэв аймгийн ID ирсэн бол шүүлтүүр хийх
    if aimag_id:
        qs = qs.filter(aimag_id=aimag_id)

    # Жагсаалтыг dict хэлбэрт оруулах (дээд тал нь 5000 мөр)
    rows = [{"id": s.id, "name": s.name} for s in qs[:5000]]

    return JsonResponse(
        {
            "results": rows,  # Select2 болон шинэ JS-д зориулсан
            "sums": rows,     # Хуучин JS-д зориулсан
        },
        json_dumps_params={"ensure_ascii": False},
    )

@staff_member_required
def location_options(request):
    aimag_id = (
        request.GET.get("aimag_id")
        or request.GET.get("aimag")
        or request.GET.get("aimag_ref")
        or ""
    ).strip()

    sum_id = (
        request.GET.get("sum_id")
        or request.GET.get("sum")
        or request.GET.get("sum_ref")
        or ""
    ).strip()

    
    kind = (request.GET.get("kind") or "").strip().upper()

    # Сум сонгогдоогүй бол location бүү буцаа
    if not sum_id:
        return JsonResponse(
            {"results": [], "locations": []},
            json_dumps_params={"ensure_ascii": False},
        )

    qs = Location.objects.select_related("aimag_ref", "sum_ref").all()

    if aimag_id:
        qs = qs.filter(aimag_ref_id=aimag_id)

    qs = qs.filter(sum_ref_id=sum_id)

    if kind:
        kind_to_location_type = {
            "AWS": ["AWS"],
            "WEATHER": ["WEATHER"],
            "HYDRO": ["HYDRO"],
            "RADAR": ["RADAR"],
            "AEROLOGY": ["AEROLOGY"],
            "AGRO": ["AGRO"],
            "ETALON": ["ETALON"],
            "OTHER": ["OTHER"],
        }
        allowed = kind_to_location_type.get(kind, [kind])
        qs = qs.filter(location_type__in=allowed)

    qs = qs.order_by("name")[:5000]

    rows = [
        {
            "id": x.id,
            "name": x.name,
            "text": x.name,
            "aimag_id": x.aimag_ref_id,
            "sum_id": x.sum_ref_id,
            "location_type": x.location_type,
        }
        for x in qs
    ]

    return JsonResponse(
        {"results": rows, "locations": rows},
        json_dumps_params={"ensure_ascii": False},
    )


@staff_member_required
def catalog_by_kind(request):
    kind = (request.GET.get("kind") or "").strip().upper()
    print("catalog_by_kind kind =", repr(kind))

    qs = InstrumentCatalog.objects.all().order_by("name_mn")
    print("ALL =", qs.count())

    if kind:
        qs = qs.filter(kind=kind)

    print("FILTERED =", qs.count())

    rows = [
        {
            "id": x.id,
            "name": x.name_mn,
            "text": x.name_mn,
            "code": x.code,
            "unit": x.unit,
        }
        for x in qs[:5000]
    ]

    return JsonResponse(
        {"results": rows},
        json_dumps_params={"ensure_ascii": False},
    )


@staff_member_required
def location_by_sum(request):
    request.GET = request.GET.copy()

    sum_id = _get_int_param(request, "sum_id", "sum", "sum_ref")
    aimag_id = _get_int_param(request, "aimag_id", "aimag", "aimag_ref")
    kind = _get_str_param(request, "kind")

    if sum_id is not None:
        request.GET["sum_id"] = str(sum_id)
    if aimag_id is not None:
        request.GET["aimag_id"] = str(aimag_id)
    if kind:
        request.GET["kind"] = kind

    return location_options(request)

def qr_device_lookup(request, token):
    device = get_object_or_404(Device, token=token)
    return render(request, "inventory/qr_device_detail.html", {"device": device})

def qr_device_public_view(request, token):
    device = get_object_or_404(Device, token=token)
    return render(request, "inventory/qr_public.html", {"device": device})

def qr_device_public_passport_pdf(request, token):
    # Энэ функц нь паспорт PDF-ийг татаж авах эсвэл харуулах зориулалттай
    device = get_object_or_404(Device, token=token)
    
    # Хэрэв танд PDF үүсгэх бэлэн код байхгүй бол одоогоор туршилтын байдлаар
    # зүгээр л текст буцааж болох юм. 
    return HttpResponse(f"{device.name} төхөөрөмжийн паспорт PDF удахгүй орно.")

# inventory/views.py файлын төгсгөлд нэмэх

@staff_member_required
def catalog_by_kind(request):
    """
    Төхөөрөмжийн төрлөөр каталог шүүж харуулах (AJAX)
    """
    kind = request.GET.get('kind', '')
    # Энд өөрийн логикоор Device-ээ шүүж буцаана
    return JsonResponse({"results": []})

def qr_device_public_passport_pdf(request, token):
    """
    Төхөөрөмжийн паспортыг PDF-ээр харуулах
    """
    device = get_object_or_404(Device, token=token)
    return HttpResponse(f"{device.name} - Паспорт бэлтгэгдэж байна.", content_type="text/plain")