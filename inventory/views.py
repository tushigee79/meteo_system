from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Count
import json
from django.core.serializers.json import DjangoJSONEncoder

from .models import Location, Device

@staff_member_required
def device_import_csv(request):
    """Багаж хэрэгслийг CSV-ээр импортлох хуудас"""
    return HttpResponse("Device CSV import page (TODO)")

@staff_member_required
def location_map(request):
    """Станцуудыг газрын зураг дээр харуулах харагдац"""
    
    # 'aimag_fk' -> 'aimag_ref' болгож засав
    # 'status' талбар байхгүй бол 'location_type'-оор орлуулж болно
    qs = (
        Location.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("aimag_ref") # Зассан нэр
        .annotate(device_count=Count('devices')) # Төхөөрөмжийн тоог шууд тоолно
    )

    points = []
    for loc in qs:
        # Модель дээр 'status' талбар байхгүй бол loc.location_type ашиглана
        status_val = getattr(loc, 'status', loc.location_type) 

        points.append({
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "status": status_val,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "", # Зассан нэр
            "device_count": loc.device_count,
        })

    return render(request, "inventory/location_map.html", {
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder)
    })