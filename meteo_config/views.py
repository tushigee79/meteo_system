from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.core.serializers.json import DjangoJSONEncoder
import json

from inventory.models import Location, SumDuureg


@staff_member_required
def station_map_view(request):
    """Зөвхөн 1 Location (сонгосон цэг) map дээр харуулна"""
    loc_id = request.GET.get("id")
    if not loc_id:
        return render(
            request,
            "inventory/location_map_one.html",
            {"locations_json": "[]", "single": True}
        )

    loc = get_object_or_404(
        Location.objects
        .select_related("aimag_ref")
        .annotate(device_count=Count("devices")),
        id=loc_id
    )

    point = [{
        "id": loc.id,
        "name": loc.name,
        "lat": float(loc.latitude),
        "lon": float(loc.longitude),
        "type": loc.location_type,
        "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
        "device_count": int(loc.device_count or 0),
    }]

    return render(
        request,
        "inventory/location_map_one.html",
        {
            "locations_json": json.dumps(point, cls=DjangoJSONEncoder),
            "single": True
        }
    )


@staff_member_required
def api_sum_duureg(request):
    """
    GET /api/sum-duureg/?aimag_id=<id>
    return: {"ok": true, "items": [{id, name}, ...]}
    """
    aimag_id = (request.GET.get("aimag_id") or "").strip()
    if not aimag_id.isdigit():
        return JsonResponse({"ok": True, "items": []})

    qs = SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")
    items = [{"id": s.id, "name": getattr(s, "name", str(s))} for s in qs]

    return JsonResponse({"ok": True, "items": items})
@staff_member_required
def api_catalog_items(request):
    """
    GET /api/catalog/?kind=<KIND>
    return: {"ok": true, "items": [{id, name, code}, ...]}
    """
    kind = (request.GET.get("kind") or "").strip()

    # ⚠️ Танай InstrumentCatalog inventory.models дотор байдаг гэж үзэв
    from inventory.models import InstrumentCatalog

    qs = InstrumentCatalog.objects.all()

    if kind:
        # kind field чинь яг ямар нэртэйгээс хамаарч filter-ийг тааруулна
        # Ихэнхдээ: kind эсвэл instrument_kind байдаг
        if hasattr(InstrumentCatalog, "kind"):
            qs = qs.filter(kind=kind)
        elif hasattr(InstrumentCatalog, "instrument_kind"):
            qs = qs.filter(instrument_kind=kind)

    # боломжит нэрийн талбарууд (name_mn / name / title гэх мэт) дээр уян хатан
    items = []
    for it in qs.order_by("id")[:2000]:
        name = getattr(it, "name_mn", None) or getattr(it, "name", None) or getattr(it, "title", None) or str(it)
        items.append({
            "id": it.id,
            "name": name,
            "code": getattr(it, "code", ""),
        })

    return JsonResponse({"ok": True, "items": items})
# backward-compatible alias (urls.py дээр views.location_map гэж дууддаг байсныг дэмжинэ)
location_map = station_map_view
@staff_member_required
def location_map(request, location_id=None):
    """
    /map/  (query param: ?id=<id>)
    /map/location/<int:location_id>/  (path param)
    -> ганц Location-г location_map_one.html дээр харуулна
    """
    loc_id = location_id or request.GET.get("id")
    if not loc_id:
        return render(
            request,
            "inventory/location_map_one.html",
            {"locations_json": "[]", "single": True}
        )

    loc = get_object_or_404(
        Location.objects
        .select_related("aimag_ref")
        .annotate(device_count=Count("devices")),
        id=loc_id
    )

    point = [{
        "id": loc.id,
        "name": loc.name,
        "lat": float(loc.latitude),
        "lon": float(loc.longitude),
        "type": loc.location_type,
        "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
        "device_count": int(loc.device_count or 0),
    }]

    return render(
        request,
        "inventory/location_map_one.html",
        {
            "locations_json": json.dumps(point, cls=DjangoJSONEncoder),
            "single": True
        }
    )

# (Optional) хуучин нэршлээр station_map_view-ээр дуудсан байвал эвдэхгүй
station_map_view = location_map
# ---------------------------
# CSV import (stub)
# ---------------------------
@staff_member_required
def device_import_csv(request):
    """
    Түр placeholder.
    Дараа нь бодит CSV import логик хийнэ.
    """
    return JsonResponse({
        "ok": False,
        "error": "device_import_csv is not implemented yet"
    }, status=501)

# ---------------------------
# Dashboard (stub)
# ---------------------------
@staff_member_required
def dashboard_cards(request):
    """
    Түр dashboard placeholder.
    """
    return render(request, "inventory/dashboard.html", {
        "ok": True,
        "cards": []
    })
