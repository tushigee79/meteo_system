# inventory/views_district_api.py
from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .geo.district_lookup import lookup_ub_district


@require_GET
def lookup_district_api(request):
    """
    GET /api/geo/lookup-district/?lat=...&lon=...
    Response:
      { ok: true, district: "Баянзүрх", sum_code: 101, ... }
    """
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")

    if lat is None or lon is None:
        return JsonResponse({"ok": False, "error": "lat and lon are required"}, status=400)

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except ValueError:
        return JsonResponse({"ok": False, "error": "lat/lon must be numbers"}, status=400)

    props = lookup_ub_district(lon_f, lat_f, base_dir=settings.BASE_DIR)
    if not props:
        return JsonResponse({"ok": True, "found": False})

    return JsonResponse(
        {
            "ok": True,
            "found": True,
            "district": props.get("name_mn"),
            "name_mn": props.get("name_mn"),
            "name_en": props.get("name_en"),
            "aimag_code": props.get("aimag_code"),
            "sum_code": props.get("sum_code"),
        }
    )