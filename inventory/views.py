from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import HttpResponse
import json
from django.core.serializers.json import DjangoJSONEncoder

from .models import Location, Device


@staff_member_required
def device_import_csv(request):
    return HttpResponse("Device CSV import page (TODO)")


@staff_member_required
def location_map(request):
    qs = (
        Location.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("aimag_fk")
    )

    points = []
    for loc in qs:
        device_count = Device.objects.filter(location=loc).count()

        points.append({
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "status": loc.status,
            "aimag": loc.aimag_fk.name if loc.aimag_fk else "",
            "device_count": device_count,
        })

    return render(request, "inventory/location_map.html", {
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder)
    })
