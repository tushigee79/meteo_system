from __future__ import annotations

import csv

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse

from .models import (
    Aimag,
    SumDuureg,
    Organization,
    Location,
    Device,
    InstrumentCatalog,
)


# -----------------------------
# Helper: model field exists?
# -----------------------------
def model_has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


# ============================================================
# Aimag / SumDuureg / Organization
# ============================================================
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "code")
    ordering = ("name",)


@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "aimag", "code")
    list_filter = ("aimag",)
    ordering = ("aimag__name", "name")
    autocomplete_fields = ("aimag",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "org_type", "aimag")
    list_filter = ("org_type", "aimag")
    autocomplete_fields = ("aimag",)
    ordering = ("name",)


# ============================================================
# Location Admin (map + custom urls)
# ============================================================
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # ✅ Чиний map template файл
    change_list_template = "admin/inventory/location/location_map_one.html"

    search_fields = ("name", "wmo_index", "district_name")
    list_display = ("name", "location_type", "aimag_ref", "district_name", "wmo_index")
    list_filter = ("location_type", "aimag_ref", "district_name")
    ordering = ("name",)

    # ⚠️ FK-үүд чинь ийм нэртэй гэж үзэв (байхгүй бол remove хийгээрэй)
    autocomplete_fields = ("aimag_ref", "sum_ref", "owner_org")

    class Media:
        # ✅ Аймаг -> сум/дүүрэг cascade хэрэгтэй бол энэ JS чинь байна
        js = ("inventory/js/admin/location_sum_filter.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "download-template/",
                self.admin_site.admin_view(self.download_aimag_template_view),
                name="download_aimag_template",
            ),
            # template дээр чинь энэ нэрээр дуудаж байгаа тул alias болгож өгч байна
            path(
                "device-import/",
                self.admin_site.admin_view(self.device_import_alias_view),
                name="inventory_device_import_csv",
            ),
            # (optional) Аймаг -> сум options API (хэрэв JS ашиглавал)
            path(
                "sum-options/",
                self.admin_site.admin_view(self.sum_options_view),
                name="location_sum_options",
            ),
        ]
        return custom + urls

    def sum_options_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        qs = SumDuureg.objects.all()
        if aimag_id.isdigit():
            qs = qs.filter(aimag_id=int(aimag_id))
        qs = qs.order_by("name")[:2000]
        return JsonResponse({"items": [{"id": s.id, "text": s.name} for s in qs]})

    def download_aimag_template_view(self, request: HttpRequest):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="location_template.csv"'
        resp.write("\ufeff".encode("utf8"))

        w = csv.writer(resp)
        w.writerow(
            [
                "name",
                "location_type",
                "aimag_ref",
                "sum_ref",
                "latitude",
                "longitude",
                "wmo_index",
                "district_name",
            ]
        )
        w.writerow(["Жишээ станц", "AWS", "Улаанбаатар", "Баянзүрх", "47.92", "106.92", "12345", "Баянзүрх"])
        return resp

    def device_import_alias_view(self, request: HttpRequest):
        # Түр хугацаанд: Device жагсаалт руу үсэрнэ (import view-г дараа нь холбоно)
        return redirect(reverse("admin:inventory_device_changelist"))


# ============================================================
# Device Admin Form (kind -> catalog, aimag/sum -> location)
# ============================================================
class DeviceAdminForm(forms.ModelForm):
    # ✅ UI-д нэмэгдэж харагдана (DB-д хадгалахгүй)
    aimag_pick = forms.ModelChoiceField(
        queryset=Aimag.objects.all().order_by("name"),
        required=False,
        label="Аймаг/Нийслэл",
    )
    sum_pick = forms.ModelChoiceField(
        queryset=SumDuureg.objects.none(),
        required=False,
        label="Сум/Дүүрэг",
    )

    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ----------------------------
        # 1) kind -> catalog_item queryset
        # ----------------------------
        kind = None
        if self.data.get("kind"):
            kind = (self.data.get("kind") or "").strip()
        elif self.instance and getattr(self.instance, "kind", None):
            kind = str(self.instance.kind)

        if "catalog_item" in self.fields:
            qs = InstrumentCatalog.objects.all()
            if kind:
                if model_has_field(InstrumentCatalog, "category"):
                    qs = qs.filter(category=kind)
                else:
                    qs = qs.filter(kind=kind)

            if model_has_field(InstrumentCatalog, "is_active"):
                qs = qs.filter(is_active=True)

            self.fields["catalog_item"].queryset = qs.order_by("sort_order", "name_mn")

        # ----------------------------
        # 2) instance.location -> aimag/sum initial
        # ----------------------------
        if self.instance and getattr(self.instance, "location_id", None):
            loc = self.instance.location
            if loc and getattr(loc, "aimag_ref_id", None):
                self.fields["aimag_pick"].initial = loc.aimag_ref_id
                self.fields["sum_pick"].queryset = SumDuureg.objects.filter(
                    aimag_id=loc.aimag_ref_id
                ).order_by("name")
                if getattr(loc, "sum_ref_id", None):
                    self.fields["sum_pick"].initial = loc.sum_ref_id

        # ----------------------------
        # 3) POST selected aimag/sum -> filter sum_pick + location queryset
        # ----------------------------
        aimag_id = (self.data.get("aimag_pick") or "").strip()
        sum_id = (self.data.get("sum_pick") or "").strip()

        if aimag_id.isdigit():
            self.fields["sum_pick"].queryset = SumDuureg.objects.filter(
                aimag_id=int(aimag_id)
            ).order_by("name")

        if "location" in self.fields:
            loc_qs = Location.objects.all()
            if sum_id.isdigit():
                loc_qs = loc_qs.filter(sum_ref_id=int(sum_id))
            elif aimag_id.isdigit():
                loc_qs = loc_qs.filter(aimag_ref_id=int(aimag_id))
            self.fields["location"].queryset = loc_qs.order_by("name")

    def clean(self):
        cleaned = super().clean()

        # “Бусад” сонгосон бол other_name заавал
        if hasattr(Device, "Kind") and cleaned.get("kind") == getattr(Device.Kind, "OTHER", None):
            other = (cleaned.get("other_name") or "").strip()
            if not other:
                raise ValidationError({"other_name": "“Бусад” сонгосон бол нэр заавал бөглөнө."})

        return cleaned


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm

    list_display = ("serial_number", "catalog_item", "location", "status", "installation_date")
    list_filter = ("status", "kind", "location__aimag_ref")
    search_fields = ("serial_number", "catalog_item__name_mn", "other_name", "location__name")

    # ❌ autocomplete хэрэглэхгүй (dependent dropdown ажиллуулахын тулд)
    autocomplete_fields = ()

    # aimag_pick, sum_pick-ийг location-оос өмнө гаргая
    fieldsets = (
        (None, {"fields": ("serial_number", "kind", "catalog_item", "other_name")}),
        ("Байршлын сонголт", {"fields": ("aimag_pick", "sum_pick", "location")}),
        ("Төлөв", {"fields": ("status", "installation_date", "lifespan_years")}),
    )

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_dependent.js",
        )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "catalog-options/",
                self.admin_site.admin_view(self.catalog_options_view),
                name="inventory_device_catalog_options",
            ),
            path(
                "sum-options/",
                self.admin_site.admin_view(self.sum_options_view),
                name="inventory_device_sum_options",
            ),
            path(
                "location-options/",
                self.admin_site.admin_view(self.location_options_view),
                name="inventory_device_location_options",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_devices_csv_view),
                name="export_devices_csv",
            ),
        ]
        return custom + urls

    def catalog_options_view(self, request: HttpRequest):
        kind = (request.GET.get("kind") or "").strip()

        qs = InstrumentCatalog.objects.all()
        if kind:
            if model_has_field(InstrumentCatalog, "category"):
                qs = qs.filter(category=kind)
            else:
                qs = qs.filter(kind=kind)

        if model_has_field(InstrumentCatalog, "is_active"):
            qs = qs.filter(is_active=True)

        qs = qs.order_by("sort_order", "name_mn")
        items = [{"id": x.id, "text": f"{x.name_mn} ({x.code})" if x.code else x.name_mn} for x in qs[:2000]]
        return JsonResponse({"items": items})

    def sum_options_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        qs = SumDuureg.objects.all()
        if aimag_id.isdigit():
            qs = qs.filter(aimag_id=int(aimag_id))
        qs = qs.order_by("name")[:2000]
        return JsonResponse({"items": [{"id": s.id, "text": s.name} for s in qs]})

    def location_options_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        sum_id = (request.GET.get("sum_id") or "").strip()

        qs = Location.objects.all()
        if sum_id.isdigit():
            qs = qs.filter(sum_ref_id=int(sum_id))
        elif aimag_id.isdigit():
            qs = qs.filter(aimag_ref_id=int(aimag_id))

        qs = qs.order_by("name")[:2000]
        return JsonResponse({"items": [{"id": x.id, "text": x.name} for x in qs]})

    def export_devices_csv_view(self, request: HttpRequest):
        qs = self.get_queryset(request).select_related("location", "catalog_item")

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="devices_export.csv"'
        resp.write("\ufeff".encode("utf8"))

        w = csv.writer(resp)
        w.writerow(["ID", "Серийн дугаар", "Төрөл", "Каталог", "Бусад нэр", "Байршил", "Статус", "Суулгасан огноо"])

        for d in qs:
            w.writerow(
                [
                    d.pk,
                    getattr(d, "serial_number", ""),
                    getattr(d, "kind", ""),
                    getattr(getattr(d, "catalog_item", None), "name_mn", "") if getattr(d, "catalog_item", None) else "",
                    getattr(d, "other_name", ""),
                    str(getattr(d, "location", "")),
                    getattr(d, "status", ""),
                    getattr(d, "installation_date", "") or "",
                ]
            )
        return resp
