import csv
import io
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from django.core.serializers.json import DjangoJSONEncoder

# Моделиудын импорт
from .models import Location, Aimag, Soum, Device

@staff_member_required
def device_import_csv(request):
    """CSV файлаас станцуудыг аймаг болон төрлөөр ангилан импортлох"""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        aimag_id = request.POST.get("aimag")
        loc_type = request.POST.get("location_type")

        if not csv_file:
            messages.error(request, 'CSV файл сонгоно уу.')
            return redirect(".")

        try:
            target_aimag = Aimag.objects.get(id=aimag_id)
            # Файлыг унших
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Гарчиг (header) алгасах

            created_count = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                # Файлын бүтэц: [0:aimag, 1:station_nam, 2:index, 3:lat, 4:lon, 5:hhh]
                if not row or len(row) < 5:
                    continue
                
                name = row[1].strip()
                wmo_idx = row[2].strip()
                lat = row[3].strip()
                lon = row[4].strip()
                elev = row[5].strip() if len(row) > 5 and row[5].strip() else 0

                # Станцын нэрийг Сум болгон бүртгэх
                soum_name = name.split('(')[0].strip()
                target_soum, _ = Soum.objects.get_or_create(
                    name=soum_name, 
                    aimag=target_aimag
                )

                # Өгөгдлийн санд үүсгэх эсвэл шинэчлэх
                Location.objects.update_or_create(
                    name=name,
                    defaults={
                        'wmo_index': wmo_idx,
                        'latitude': lat,
                        'longitude': lon,
                        'elevation': elev,
                        'location_type': loc_type,
                        'aimag_ref': target_aimag,
                        'soum_ref': target_soum,
                    }
                )
                created_count += 1
            
            messages.success(request, f'Амжилттай: {created_count} станц ({loc_type}) {target_aimag.name}-д бүртгэгдлээ.')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {e}')
        
        return redirect("admin:inventory_location_changelist")

    # GET хүсэлтээр аймаг болон төрлийн жагсаалтыг явуулна
    aimags = Aimag.objects.all().order_by('name')
    context = {
        'opts': Location._meta,
        'aimags': aimags,
        'location_types': [
            ('METEO', 'Цаг уурын өртөө (METEO)'),
            ('HYDRO', 'Ус судлалын харуул (HYDRO)'),
            ('AWS', 'Автомат станц (AWS)'),
        ]
    }
    return render(request, "admin/csv_form.html", context)

@staff_member_required
def location_map(request):
    """Газрын зураг дээр станцуудыг харуулах функц (AttributeError-оос сэргийлнэ)"""
    # Координаттай бүх байршлыг авах
    qs = Location.objects.exclude(latitude__isnull=True).select_related("aimag_ref").annotate(
        device_count=Count('devices')
    )
    
    points = []
    for loc in qs:
        points.append({
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "",
            "device_count": loc.device_count,
        })
        
    return render(request, "inventory/location_map.html", {
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder)
    })