import csv
import io
import json
import string
import random
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin as dj_admin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest

from .models import (
    Location, Organization, Device, Aimag, SumDuureg,
    InstrumentCatalog, UserProfile
)

ADMIN_NS = "admin"


class _DummyModelAdminStub:
    # Django admin search_form expects these attributes
    search_fields = ()
    search_help_text = ""


class _DummyCL:
    """
    Minimal ChangeList stub so that Django admin template tags like
    {% search_form cl %} work without errors.
    """
    def __init__(self, opts, request=None, result_count=0, full_result_count=0):
        self.opts = opts
        self.request = request

        self.result_count = int(result_count or 0)
        self.full_result_count = int(full_result_count or 0)
        self.model_admin = _DummyModelAdminStub()

        # Attributes commonly accessed by admin templates
        self.query = ""
        self.params = {}
        self.is_popup = False
        self.show_result_count = (self.result_count != self.full_result_count)

    def get_query_string(self, new_params=None, remove=None):
        params = dict(getattr(self.request, "GET", {}) or {})
        new_params = new_params or {}
        remove = remove or []

        for k, v in new_params.items():
            params[k] = v
        for k in remove:
            params.pop(k, None)

        return "?" + urlencode(params, doseq=True) if params else ""


def _get_user_scope(request):
    """
    Scope тодорхойлох:
      - superuser => бүхнийг зөвшөөрнө
      - бусад => UserProfile.aimag дээр тулгуурлана
      - УБ (aimag_id==1) дээр UserProfile.sumduureg байвал дүүргээр шүүнэ
    """
    u = getattr(request, "user", None)
    if not u or getattr(u, "is_superuser", False):
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)
    sum_id = (
        getattr(prof, "sumduureg_id", None)
        or getattr(prof, "sum_ref_id", None)
        or getattr(prof, "district_id", None)
    )

    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}


@staff_member_required
def station_map_view(request):
    """Нэг байршлыг газрын зураг дээр харуулах (?id=...)"""
    loc_id = request.GET.get("id")

    if not loc_id:
        context = {
            **dj_admin.site.each_context(request),
            "title": "Газрын зураг (нэг цэг)",
            "opts": Location._meta,
                        "locations_json": "[]",
            "single": True,
        }
        return render(request, "inventory/location_map_one.html", context)

    scope = _get_user_scope(request)

    qs = Location.objects.select_related("aimag_ref", "sum_ref", "owner_org").annotate(device_count=Count("devices"))
    if not scope.get("all"):
        if scope.get("aimag_id"):
            qs = qs.filter(aimag_ref_id=scope["aimag_id"])
        if scope.get("aimag_id") == 1 and scope.get("sum_id"):
            qs = qs.filter(sum_ref_id=scope["sum_id"])

    loc = get_object_or_404(qs, id=loc_id)

    try:
        lat = float(loc.latitude)
        lon = float(loc.longitude)
    except Exception:
        lat, lon = None, None

    org = getattr(loc, "owner_org", None)
    org_name = getattr(org, "name", "") if org else ""

    loc_admin_url = ""
    org_admin_url = ""
    try:
        loc_admin_url = reverse(f"{ADMIN_NS}:inventory_location_change", args=[loc.id])
    except Exception:
        pass
    if org:
        try:
            org_admin_url = reverse(f"{ADMIN_NS}:inventory_organization_change", args=[org.id])
        except Exception:
            pass

    dev_list_url = ""
    try:
        dev_list_url = reverse(f"{ADMIN_NS}:inventory_device_changelist") + f"?location__id__exact={loc.id}"
    except Exception:
        pass

    code_val = getattr(loc, "code", "") or getattr(loc, "station_code", "") or ""
    wmo_val = getattr(loc, "wmo_code", "") or getattr(loc, "wmo", "") or ""

    sum_name = ""
    sum_obj = getattr(loc, "sum_ref", None)
    sum_name = getattr(sum_obj, "name", "") if sum_obj else ""

    point = [{
        "id": loc.id,
        "name": getattr(loc, "name", "") or "",
        "code": code_val,
        "wmo": wmo_val,
        "lat": lat,
        "lon": lon,
        "type": getattr(loc, "location_type", "") or "",
        "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
        "sum": sum_name,
        "org": org_name,
        "device_count": int(getattr(loc, "device_count", 0) or 0),
        "loc_admin_url": loc_admin_url,
        "org_admin_url": org_admin_url,
        "device_list_url": dev_list_url,
    }]

    context = {
        **dj_admin.site.each_context(request),
        "title": "Газрын зураг (нэг цэг)",
        "opts": Location._meta,
                "locations_json": json.dumps(point, cls=DjangoJSONEncoder),
        "single": True,
    }

    return render(request, "inventory/location_map_one.html", context)


# inventory/views.py

@staff_member_required
def location_map(request):
    """Бүх станцыг нэгдсэн газрын зураг дээр төлөвөөр нь ялгаж харуулах"""
    scope = _get_user_scope(request) # Таны өмнөх scope логик

    # Coordinate-той бүх байршлыг төхөөрөмжүүдтэй нь хамт унших
    qs = (
        Location.objects
        .exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        .select_related("aimag_ref", "sum_ref", "owner_org")
        .prefetch_related("devices")
    )

    if not scope.get("all"):
        if scope.get("aimag_id"):
            qs = qs.filter(aimag_ref_id=scope["aimag_id"])

    points = []
    for loc in qs:
        try:
            lat, lon = float(loc.latitude), float(loc.longitude)
        except (TypeError, ValueError):
            continue

        # Станцын төлөвийг тодорхойлох логик
        devs = loc.devices.all()
        status_color = "green" # Хэвийн
        if devs.filter(status__in=["Broken", "Repair"]).exists():
            status_color = "red"   # Эвдрэлтэй
        elif devs.count() == 0:
            status_color = "gray"  # Багажгүй

        points.append({
            "id": loc.id,
            "name": loc.name,
            "lat": lat,
            "lon": lon,
            "color": status_color, # Өнгөөр ялгах талбар
            "type": loc.location_type,
            "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
            "device_count": devs.count(),
            "loc_admin_url": reverse(f"{ADMIN_NS}:inventory_location_change", args=[loc.id]),
            "device_list_url": reverse(f"{ADMIN_NS}:inventory_device_changelist") + f"?location__id__exact={loc.id}"
        })

    context = {
        **dj_admin.site.each_context(request),
        "title": "Улсын сүлжээний интерактив зураглал",
        "locations_json": json.dumps(points, cls=DjangoJSONEncoder),
    }
    return render(request, "inventory/location_map.html", context)

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


@require_GET
def api_sum_duureg(request):
    """
    Sum/Duureg жагсаалт (Аймаг/Нийслэлээр шүүж JSON буцаана)
    GET: ?aimag_id=<id>
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
        pass

    return JsonResponse({"ok": True, "items": [{"id": s.id, "name": s.name} for s in qs]})


@require_GET
def api_catalog_items(request):
    """
    ДЦУБ каталогийг төрлөөр нь шүүж JSON буцаана
    GET: ?kind=ETALON|WEATHER|HYDRO|RADAR|AEROLOGY|AWS|AGRO|OTHER
    """
    kind = (request.GET.get("kind") or "").strip()

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


@staff_member_required
def admin_data_entry(request: HttpRequest):
    if not request.user.has_perm("auth.view_user"):
        raise PermissionDenied("Admin only")

    context = {
        "title": "Өгөгдөл бүртгэх (Админ)",
        "cards": [
            ("Аймаг/Нийслэл", "/django-admin/inventory/aimag/", "fas fa-city"),
            ("Сум/Дүүрэг", "/django-admin/inventory/sumduureg/", "fas fa-map"),
            ("Байгууллагууд", "/django-admin/inventory/organization/", "fas fa-building"),
            ("Байршил", "/django-admin/inventory/location/", "fas fa-map-marker-alt"),
            ("ДЦУБ каталог", "/django-admin/inventory/instrumentcatalog/", "fas fa-book"),
            ("Хэмжих хэрэгсэл", "/django-admin/inventory/device/", "fas fa-tools"),
            ("Засвар, үйлчилгээ", "/django-admin/inventory/maintenanceservice/", "fas fa-wrench"),
            ("Хяналт, тохируулга", "/django-admin/inventory/controladjustment/", "fas fa-sliders-h"),
            ("Хэрэглэгчид", "/django-admin/auth/user/", "fas fa-user"),
            ("Бүлгүүд", "/django-admin/auth/group/", "fas fa-users"),
        ],
    }
    return render(request, "admin/data_entry.html", context)
