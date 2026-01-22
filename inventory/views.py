import csv
import io
import json
import string
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction

from .models import (
    Location, Organization, Device, Aimag, SumDuureg,
    InstrumentCatalog, UserProfile
)

# ✅ Админ панелийн нэрсийн орон зай (Namespace)
ADMIN_NS = "admin"  # хэрэв өөрчилсөн бол 'burtgel_admin' гэх мэт болгоно


# -----------------------------
# ГАЗРЫН ЗУРГИЙН ФУНКЦҮҮД
# -----------------------------

@staff_member_required
def station_map_view(request):
    """Нэг байршлыг газрын зураг дээр харуулах (?id=...)"""
    loc_id = request.GET.get("id")
    if not loc_id:
        return render(request, "inventory/location_map_one.html", {"locations_json": "[]"})

    loc = get_object_or_404(
        Location.objects.select_related("aimag_ref").annotate(device_count=Count("devices")),
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

    return render(request, "inventory/location_map_one.html", {
        "locations_json": json.dumps(point, cls=DjangoJSONEncoder)
    })


@staff_member_required
def location_map(request):
    """Бүх станцыг нэгдсэн газрын зураг дээр харуулах"""
    qs = (
        Location.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("aimag_ref")
        .annotate(device_count=Count("devices"))
    )

    points = []
    for loc in qs:
        points.append({
            "id": loc.id,
            "name": loc.name,
            "lat": float(loc.latitude),
            "lon": float(loc.longitude),
            "type": loc.location_type,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
            "device_count": int(loc.device_count or 0),
        })

    return render(
        request,
        "inventory/location_map.html",
        {"locations_json": json.dumps(points, cls=DjangoJSONEncoder)}
    )


# -----------------------------
# CSV ИМПОРТ / ЭКСПОРТ
# -----------------------------

@staff_member_required
def device_import_csv(request):
    """Багаж хэрэгслийг CSV-ээс импортлох"""
    if request.method == "POST" and request.FILES.get("csv_file"):
        try:
            file_data = request.FILES["csv_file"].read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(file_data))
            success_count = 0

            with transaction.atomic():
                for row in reader:
                    parts = row.get("Байршил (Аймаг - Сум - Станц)", "").split(" - ")
                    loc_obj = Location.objects.filter(name=parts[-1].strip()).first() if parts else None
                    if not loc_obj:
                        continue

                    Device.objects.update_or_create(
                        serial_number=row.get("serial_number") or row.get("Серийн дугаар"),
                        defaults={
                            "location": loc_obj,
                            "status": row.get("status") or row.get("Төлөв", "Active"),
                            "installation_date": row.get("installation_date") or row.get("Суурилуулсан огноо") or None,
                        },
                    )
                    success_count += 1

            messages.success(request, f"Амжилттай: {success_count} багаж бүртгэгдлээ.")
        except Exception as e:
            messages.error(request, f"Алдаа: {str(e)}")

        return redirect(f"{ADMIN_NS}:inventory_device_changelist")

    return render(request, "admin/inventory/device/import_csv.html")


@staff_member_required
def download_aimag_template(request):
    """CSV Загвар татах (Төв газар болон Аймгийн инженерүүдэд)"""
    response = HttpResponse(content_type="text/csv")
    profile = getattr(request.user, "profile", None)
    aimag_obj = getattr(profile, "aimag", None)
    aimag_name = aimag_obj.name if aimag_obj else "Template"
    response["Content-Disposition"] = f'attachment; filename="{aimag_name}_template.csv"'
    response.write(u"\ufeff".encode("utf8"))

    writer = csv.writer(response)
    writer.writerow([
        "Байршил (Аймаг - Сум - Станц)",
        "Төрөл (Жагсаалтаас)",
        "Бусад",
        "Серийн дугаар",
        "Төлөв",
        "Суурилуулсан огноо",
    ])
    return response


@staff_member_required
def download_retired_archive(request):
    """Хасагдсан багажнуудын архив татах"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="retired_archive.csv"'
    response.write(u"\ufeff".encode("utf8"))

    writer = csv.writer(response)
    writer.writerow(["Серийн дугаар", "Байршил", "Хасагдсан огноо", "Шалтгаан"])
    for d in Device.objects.filter(status="Retired"):
        writer.writerow([
            d.serial_number,
            str(d.location),
            getattr(d, "retirement_date", "-"),
            getattr(d, "retirement_reason", "-"),
        ])
    return response


# =========================
# API: Dependent dropdowns
# =========================

@require_GET
def api_sum_duureg(request):
    """
    Sum/Duureg жагсаалт (Аймаг/Нийслэлээр шүүж JSON буцаана)
    GET: ?aimag_id=<id>

    - aimag.name == "Улаанбаатар" => is_ub_district=True (9 дүүрэг)
    - бусад => is_ub_district=False (сумууд)
    """
    aimag_id = request.GET.get("aimag_id")
    if not aimag_id:
        return JsonResponse({"ok": False, "items": []})

    qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name")

    try:
        aimag = Aimag.objects.filter(id=aimag_id).first()
        if aimag and (aimag.name or "").strip() == "Улаанбаатар":
            qs = qs.filter(is_ub_district=True)
        else:
            qs = qs.filter(is_ub_district=False)
    except Exception:
        # field/өгөгдлийн асуудлаас болж API эвдрүүлэхгүй
        pass

    return JsonResponse({"ok": True, "items": [{"id": s.id, "name": s.name} for s in qs]})


@require_GET
def api_catalog_items(request):
    """
    ДЦУБ каталогийг төрлөөр нь шүүж JSON буцаана
    GET: ?kind=ETALON|DEVICE|RADAR|AEROLOGY|AWS|OTHER
    """
    kind = (request.GET.get("kind") or "").strip()

    # OTHER бол жагсаалт шаардахгүй (гараар нэр бичнэ)
    if not kind or kind == "OTHER":
        return JsonResponse({"ok": True, "items": []})

    qs = InstrumentCatalog.objects.filter(kind=kind)

    if hasattr(InstrumentCatalog, "is_active"):
        qs = qs.filter(is_active=True)

    if hasattr(InstrumentCatalog, "sort_order"):
        qs = qs.order_by("sort_order", "name_mn" if hasattr(InstrumentCatalog, "name_mn") else "id")
    else:
        qs = qs.order_by("name_mn" if hasattr(InstrumentCatalog, "name_mn") else "id")

    name_field = "name_mn" if hasattr(InstrumentCatalog, "name_mn") else "name"
    items = [{"id": c.id, "name": getattr(c, name_field, str(c))} for c in qs]
    return JsonResponse({"ok": True, "items": items})

