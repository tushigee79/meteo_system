import csv
import io
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import Location, Organization, Device, Aimag

@staff_member_required
def device_import_csv(request):
    """Багаж импортлох функц"""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Файл сонгоно уу.")
            return redirect("..")
        # Импортлох логик энд бичигдэнэ
        messages.success(request, "Амжилттай импортлоо.")
        return redirect("..")
    return render(request, "admin/csv_form.html", {"title": "CSV Импорт"})

@staff_member_required
def location_map(request):
    """Газрын зураг руу өгөгдөл дамжуулах"""
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

@staff_member_required
def national_dashboard(request):
    """Улсын сүлжээний багаж, хэмжих хэрэгслийн бэлэн байдлын график тайлан"""
    # 1. Ерөнхий статистик тоо
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status='Active').count()
    broken_devices = Device.objects.filter(status__in=['Broken', 'Repair']).count()
    
    # 2. Ашиглалтын хугацаа (Lifespan) дууссан багажнууд
    today = timezone.now().date()
    expired_count = 0
    devices = Device.objects.all()
    for d in devices:
        if d.lifespan_expiry and d.lifespan_expiry < today:
            expired_count += 1

    # 3. График 1: Төлөвийн харьцаа (Pie Chart өгөгдөл)
    status_stats = list(Device.objects.values('status').annotate(count=Count('id')))

    # 4. График 2: Аймгуудын эвдрэлийн тоо (Bar Chart өгөгдөл)
    # Хамгийн их эвдрэлтэй 10 аймгийг шүүнэ
    aimag_stats = list(Aimag.objects.annotate(
        broken_count=Count('location__devices', filter=Q(location__devices__status='Broken'))
    ).filter(broken_count__gt=0).order_by('-broken_count')[:10].values('name', 'broken_count'))

    context = {
        'title': "Улсын сүлжээний багаж, хэмжих хэрэгслийн бэлэн байдлын график тайлан",
        'total_devices': total_devices,
        'active_devices': active_devices,
        'broken_devices': broken_devices,
        'expired_count': expired_count,
        'status_stats_json': json.dumps(status_stats, cls=DjangoJSONEncoder),
        'aimag_stats_json': json.dumps(aimag_stats, cls=DjangoJSONEncoder),
    }
    return render(request, 'inventory/dashboard.html', context)