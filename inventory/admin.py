import csv
import json

import pandas as pd
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .models import (
    Aimag,
    AuthAuditLog,
    ControlAdjustment,
    Device,
    InstrumentCatalog,
    Location,
    MaintenanceService,
    Organization,
    SparePartItem,
    SparePartOrder,
    SumDuureg,
    UserProfile,
)

# ============================================================
# ✅ Location list_filter cascade (АЙМАГ → СУМ/ДҮҮРЭГ)
# ============================================================
class AimagCascadeFilter(admin.SimpleListFilter):
    title = _("Аймаг/Нийслэл")
    parameter_name = "aimag_ref__id__exact"  # ✅ URL param

    def lookups(self, request, model_admin):
        qs = Aimag.objects.order_by("name")
        return [(str(a.id), a.name) for a in qs]

    def queryset(self, request, queryset):
        v = self.value()
        if v and str(v).isdigit():
            return queryset.filter(aimag_ref_id=int(v))
        return queryset


class SumDuuregCascadeFilter(admin.SimpleListFilter):
    title = _("Сум/Дүүрэг")
    parameter_name = "sum_ref__id__exact"  # ✅ стандарт

    def lookups(self, request, model_admin):
        aimag_id = request.GET.get("aimag_ref__id__exact")  # ✅ cascade түлхүүр
        qs = SumDuureg.objects.all()

        if aimag_id and str(aimag_id).isdigit():
            qs = qs.filter(aimag_id=int(aimag_id))
        else:
            qs = SumDuureg.objects.none()  # aimag сонгоогүй үед хоосон

        qs = qs.order_by("name")
        return [(str(s.id), s.name) for s in qs]

    def queryset(self, request, queryset):
        v = self.value()
        if v and str(v).isdigit():
            return queryset.filter(sum_ref_id=int(v))
        return queryset


# ============================================================
# ✅ Instrument Catalog (filter + CSV import товч)
# ============================================================
@admin.register(InstrumentCatalog)
class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "unit", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("kind", "code")

    change_list_template = "admin/inventory/instrumentcatalog/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-csv/", self.import_csv_view, name="instrumentcatalog_import_csv"),
        ]
        return custom + urls

    def import_csv_view(self, request):
        if request.method == "POST" and request.FILES.get("csv_file"):
            f = request.FILES["csv_file"]
            try:
                df = pd.read_csv(f)

                created = 0
                skipped = 0

                for _, r in df.iterrows():
                    code = str(r.get("code")).strip()
                    name_mn = str(r.get("name_mn")).strip()
                    kind = str(r.get("location_type")).strip() if pd.notna(r.get("location_type")) else "OTHER"
                    unit = str(r.get("unit")).strip() if pd.notna(r.get("unit")) else ""

                    if not code or not name_mn:
                        skipped += 1
                        continue

                    obj, is_new = InstrumentCatalog.objects.get_or_create(
                        code=code,
                        defaults={
                            "name_mn": name_mn,
                            "kind": kind,
                            "unit": unit,
                            "is_active": True,
                        },
                    )

                    if is_new:
                        created += 1

                messages.success(request, f"CSV импорт дууссан: нэмэгдсэн={created}, алгассан={skipped}")
                return redirect("..")

            except Exception as e:
                messages.error(request, f"CSV уншихад алдаа гарлаа: {e}")

        return render(request, "admin/inventory/instrumentcatalog/import_csv.html")


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
# ✅ Location add/edit form (Аймаг → Сум/Дүүрэг queryset filter)
# ============================================================
class LocationAdminForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ aimag-г POST -> instance -> initial дарааллаар олно
        aimag_id = (self.data.get("aimag_ref") or "").strip()
        if not aimag_id.isdigit():
            aimag_id = str(getattr(self.instance, "aimag_ref_id", "") or "").strip()
        if not aimag_id.isdigit():
            aimag_id = str(self.initial.get("aimag_ref") or "").strip()

        # ✅ sum_ref queryset-ийг aimag-аар шүүнэ
        if "sum_ref" in self.fields:
            if aimag_id.isdigit():
                self.fields["sum_ref"].queryset = (
                    SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")
                )
            else:
                self.fields["sum_ref"].queryset = SumDuureg.objects.none()


# ============================================================
# ✅ Location Admin (map one + cascade + template)
# ============================================================
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationAdminForm

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

    # ✅ cascade filters (change list)
    list_filter = (
        "location_type",
        AimagCascadeFilter,
        SumDuuregCascadeFilter,
        "owner_org",
    )

    search_fields = ("name", "wmo_index", "district_name")

    # ✅ CRITICAL: sum_ref-ийг autocomplete-оос авна (эс бөгөөс бүх сум гарсаар байдаг)
    autocomplete_fields = ("aimag_ref", "owner_org")

    ordering = ("aimag_ref__name", "name")

    # ✅ “Хариуцагч”-ийг хамгаалах
    readonly_fields = ("owner_org",)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # ✅ templates-үүд өөр өөр key ашиглаж магадгүй тул 2-ууланг нь өгнө
        choices = list(getattr(Location, "LOCATION_TYPES", []))
        extra_context["LOCATION_TYPE_CHOICES"] = choices
        extra_context["location_type_choices"] = choices

        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        # ✅ owner_org хоосон үед л автоматаар бөглөнө
        if not obj.owner_org_id and obj.aimag_ref_id:
            org = Organization.objects.filter(
                aimag_id=obj.aimag_ref_id,
                org_type="OBS_CENTER",
                is_ub=False,
            ).order_by("id").first()

            if not org:
                org = Organization.objects.filter(
                    aimag_id=obj.aimag_ref_id,
                    name__icontains="УЦУОШТ",
                ).order_by("id").first()

            if org:
                obj.owner_org = org

        super().save_model(request, obj, form, change)

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

        # ✅ УБ/бусад ялгалт: тухайн aimag дээр UB district байгаа эсэхээр шийднэ
        if qs.filter(is_ub_district=True).exists():
            qs = qs.filter(is_ub_district=True)
        else:
            qs = qs.filter(is_ub_district=False)

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
        # ✅ Давхардалгүй:
        # 1) change_list (лист дээрх filter/cascade)
        # 2) add/change form дээр aimag→sum dropdown динамик (sums-by-aimag/)
        # 3) map дээр UB district autofill (district_name)
        js = (
            "inventory/js/admin/location_cascade.js",
            "inventory/js/admin/location_add_cascade.js",
            "inventory/js/admin/ub_district_autofill.js",
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

        # ------------------------------------------------------------
        # A) Location cascade (aimag/sumduureg initial)
        # ------------------------------------------------------------
        loc = getattr(self.instance, "location", None)
        if loc and getattr(loc, "aimag_ref", None):
            self.fields["aimag"].initial = loc.aimag_ref

            qs = SumDuureg.objects.filter(aimag=loc.aimag_ref).order_by("name")
            if (loc.aimag_ref.name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            else:
                qs = qs.filter(is_ub_district=False)

            self.fields["sumduureg"].queryset = qs
            if getattr(loc, "sum_ref", None):
                self.fields["sumduureg"].initial = loc.sum_ref

        # POST үед aimag-аар sumduureg queryset
        aimag_id = (self.data.get("aimag") or "").strip()
        if aimag_id.isdigit():
            qs = SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")

            aimag_name = (
                Aimag.objects.filter(id=int(aimag_id))
                .values_list("name", flat=True)
                .first()
                or ""
            )

            if (aimag_name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            else:
                qs = qs.filter(is_ub_district=False)

            self.fields["sumduureg"].queryset = qs

        # ------------------------------------------------------------
        # B) ✅ Catalog dropdown queryset filter by Device.kind
        #    IMPORTANT: autocomplete ашиглавал queryset үл тооно.
        # ------------------------------------------------------------
        kind = (self.data.get("kind") or "").strip()
        if not kind:
            kind = (getattr(self.instance, "kind", None) or "").strip()

        if "catalog_item" in self.fields:
            f = self.fields["catalog_item"]

            if kind:
                f.queryset = InstrumentCatalog.objects.filter(kind=kind).order_by(
                    "sort_order", "code", "name_mn"
                )
            else:
                f.queryset = InstrumentCatalog.objects.none()


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
    search_fields = (
        "serial_number",
        "other_name",
        "catalog_item__name_mn",
        "catalog_item__code",
        "location__name",
        "location__wmo_index",
    )

    # ✅ CRITICAL: catalog_item autocomplete-ийг авахгүй (эс бөгөөс бүгд гарсаар байдаг)
    autocomplete_fields = ()  # intentionally empty
    ordering = ("serial_number",)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["KIND_CHOICES"] = list(getattr(InstrumentCatalog, "KIND_CHOICES", []))
        return super().changelist_view(request, extra_context=extra_context)

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

        if not kind:
            return JsonResponse({"results": []})

        qs = InstrumentCatalog.objects.filter(kind=kind)

        if q:
            qs = qs.filter(Q(name_mn__icontains=q) | Q(code__icontains=q))

        qs = qs.order_by("sort_order", "code", "name_mn")[:500]
        return JsonResponse({"results": [{"id": x.id, "text": f"{x.code} – {x.name_mn}"} for x in qs]})

    def sums_by_aimag(self, request):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        if not aimag_id.isdigit():
            return JsonResponse({"results": []})

        aimag_name = (
            Aimag.objects.filter(id=int(aimag_id))
            .values_list("name", flat=True)
            .first()
            or ""
        )

        qs = SumDuureg.objects.filter(aimag_id=int(aimag_id)).order_by("name")
        if (aimag_name or "").strip() == "Улаанбаатар":
            qs = qs.filter(is_ub_district=True)
        else:
            qs = qs.filter(is_ub_district=False)

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
            prof = getattr(request.user, "userprofile", None)
            if prof and getattr(prof, "aimag_id", None):
                qs = qs.filter(location__aimag_ref_id=prof.aimag_id)
                # ✅ зөвхөн УБ дээр дүүргээр
                sum_id = getattr(prof, "sumduureg_id", None) or getattr(prof, "sum_ref_id", None) or getattr(prof, "district_id", None)
                if prof.aimag_id == 1 and sum_id:
                    qs = qs.filter(location__sum_ref_id=sum_id)

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="devices_{now().date()}.csv"'
        resp.write("\ufeff")

        w = csv.writer(resp)
        w.writerow(["ID", "Каталог", "Бусад нэр", "Серийн №", "Байршил"])
        for d in qs:
            w.writerow(
                [
                    d.id,
                    getattr(d.catalog_item, "name_mn", ""),
                    d.other_name,
                    d.serial_number,
                    getattr(d.location, "name", "") if d.location else "",
                ]
            )
        return resp

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_cascade.js",
        )


# ============================================================
# ✅ Admin + “Device FK scope filter” (аймаг/дүүрэг зөвшөөрөл)
# ============================================================
def _get_user_scope(request):
    """
    Scope тодорхойлох:
      - superuser => бүхнийг зөвшөөрнө
      - бусад => UserProfile.aimag дээр тулгуурлана
      - УБ (aimag_id==1) дээр UserProfile.sumduureg байвал дүүргээр шүүнэ
    """
    u = request.user
    if u.is_superuser:
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)

    # УБ дүүрэг (байвал)
    sum_id = getattr(prof, "sumduureg_id", None) or getattr(prof, "sum_ref_id", None) or getattr(prof, "district_id", None)

    # Зөвхөн УБ дээр дүүргээр шүүнэ (aimag_id==1 үед)
    if aimag_id != 1:
        sum_id = None

    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}


def _device_queryset_for_request(request):
    scope = _get_user_scope(request)
    qs = Device.objects.all()

    if scope["all"]:
        return qs

    # aimag байхгүй бол юу ч зөвшөөрөхгүй (аюулгүй тал)
    if not scope["aimag_id"]:
        return Device.objects.none()

    # Device -> Location -> aimag_ref / sum_ref гэж үзэв
    qs = qs.filter(location__aimag_ref_id=scope["aimag_id"])

    if scope["sum_id"]:
        qs = qs.filter(location__sum_ref_id=scope["sum_id"])

    return qs


class ScopedDeviceFKMixin:
    """
    ModelAdmin дээр device FK-г scope-оор шүүнэ.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device":
            kwargs["queryset"] = _device_queryset_for_request(request)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        scope = _get_user_scope(request)

        if scope["all"]:
            return qs

        if not scope["aimag_id"]:
            return qs.none()

        qs = qs.filter(device__location__aimag_ref_id=scope["aimag_id"])
        if scope["sum_id"]:
            qs = qs.filter(device__location__sum_ref_id=scope["sum_id"])
        return qs

    def has_delete_permission(self, request, obj=None):
        # Аймгийн инженерүүд delete хийхгүй (санасан policy)
        if request.user.groups.filter(name="AimagEngineer").exists() and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


class MaintenanceServiceAdminForm(forms.ModelForm):
    class Meta:
        model = MaintenanceService
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.request is not None and "device" in self.fields:
            self.fields["device"].queryset = _device_queryset_for_request(self.request)

    def clean_device(self):
        dev = self.cleaned_data.get("device")
        if not dev or not self.request:
            return dev
        allowed = _device_queryset_for_request(self.request).filter(pk=dev.pk).exists()
        if not allowed:
            raise ValidationError("Таны эрхийн хүрээнд хамаарахгүй багаж сонгогдсон байна.")
        return dev


class ControlAdjustmentAdminForm(forms.ModelForm):
    class Meta:
        model = ControlAdjustment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.request is not None and "device" in self.fields:
            self.fields["device"].queryset = _device_queryset_for_request(self.request)

    def clean_device(self):
        dev = self.cleaned_data.get("device")
        if not dev or not self.request:
            return dev
        allowed = _device_queryset_for_request(self.request).filter(pk=dev.pk).exists()
        if not allowed:
            raise ValidationError("Таны эрхийн хүрээнд хамаарахгүй багаж сонгогдсон байна.")
        return dev


@admin.register(MaintenanceService)
class MaintenanceServiceAdmin(ScopedDeviceFKMixin, admin.ModelAdmin):
    list_display = ("date", "device", "reason", "performer_type", "evidence")
    list_filter = ("reason", "performer_type", "date")
    search_fields = ("device__serial_number", "device__other_name", "performer_engineer_name", "performer_org_name")
    autocomplete_fields = ()  # FK-г энгийн select байлгах (scope шүүлтүүртэй)

    fieldsets = (
        ("Үндсэн", {"fields": ("device", "date", "reason")}),
        ("Гүйцэтгэсэн этгээд", {"fields": ("performer_type", "performer_engineer_name", "performer_org_name")}),
        ("Нотлох баримт", {"fields": ("evidence",)}),
        ("Тайлбар", {"fields": ("note",)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        base_form = MaintenanceServiceAdminForm

        class WrappedForm(base_form):
            def __new__(cls, *a, **k):
                k["request"] = request
                return base_form(*a, **k)

        kwargs["form"] = WrappedForm
        return super().get_form(request, obj, **kwargs)


@admin.register(ControlAdjustment)
class ControlAdjustmentAdmin(ScopedDeviceFKMixin, admin.ModelAdmin):
    list_display = ("date", "device", "result", "performer_type", "evidence")
    list_filter = ("result", "performer_type", "date")
    search_fields = ("device__serial_number", "device__other_name", "performer_engineer_name", "performer_org_name")
    autocomplete_fields = ()  # FK-г энгийн select байлгах (scope шүүлтүүртэй)

    fieldsets = (
        ("Үндсэн", {"fields": ("device", "date", "result")}),
        ("Гүйцэтгэсэн этгээд", {"fields": ("performer_type", "performer_engineer_name", "performer_org_name")}),
        ("Нотлох баримт", {"fields": ("evidence",)}),
        ("Тайлбар", {"fields": ("note",)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        base_form = ControlAdjustmentAdminForm

        class WrappedForm(base_form):
            def __new__(cls, *a, **k):
                k["request"] = request
                return base_form(*a, **k)

        kwargs["form"] = WrappedForm
        return super().get_form(request, obj, **kwargs)


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
