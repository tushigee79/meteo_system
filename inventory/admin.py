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
# ✅ Instrument Catalog (SAFE / model-aware)
# ============================================================
@admin.register(InstrumentCatalog)
class InstrumentCatalogAdmin(admin.ModelAdmin):
    base_list_display = ("kind", "code", "name_mn", "sort_order")
    base_list_filter = ("kind",)
    base_search_fields = ("name_mn", "code")
    ordering = ("kind", "sort_order", "name_mn")

    change_list_template = "admin/inventory/instrumentcatalog/import_csv.html"

    def _has_field(self, name: str) -> bool:
        return any(f.name == name for f in self.model._meta.get_fields())

    def get_list_display(self, request):
        cols = list(self.base_list_display)
        if self._has_field("subcategory"):
            cols.insert(3, "subcategory")
        return tuple(cols)

    def get_list_filter(self, request):
        filters = list(self.base_list_filter)
        if self._has_field("subcategory"):
            filters.append("subcategory")
        return tuple(filters)

    search_fields = base_search_fields

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="inventory_instrumentcatalog_import_csv",
            ),
        ]
        return custom + urls

    def import_csv(self, request):
        if request.method == "POST" and request.FILES.get("csv_file"):
            f = request.FILES["csv_file"]
            raw = f.read().decode("utf-8-sig").splitlines()
            reader = csv.DictReader(raw)

            created = 0
            updated = 0

            for row in reader:
                kind = (row.get("kind") or "").strip()
                code = (row.get("code") or "").strip()
                name_mn = (row.get("name_mn") or "").strip()
                sort_order = row.get("sort_order") or "0"

                if not (kind and code and name_mn):
                    continue

                defaults = {
                    "name_mn": name_mn,
                    "sort_order": int(sort_order) if str(sort_order).isdigit() else 0,
                }

                if self._has_field("subcategory"):
                    defaults["subcategory"] = (row.get("subcategory") or "").strip()

                _, is_created = InstrumentCatalog.objects.update_or_create(
                    kind=kind,
                    code=code,
                    defaults=defaults,
                )
                created += 1 if is_created else 0
                updated += 0 if is_created else 1

            ctx = dict(
                self.admin_site.each_context(request),
                title="CSV импорт (InstrumentCatalog)",
                created=created,
                updated=updated,
            )
            return TemplateResponse(
                request,
                "admin/inventory/instrumentcatalog/import_csv_result.html",
                ctx,
            )

        ctx = dict(self.admin_site.each_context(request), title="CSV импорт (InstrumentCatalog)")
        return TemplateResponse(
            request,
            "admin/inventory/instrumentcatalog/import_csv.html",
            ctx,
        )

    class Media:
        js = ("inventory/js/admin/instrumentcatalog_dependent_subcategory.js",)


# ============================================================
# ✅ Aimag / SumDuureg / Organization
# ============================================================
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "code")
    ordering = ("name",)


@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    list_display = ("name", "aimag", "code", "is_ub_district")
    list_filter = ("aimag", "is_ub_district")
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
# ✅ Location admin form (Aimag -> Sum cascade)
# ============================================================
class LocationAdminForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        aimag = getattr(self.instance, "aimag_ref", None)
        aimag_id = (self.data.get("aimag_ref") or "").strip()

        if aimag_id.isdigit():
            aimag = Aimag.objects.filter(id=int(aimag_id)).first()

        if aimag:
            qs = SumDuureg.objects.filter(aimag=aimag).order_by("name")
            if (aimag.name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            self.fields["sum_ref"].queryset = qs
        else:
            self.fields["sum_ref"].queryset = SumDuureg.objects.none()


# ============================================================
# ✅ Location
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
    list_filter = ("location_type", "aimag_ref", "sum_ref", "owner_org")
    search_fields = ("name", "wmo_index", "district_name")
    autocomplete_fields = ("owner_org",)
    ordering = ("aimag_ref__name", "name")

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

        if (aimag.name or "").strip() == "Улаанбаатар":
            qs = qs.filter(is_ub_district=True)

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

        qs = qs.order_by("name")[:200]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

    def locations_by_sum(self, request):
        sum_id = (request.GET.get("sum_id") or "").strip()
        if not sum_id.isdigit():
            return JsonResponse({"results": []})

        qs = Location.objects.filter(sum_ref_id=int(sum_id)).order_by("name")[:300]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

    def download_aimag_template(self, request):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="aimag_template.csv"'
        resp.write("\ufeff")

        w = csv.writer(resp)
        w.writerow(["name", "code"])
        w.writerow(["Улаанбаатар", "UB"])
        w.writerow(["Архангай", "AR"])
        return resp

    def location_map_one(self, request, pk: int):
        loc = Location.objects.filter(pk=pk).first()
        if not loc:
            return TemplateResponse(
                request,
                "admin/inventory/location/location_map_one.html",
                dict(self.admin_site.each_context(request), title="Not found"),
            )

        device_count = Device.objects.filter(location=loc).count()

        points = []
        for _loc in [loc]:
            try:
                points.append(
                    {
                        "id": _loc.id,
                        "name": _loc.name,
                        "aimag": str(_loc.aimag_ref),
                        "type": _loc.location_type,
                        "lat": float(_loc.latitude),
                        "lon": float(_loc.longitude),
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
        js = ("inventory/js/admin/location_cascade.js",)


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
            aimag_name = (
                Aimag.objects.filter(id=int(aimag_id)).values_list("name", flat=True).first()
                or ""
            )
            if (aimag_name or "").strip() == "Улаанбаатар":
                qs = qs.filter(is_ub_district=True)
            self.fields["sumduureg"].queryset = qs

        # ✅ server-side хамгаалалт: sumduureg сонгогдоогүй бол Location хоосон
        if "location" in self.fields:
            sum_id = (self.data.get("sumduureg") or "").strip()
            if sum_id.isdigit():
                self.fields["location"].queryset = Location.objects.filter(
                    sum_ref_id=int(sum_id)
                ).order_by("name")
            elif loc and getattr(loc, "sum_ref_id", None):
                self.fields["location"].queryset = Location.objects.filter(
                    sum_ref_id=loc.sum_ref_id
                ).order_by("name")
            else:
                self.fields["location"].queryset = Location.objects.none()

        # catalog_item queryset filter by kind
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
    search_fields = (
        "serial_number",
        "other_name",
        "catalog_item__name_mn",
        "catalog_item__code",
        "location__name",
        "location__wmo_index",
    )
    autocomplete_fields = ("location",)
    ordering = ("serial_number",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "catalog-by-kind/",
                self.admin_site.admin_view(self.catalog_by_kind),
                name="device_catalog_by_kind",
            ),
            path(
                "sums-by-aimag/",
                self.admin_site.admin_view(self.sums_by_aimag),
                name="device_sums_by_aimag",
            ),
            path(
                "locations-by-sum/",
                self.admin_site.admin_view(self.locations_by_sum),
                name="device_locations_by_sum",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_devices_csv),
                name="export_devices_csv",
            ),
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

    # ✅ FINAL (aid==1): DeviceAdmin.sums_by_aimag
    def sums_by_aimag(self, request):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        qs = SumDuureg.objects.none()

        if not aimag_id.isdigit():
            return JsonResponse({"results": []})

        aid = int(aimag_id)

        if aid == 1:
            # УБ: зөвхөн 9 дүүрэг
            qs = SumDuureg.objects.filter(aimag_id=1, is_ub_district=True)
        else:
            # Бусад аймаг: тухайн аймгийн сум (is_ub_district=False)
            qs = SumDuureg.objects.filter(aimag_id=aid, is_ub_district=False)

        qs = qs.order_by("name")[:500]
        return JsonResponse({"results": [{"id": x.id, "text": x.name} for x in qs]})

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

        w.writerow(
            [
                "serial_number",
                "kind",
                "catalog_code",
                "catalog_name",
                "other_name",
                "location",
                "aimag",
                "sumduureg",
                "status",
                "installation_date",
                "lifespan_years",
            ]
        )

        for d in qs:
            w.writerow(
                [
                    d.serial_number,
                    d.kind,
                    getattr(d.catalog_item, "code", ""),
                    getattr(d.catalog_item, "name_mn", ""),
                    d.other_name,
                    getattr(d.location, "name", ""),
                    getattr(getattr(d.location, "aimag_ref", None), "name", ""),
                    getattr(getattr(d.location, "sum_ref", None), "name", ""),
                    d.status,
                    d.installation_date,
                    d.lifespan_years,
                ]
            )

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
    list_display = ("created_at", "aimag", "status")
    list_filter = ("aimag", "status")
    inlines = [SparePartItemInline]


# ============================================================
# ✅ Users / audit
# ============================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "org", "must_change_password")
    list_filter = ("aimag", "must_change_password")
    search_fields = ("user__username", "user__email")


# ============================================================
# ✅ AuthAuditLog (SAFE / model-aware)
# ============================================================
@admin.register(AuthAuditLog)
class AuthAuditLogAdmin(admin.ModelAdmin):
    def _fields(self):
        return {f.name for f in self.model._meta.get_fields()}

    def _pick(self, *candidates):
        fs = self._fields()
        for c in candidates:
            if c in fs:
                return c
        return None

    def get_list_display(self, request):
        fs = self._fields()
        cols = []

        t = self._pick("timestamp", "created_at", "created", "time", "datetime")
        u = self._pick("user", "username", "actor")
        ip = self._pick("ip_address", "ip", "remote_addr")
        ok = self._pick("success", "is_success", "ok", "result")

        for x in (t, u, ip, ok):
            if x and x in fs:
                cols.append(x)

        return tuple(cols) if cols else ("__str__",)

    def get_list_filter(self, request):
        fs = self._fields()
        ok = self._pick("success", "is_success", "ok", "result")
        return (ok,) if ok and ok in fs else ()

    def get_search_fields(self, request):
        fs = self._fields()
        s = []
        if "ip_address" in fs:
            s.append("ip_address")
        if "ip" in fs:
            s.append("ip")
        if "remote_addr" in fs:
            s.append("remote_addr")
        if "user" in fs:
            s.append("user__username")
        return tuple(s)

    def get_ordering(self, request):
        fs = self._fields()
        t = self._pick("timestamp", "created_at", "created", "time", "datetime")
        return (f"-{t}",) if t and t in fs else ()
