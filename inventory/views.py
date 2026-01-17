import csv
import io
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Count
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder

from .models import Location, Device

@staff_member_required
def device_import_csv(request):
    """Багаж хэрэгслийг CSV файлаас бөөнөөр нь уншиж бүртгэх"""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        
        # Файлын төрлийг шалгах
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Зөвхөн .csv файл оруулна уу.')
            return redirect("..")

        try:
            # Файлыг уншиж бэлтгэх
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string) # Баганын нэрсийг алгасах

            created_count = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                # CSV-ийн бүтэц: нэр, серийн_дугаар, станцын_нэр
                if len(row) < 3: continue
                name, serial, loc_name = row
                
                # Станцыг нэрээр нь хайж олох
                location = Location.objects.filter(name=loc_name.strip()).first()
                
                # Серийн дугаараар нь шалгаж шинээр үүсгэх эсвэл шинэчлэх
                Device.objects.update_or_create(
                    serial_number=serial.strip(),
                    defaults={'name': name.strip(), 'location': location}
                )
                created_count += 1

            messages.success(request, f'Амжилттай: {created_count} багаж бүртгэгдлээ.')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {e}')
        
        return redirect("admin:inventory_device_changelist")

    # GET хүсэлт ирэхэд файл сонгох форм харуулна
    return render(request, "admin/csv_form.html", {'opts': Device._meta})

@staff_member_required
def location_map(request):
    """Станцуудыг газрын зураг дээр харуулах харагдац"""
    
    # Координаттай станцуудыг шүүж, аймаг болон төхөөрөмжийн тоог хамт татах
    qs = (
        Location.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("aimag_ref") # aimag_fk-г aimag_ref болгож зассан
        .annotate(device_count=Count('devices'))
    )

    points = []
    for loc in qs:
        # Модель дээр 'status' талбар байхгүй бол 'location_type'-оор орлуулна
        status_val = getattr(loc, 'status', loc.location_type) 

        points.append({
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "status": status_val,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "",
            "device_count": loc.device_count,
        })

    return render(request, "inventory/location_map.html", {
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder)
    })