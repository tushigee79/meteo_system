# inventory/admin.py
import csv
import json

from django import forms
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.timezone import now

from .models import (
    Aimag,
    AuthAuditLog,
    Device,
    InstrumentCatalog,
    Location,
    Organization,
    SparePartItem,
    SparePartOrder,
    SumDuureg,
    UserProfile,
)

# ============================================================
# ✅ Instrument Catalog
# ============================================================
@admin.register(InstrumentCatalog)
class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("kind", "code", "name_mn", "unit", "is_active", "sort_order")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("sort_order", "kind", "name_mn")


# ============================================================
# ✅ Aimag / SumDuureg
# ============================================================
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag", "code", "is_ub_district")
    list_filter = ("aimag", "is_ub_district")
    search_fields = ("name", "code", "aimag__name")
    autocomplete_fields = ("aimag",)
    ordering = ("aimag__name", "name")


# ============================================================
# ✅ Organization
# ============================================================
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "aimag", "is_ub")
    list_filter = ("org_type", "aimag", "is_ub")
    search_fields = ("name", "aimag__name")
    autocomplete_fields = ("aimag",)
    ordering = ("name",)


# ============================================================
# ✅ Location Admin (map one + cascade + template)
# ============================================================
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location_type",
        "aimag_ref",
        "sum_ref",
        "wmo_index",
        "district_name",
        "owner_org",
        "latitude",
        "longitude",
        "view_map_link",
    )
    list_filter = ("location_type", "aimag_ref", "sum_ref", "owner_org")
    search_fields = ("name", "wmo_index", "district_name")
    autocomplete_fields = ("aimag_ref", "sum_ref", "owner_org")
    ordering = ("aimag_ref__name", "name")

    # ✅ “Харах” линк
    def view_map_link(self, obj):
        url = reverse("admin:inventory_location_location_map_one", args=[obj.pk])
        return format_html('<a class="button" href="{}">Харах</a>', url)

    view_map_link.short_description = "Харах"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/map/",
                self.admin_site.admin_view(self.location_map_one),
                name="inventory_location_location_map_one",
            ),
            path(
                "sums-by-aimag/",
                self.admin_site.admin_view(self.sums_by_aimag),
                name="location_sums_by_aimag",
            ),
            path(
                "locations-by-sum/",
                self.admin_site.admin_view(self.locations_by_sum),
                name="location_locations_by_sum",
            ),
            path(
                "download-aimag-template/",
                self.admin_site.admin_view(self.download_aimag_template),
                name="download_aimag_template",
            ),
        ]
        return custom + urls

    def sums_by_aimag(self, request):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        q = (request.GET.get("q") or "").strip()

        if not aimag_id.isdigit():
            return JsonResponse({"results": []})

        aimag = Aimag.objects.filter(id=int(aimag_id)).first()
        if not aimag:
            return JsonResponse({"results": []})

        qs = SumDuureg.objects.filter(aimag=aimag)

        # ✅ Улаанбаатар бол зөвхөн 9 дүүрэг
        if (aimag.name or "").strip() == "Улаанбаатар":
            qs = qs.filter(is_ub_district=True)

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

        qs = qs.order_by("name")[:200]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

    def locations_by_sum(self, request):
        sum_id = (request.GET.get("sum_id") or "").strip()
        q = (request.GET.get("q") or "").strip()

        if not sum_id.isdigit():
            return JsonResponse({"results": []})

        qs = Location.objects.filter(sum_ref_id=int(sum_id))

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(wmo_index__icontains=q))

        qs = qs.order_by("name")[:200]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

    def download_aimag_template(self, request):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="aimag_template.csv"'
        resp.write("\ufeff")
        w = csv.writer(resp)
        w.writerow(["aimag", "sum", "code"])
        w.writerow(["Улаанбаатар", "Баянзүрх", ""])
        return resp

    # ✅ Нэг байршлын map view
    def location_map_one(self, request, pk: int):
        loc = Location.objects.filter(pk=pk).first()
        if not loc:
            return HttpResponse("Location not found", status=404)

        device_count = Device.objects.filter(location=loc).count()

        points = []
        if loc.latitude is not None and loc.longitude is not None:
            try:
                points.append(
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "aimag": str(loc.aimag_ref),
                        "type": loc.location_type,
                        "lat": float(loc.latitude),
                        "lon": float(loc.longitude),
                        "device_count": device_count,
                    }
                )
            except Exception:
                pass

        ctx = dict(
            self.admin_site.each_context(request),
            title=f"Байршил газрын зураг: {loc.name}",
            locations_json=json.dumps(points, ensure_ascii=False),
        )
        return TemplateResponse(
            request,
            "admin/inventory/location/location_map_one.html",
            ctx,
        )

    class Media:
        js = (
            "inventory/js/admin/location_cascade.js",
        )


# ============================================================
# ✅ Device (kind -> catalog filter + location cascade + CSV export)
# ============================================================
class DeviceAdminForm(forms.ModelForm):
    aimag = forms.ModelChoiceField(
        queryset=Aimag.objects.all().order_by("name"),
        required=False,
        label="Аймаг/Нийслэл",
    )
    sumduureg = forms.ModelChoiceField(
        queryset=SumDuureg.objects.none(),
        required=False,
        label="Сум/Дүүрэг",
    )

    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initial aimag/sum from existing location
        loc = getattr(self.instance, "location", None)
        if loc and getattr(loc, "aimag_ref", None):
            self.fields["aimag"].initial = loc.aimag_ref
            qs = SumDuureg.objects.filter(aimag=loc.aimag_ref).order_by("name")
            if (loc.aimag_ref.name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            self.fields["sumduureg"].queryset = qs
            if getattr(loc, "sum_ref", None):
                self.fields["sumduureg"].initial = loc.sum_ref

        # if POST, set sumduureg queryset by posted aimag
        aimag_id = (self.data.get("aimag") or "").strip()
        if aimag_id.isdigit():
            qs = SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")
            aimag_name = Aimag.objects.filter(id=int(aimag_id)).values_list("name", flat=True).first() or ""
            if (aimag_name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            self.fields["sumduureg"].queryset = qs

        # catalog_item queryset filter by kind (initial render)
        kind = (self.data.get("kind") or "").strip() or getattr(self.instance, "kind", None)
        if "catalog_item" in self.fields:
            qs = InstrumentCatalog.objects.all()
            if kind:
                qs = qs.filter(kind=kind)
            self.fields["catalog_item"].queryset = qs.order_by("sort_order", "name_mn")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm

    fieldsets = (
        (None, {"fields": ("serial_number", "kind", "catalog_item", "other_name")}),
        ("Байршил", {"fields": ("aimag", "sumduureg", "location")}),
        ("Бусад", {"fields": ("status", "installation_date", "lifespan_years")}),
    )

    list_display = (
        "serial_number",
        "kind",
        "catalog_item",
        "other_name",
        "location",
        "status",
        "installation_date",
        "lifespan_years",
    )
    list_filter = ("kind", "status", "location__aimag_ref", "location__location_type")
    search_fields = ("serial_number", "other_name", "catalog_item__name_mn", "catalog_item__code", "location__name", "location__wmo_index")
    autocomplete_fields = ("catalog_item", "location")
    ordering = ("serial_number",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("catalog-by-kind/", self.admin_site.admin_view(self.catalog_by_kind), name="device_catalog_by_kind"),
            path("sums-by-aimag/", self.admin_site.admin_view(self.sums_by_aimag), name="device_sums_by_aimag"),
            path("locations-by-sum/", self.admin_site.admin_view(self.locations_by_sum), name="device_locations_by_sum"),
            path("export-csv/", self.admin_site.admin_view(self.export_devices_csv), name="export_devices_csv"),
        ]
        return custom + urls

    def catalog_by_kind(self, request):
        kind = (request.GET.get("kind") or "").strip()
        q = (request.GET.get("q") or "").strip()

        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)
        if q:
            qs = qs.filter(Q(name_mn__icontains=q) | Q(code__icontains=q))

        qs = qs.order_by("sort_order", "name_mn")[:200]
        return JsonResponse({"results": [{"id": x.id, "text": x.name_mn} for x in qs]})

    def sums_by_aimag(self, request):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        if not aimag_id.isdigit():
            return JsonResponse({"results": []})

        qs = SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")

        aimag_name = Aimag.objects.filter(id=int(aimag_id)).values_list("name", flat=True).first() or ""
        if (aimag_name or "").strip() == "Улаанбаатар":
            qs = qs.filter(is_ub_district=True)

        return JsonResponse({"results": [{"id": s.id, "text": s.name} for s in qs]})

    def locations_by_sum(self, request):
        sum_id = (request.GET.get("sum_id") or "").strip()
        if not sum_id.isdigit():
            return JsonResponse({"results": []})

        qs = Location.objects.filter(sum_ref_id=int(sum_id)).order_by("name")[:300]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

    def export_devices_csv(self, request):
        qs = Device.objects.all().select_related("location", "catalog_item")

        if not request.user.is_superuser:
            profile = getattr(request.user, "profile", None)
            if profile and getattr(profile, "aimag", None):
                qs = qs.filter(location__aimag_ref=profile.aimag)

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="devices_{now().date()}.csv"'
        resp.write("\ufeff")

        w = csv.writer(resp)
        w.writerow(["ID", "Каталог", "Бусад нэр", "Серийн №", "Байршил"])
        for d in qs:
            w.writerow([d.id, getattr(d.catalog_item, "name_mn", ""), d.other_name, d.serial_number, getattr(d.location, "name", "") if d.location else ""])
        return resp

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_cascade.js",
        )


# ============================================================
# ✅ Spare parts orders
# ============================================================
class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1


@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "aimag", "status", "created_at")
    list_filter = ("status", "aimag")
    search_fields = ("order_no", "aimag__name")
    autocomplete_fields = ("aimag",)
    inlines = [SparePartItemInline]
    ordering = ("-created_at",)


@admin.register(SparePartItem)
class SparePartItemAdmin(admin.ModelAdmin):
    list_display = ("order", "part_name", "quantity")
    search_fields = ("part_name", "order__order_no")
    autocomplete_fields = ("order",)


# ============================================================
# ✅ UserProfile
# ============================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "aimag", "org", "must_change_password")
    list_filter = ("role", "aimag", "org", "must_change_password")
    search_fields = ("user__username", "user__email", "aimag__name", "org__name")
    autocomplete_fields = ("user", "aimag", "org")


# ============================================================
# ✅ Auth audit log (readonly)
# ============================================================
@admin.register(AuthAuditLog)
class AuthAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "username", "user", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("username", "user__username", "ip_address", "user_agent")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    readonly_fields = ("user", "username", "action", "ip_address", "user_agent", "created_at", "extra")
