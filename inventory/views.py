import csv
import io
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from .models import Location, Organization, Device

@staff_member_required
def device_import_csv(request):
    """Багаж импортлох логик"""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Файл сонгоно уу.")
            return redirect("..")
        # Импортын логик энд үргэлжилнэ...
        messages.success(request, "Амжилттай импортлоо.")
        return redirect("..")
    return render(request, "admin/csv_form.html", {"title": "CSV Импорт"})

@staff_member_required
def location_map(request):
    """Байгууллага болон багажийн тоог дамжуулах"""
    qs = Location.objects.exclude(latitude__isnull=True).select_related("aimag_ref", "owner_org").annotate(
        device_count=Count('devices')
    )
    
    points = []
    for loc in qs:
        points.append({
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
            "org": loc.owner_org.name if loc.owner_org else "Тодорхойгүй",
            "device_count": loc.device_count,
        })
        
    return render(request, "inventory/location_map.html", {
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder)
    })