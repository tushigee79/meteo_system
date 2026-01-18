import csv
import io
import json
import string
import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from .models import Location, Organization, Device, Aimag, MasterDevice, UserProfile

@staff_member_required
def download_retired_archive(request):
    """Ашиглалтаас хасагдсан багажнуудын архивыг CSV-ээр татах"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="retired_instruments_archive.csv"'
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response)
    writer.writerow(['Серийн дугаар', 'Төрөл/Загвар', 'Байршил', 'Хасагдсан огноо', 'Шалтгаан'])

    # Зөвхөн 'Retired' төлөвтэй багажнуудыг шүүнэ
    retired_devices = Device.objects.filter(status='Retired')

    for d in retired_devices:
        writer.writerow([
            d.serial_number, 
            str(d.master_device or d.other_device_name),
            str(d.location),
            getattr(d, 'retirement_date', '-'),
            getattr(d, 'retirement_reason', '-')
        ])
    return response

@staff_member_required
def import_engineers_from_csv(request):
    """Инженерүүдийг CSV-ээс уншиж, нэвтрэх эрх болон и-мэйл илгээх функц"""
    if request.method == "POST" and request.FILES.get("csv_file"):
        try:
            file_data = request.FILES["csv_file"].read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(file_data))
            
            for row in reader:
                email = row['Цахим хаяг']
                aimag_name = row['Аймаг/Нийслэл']
                full_name = row['Овог нэр']
                role = row.get('Үүрэг', 'AIMAG_ENG')
                
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                username = email.split('@')[0]
                
                user, created = User.objects.get_or_create(
                    email=email, 
                    defaults={'username': username, 'first_name': full_name}
                )
                user.set_password(temp_password)
                user.save()
                
                aimag_obj = Aimag.objects.filter(name=aimag_name).first()
                UserProfile.objects.update_or_create(
                    user=user, 
                    defaults={'aimag': aimag_obj, 'role': role}
                )
                
                subject = "ЦУОШГ: Системд нэвтрэх эрх олгогдлоо"
                message = (f"Сайн байна уу, {full_name}.\n\nТанд системийн нэвтрэх эрх олгогдлоо.\n\n"
                           f"Нэвтрэх нэр: {username}\nНэг удаагийн нууц үг: {temp_password}\n\n"
                           f"Та нэвтэрснийхээ дараа 'Тохиргоо' хэсэгт орж өөрийн нууц үгээ заавал шинэчлээрэй.")
                send_mail(subject, message, 'noreply@namem.gov.mn', [email])
                
            messages.success(request, "Инженерүүдийн бүртгэл амжилттай хийгдэж, и-мэйл илгээгдлээ.")
        except Exception as e:
            messages.error(request, f"Алдаа гарлаа: {str(e)}")
            
        return redirect("admin:auth_user_changelist")
    return render(request, "admin/csv_form.html", {"title": "Инженерүүд импортлох"})

@staff_member_required
def device_import_csv(request):
    """Багаж импортлох үндсэн функц"""
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Файл сонгоно уу.")
            return redirect("..")
        
        try:
            file_data = csv_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(file_data))
            
            for row in reader:
                # 1. Байршлыг салгаж авах (Аймаг - Сум - Станц)
                parts = row['Байршил (Аймаг - Сум - Станц)'].split(" - ")
                
                # 2. Тухайн байршлыг өгөгдлийн сангаас шүүж олох
                location = Location.objects.get(
                    aimag_ref__name=parts[0], 
                    sum_ref__name=parts[1], 
                    name=parts[2]
                )
                
                # 3. Багажны төрлийг (MasterDevice) нэрээр нь хайх
                master = MasterDevice.objects.filter(
                    name__icontains=row['Төрөл (Жагсаалтаас)']
                ).first()
                
                # 4. Багажийг үүсгэх эсвэл шинэчлэх
                Device.objects.update_or_create(
                    serial_number=row['Серийн дугаар'],
                    defaults={
                        'location': location,
                        'master_device': master,
                        'other_device_name': row['Бусад (Гараар бичих)'] if not master else '',
                        'status': row.get('Төлөв', 'Active'),
                        'installation_date': row.get('Суурилуулсан огноо') or None
                    }
                )
            messages.success(request, "Багаж хэрэгслийн жагсаалт амжилттай шинэчлэгдлээ.")
        except Exception as e:
            messages.error(request, f"Алдаа гарлаа: {str(e)}")
            
        return redirect("admin:inventory_device_changelist")
    return render(request, "admin/csv_form.html", {"title": "CSV Импорт"})

@staff_member_required
def download_aimag_template(request):
    """Аймгийн инженер зөвхөн өөрт зөвшөөрөгдсөн станцуудын жагсаалтыг татах"""
    response = HttpResponse(content_type='text/csv')
    aimag_obj = getattr(request.user.userprofile, 'aimag', None)
    aimag_name = aimag_obj.name if aimag_obj else "Template"
    
    response['Content-Disposition'] = f'attachment; filename="{aimag_name}_template.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow(['Байршил (Аймаг - Сум - Станц)', 'Төрөл (Жагсаалтаас)', 'Бусад (Гараар бичих)', 'Серийн дугаар', 'Төлөв', 'Суурилуулсан огноо'])

    if request.user.is_superuser or request.user.userprofile.role in ['NAMEM_HQ', 'LAB_RIC']:
        locations = Location.objects.all()
    else:
        locations = Location.objects.filter(aimag_ref=aimag_obj)

    for loc in locations:
        writer.writerow([f"{loc.aimag_ref.name} - {loc.sum_ref.name} - {loc.name}", '', '', '', 'Active', ''])
    return response

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
    """Улсын сүлжээний график тайлан"""
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(status='Active').count()
    broken_devices = Device.objects.filter(status__in=['Broken', 'Repair']).count()
    
    today = timezone.now().date()
    expired_count = sum(1 for d in Device.objects.all() if d.lifespan_expiry and d.lifespan_expiry < today)

    status_stats = list(Device.objects.values('status').annotate(count=Count('id')))
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