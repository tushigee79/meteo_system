# meteo_config/admin.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Q, QuerySet, F
from django.http import HttpRequest, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from inventory.models import (  # ✅ your main app models
    Aimag,
    SumDuureg,
    Organization,
    Location,
    InstrumentCatalog,
    Device,
    MaintenanceService,
    ControlAdjustment,
    MaintenanceEvidence,
    ControlEvidence,
    SparePartOrder,
    SparePartItem,
    UserProfile,
    AuthAuditLog,
)

# Optional model
try:
    from inventory.models import AuditEvent  # type: ignore
except Exception:
    AuditEvent = None  # type: ignore


# ============================================================
# Admin list filters (enterprise)
# ============================================================

class AimagFilter(admin.SimpleListFilter):
    title = "Аймаг"
    parameter_name = "aimag_ref__id__exact"

    def lookups(self, request: HttpRequest, model_admin):
        qs = Aimag.objects.all().order_by("name")
        return [(str(a.id), a.name) for a in qs]

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        v = self.value()
        if v:
            return queryset.filter(aimag_ref_id=v)
        return queryset


class SumDuuregByAimagFilter(admin.SimpleListFilter):
    """Cascading Sum/Duureg filter: shows options only for selected Aimag."""
    title = "Сум/Дүүрэг"
    parameter_name = "sum_ref__id__exact"

    def lookups(self, request: HttpRequest, model_admin):
        aimag_id = (request.GET.get("aimag_ref__id__exact") or "").strip()
        if not aimag_id:
            return []

        qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name")

        # If model has is_ub_district and aimag is UB, show only districts; else show non-district sums.
        try:
            is_ub = Aimag.objects.filter(id=aimag_id, is_ub=True).exists()
            if hasattr(SumDuureg, "is_ub_district"):
                qs = qs.filter(is_ub_district=True) if is_ub else qs.filter(is_ub_district=False)
        except Exception:
            pass

        return [(str(o.id), getattr(o, "name_mn", None) or getattr(o, "name", None) or str(o)) for o in qs[:800]]

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        v = self.value()
        if v:
            return queryset.filter(sum_ref_id=v)
        return queryset


class OrganizationFilter(admin.SimpleListFilter):
    title = "Байгууллага"
    parameter_name = "owner_org__id__exact"

    def lookups(self, request: HttpRequest, model_admin):
        qs = Organization.objects.all().order_by("name")
        return [(str(o.id), o.name) for o in qs[:1200]]

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        v = self.value()
        if v:
            return queryset.filter(owner_org_id=v)
        return queryset


class LocationTypeFilter(admin.SimpleListFilter):
    title = "Байршлын төрөл"
    parameter_name = "location_type"  # DB field

    def lookups(self, request: HttpRequest, model_admin):
        # Location дээр choices байвал тэрийг ашиглана
        choices = getattr(Location, "LOCATION_TYPE_CHOICES", None) or getattr(Location, "TYPE_CHOICES", None)

        if choices:
            return [(val, label) for (val, label) in choices]

        # fallback (map дээр ашигладаг key-үүд)
        return [
            ("WEATHER", "Цаг уур"),
            ("AWS", "AWS"),
            ("RADAR", "Радар"),
            ("HYDRO", "Ус судлал"),
            ("AEROLOGY", "Аэрологи"),
            ("AGRO", "ХАА / Agro"),
            ("ETALON", "Эталон"),
            ("OTHER", "Бусад"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        v = self.value()
        if not v:
            return queryset
        return queryset.filter(location_type=v)
    
class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ - Админ"
    site_title = "БҮРТГЭЛ"
    index_title = "Удирдлага"

    def get_urls(self):
        urls = super().get_urls()

        from inventory import admin_workflow as wf

        custom = [
            path(
                "inventory/workflow/pending-counts/",
                self.admin_view(wf.workflow_pending_counts),
                name="workflow_pending_counts",
            ),
            path("debug-hello/", self.admin_view(lambda r: HttpResponse("HELLO")), name="debug_hello"),

            # ✅ Хэрвээ AdminSite дээр map route хэрэгтэй бол:
            path("inventory/location/map/", self.admin_view(self.map_view), name="inventory_location_map"),
            path("inventory/location/map/one/", self.admin_view(self.map_one_view), name="inventory_location_map_one"),
        ]
        return custom + urls

    def map_view(self, request: HttpRequest):
        return TemplateResponse(request, "inventory/admin/location_map_embed.html", {
            "title": "Газрын зураг",
            "map_url": reverse("inventory:inventory_map"),
        })

    def map_one_view(self, request: HttpRequest):
        return TemplateResponse(request, "inventory/admin/location_map_one_embed.html", {
            "title": "Газрын зураг (нэг)",
            "map_url": reverse("station_map_one"),
        })
# inventory/admin.py (төөгсгөлд нь)
from django.contrib.admin.sites import AlreadyRegistered

def register_with(site):
    """
    Custom AdminSite дээр (inventory_admin_site гэх мэт) бүх ModelAdmin-уудыг дахин register хийх.
    admin.py өөрөө admin_site.py-г импортлохгүй байх ёстой!
    """
    # ЖИЧ: Доорх model/admin class-ууд таны admin.py дээр аль хэдийн тодорхойлогдсон гэж үзэж байна.

    try:
        site.register(Device, DeviceAdmin)
    except AlreadyRegistered:
        pass

    try:
        site.register(Location, LocationAdmin)
    except AlreadyRegistered:
        pass

    # ... (адилхан бусад модель/админуудаа энд нэм)


# ============================================================
# Scope helpers (аймгийн инженер зөвхөн өөрийн аймаг)
# ============================================================

def _get_scope(request: HttpRequest) -> Dict[str, Any]:
    u = getattr(request, "user", None)
    if not u or u.is_superuser:
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)
    sum_id = (
        getattr(prof, "sumduureg_id", None)
        or getattr(prof, "sum_ref_id", None)
        or getattr(prof, "district_id", None)
    )
    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}


def _scope_qs(request: HttpRequest, qs: QuerySet, *, aimag_field: str) -> QuerySet:
    scope = _get_scope(request)
    if scope.get("all"):
        return qs

    aimag_id = scope.get("aimag_id")
    if not aimag_id:
        return qs.none()

    qs = qs.filter(**{f"{aimag_field}_id": aimag_id})

    # UB only: optionally scope by district/sum if your data uses it
    sum_id = scope.get("sum_id")
    if aimag_id == 1 and sum_id:
        if aimag_field.endswith("aimag_ref") and hasattr(qs.model, "sum_ref_id"):
            qs = qs.filter(sum_ref_id=sum_id)
        elif "location__" in aimag_field and hasattr(qs.model, "device"):
            qs = qs.filter(device__location__sum_ref_id=sum_id)
    return qs


def _scope_location_qs(request: HttpRequest) -> QuerySet[Location]:
    qs = Location.objects.all()
    scope = _get_scope(request)
    if scope["all"]:
        return qs
    if not scope["aimag_id"]:
        return qs.none()
    qs = qs.filter(aimag_ref_id=scope["aimag_id"])
    if scope["aimag_id"] == 1 and scope["sum_id"]:
        qs = qs.filter(sum_ref_id=scope["sum_id"])
    return qs


# ============================================================
# Map payload helper (used by location changelist map template)
# ============================================================

def _build_locations_payload(qs: QuerySet[Location]) -> List[Dict[str, Any]]:
    """
    Safe, template-friendly payload.
    The template can ignore keys it doesn't need.
    """
    out: List[Dict[str, Any]] = []

    for loc in qs:
        lat = getattr(loc, "latitude", None)
        lon = getattr(loc, "longitude", None)
        if lat is None or lon is None:
            continue

        try:
            change_url = reverse("admin:inventory_location_change", args=[loc.id])
        except Exception:
            change_url = ""

        out.append({
            "id": loc.id,
            "name": getattr(loc, "name", "") or "",
            "location_type": getattr(loc, "location_type", "") or "",
            "aimag": getattr(getattr(loc, "aimag_ref", None), "name", "") or "",
            "sum": getattr(getattr(loc, "sum_ref", None), "name", "") or "",
            "district_name": getattr(loc, "district_name", "") or "",
            "wmo_index": getattr(loc, "wmo_index", "") or "",
            "code": getattr(loc, "code", "") or "",
            "lat": float(lat),
            "lon": float(lon),
            "device_count": int(getattr(loc, "device_count", 0) or 0),
            "pending_total": int(getattr(loc, "pending_total", 0) or 0),
            "admin_change_url": change_url,
        })

    return out


# ============================================================
# Inlines
# ============================================================

class MaintenanceEvidenceInline(admin.TabularInline):
    model = MaintenanceEvidence
    extra = 1
    readonly_fields = ("uploaded_at",)


class ControlEvidenceInline(admin.TabularInline):
    model = ControlEvidence
    extra = 1
    readonly_fields = ("uploaded_at",)


class MaintenanceHistoryInline(admin.TabularInline):
    model = MaintenanceService
    fk_name = "device"
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("-date", "-id")
    readonly_fields = (
        "date",
        "reason",
        "workflow_status",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",
        "note",
    )
    fields = readonly_fields


class ControlHistoryInline(admin.TabularInline):
    model = ControlAdjustment
    fk_name = "device"
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("-date", "-id")
    readonly_fields = (
        "date",
        "result",
        "workflow_status",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",
        "note",
    )
    fields = readonly_fields


class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1


# ============================================================
# Global filters (Aimag/UB, Sum/Duureg, Kind) for ALL modules
# - Works with URL params: ?aimag=<id>&sum=<id>&kind=<KIND>
# - Compatible aliases: aimag_id, sum_id, location_type
# ============================================================

class GlobalAdminFilterMixin:
    """
    Reusable filtering for admin changelists (production-safe).
    Configure on each ModelAdmin:
      aimag_path: str | None   (FK path to Aimag, e.g. 'location__aimag_ref')
      sum_path: str | None     (FK path to SumDuureg, e.g. 'location__sum_ref')
      kind_path: str | None    (field path for kind, e.g. 'kind' or 'device__kind')
    """
    aimag_path: Optional[str] = None
    sum_path: Optional[str] = None
    kind_path: Optional[str] = None

    def _get_param(self, request: HttpRequest, *names: str) -> str:
        for n in names:
            v = (request.GET.get(n) or "").strip()
            if v:
                return v
        return ""

    def apply_global_filters(self, request: HttpRequest, qs: QuerySet) -> QuerySet:
        aimag_val = self._get_param(request, "aimag", "aimag_id")
        sum_val = self._get_param(request, "sum", "sum_id")
        kind_val = self._get_param(request, "kind", "location_type")

        if self.aimag_path and aimag_val:
            qs = qs.filter(**{f"{self.aimag_path}_id": aimag_val})

        if self.sum_path and sum_val:
            qs = qs.filter(**{f"{self.sum_path}_id": sum_val})

        if self.kind_path and kind_val:
            qs = qs.filter(**{self.kind_path: kind_val})

        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context.setdefault("AIMAG_CHOICES", list(Aimag.objects.order_by("name").values_list("id", "name")))
        except Exception:
            extra_context.setdefault("AIMAG_CHOICES", [])
        try:
            extra_context.setdefault("KIND_CHOICES", getattr(InstrumentCatalog, "KIND_CHOICES", []))
        except Exception:
            extra_context.setdefault("KIND_CHOICES", [])
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# Master tables
# ============================================================

@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag", "is_ub_district", "code")
    list_filter = ("aimag", "is_ub_district")
    search_fields = ("name", "code", "aimag__name")
    ordering = ("aimag__name", "name")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "aimag", "is_ub")
    list_filter = ("org_type", "is_ub", "aimag")
    search_fields = ("name", "aimag__name")
    ordering = ("aimag__name", "name")


# ============================================================
# Instrument catalog
# ============================================================

@admin.register(InstrumentCatalog)
class InstrumentCatalogAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "unit", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("kind", "code")


# ============================================================
# Location (map + cascade + device count)
# ============================================================

@admin.register(Location)
class LocationAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "aimag_ref"
    sum_path = "sum_ref"
    kind_path = "location_type"

    change_list_template = "inventory/admin/location_changelist_with_map.html"

    list_display = (
        "name",
        "location_type",
        "aimag_ref",
        "sum_ref",
        "district_name",
        "owner_org",
        "wmo_index",
        "latitude",
        "longitude",
        "pending_badge_col",
        "device_count_col",
        "view_map_col",
    )
    list_select_related = ("aimag_ref", "sum_ref", "owner_org")

    search_fields = ("name", "wmo_index", "code")
    list_filter = (
        LocationTypeFilter,
        AimagFilter,
        SumDuuregByAimagFilter,
        OrganizationFilter,
        "status",
    )
    ordering = ("aimag_ref__name", "sum_ref__name", "name")

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request).select_related("aimag_ref", "sum_ref", "owner_org")

        # scope by role/aimag
        qs = _scope_qs(request, qs, aimag_field="aimag_ref")

        # device count
        qs = qs.annotate(device_count=Count("devices", distinct=True))

        # pending workflow counts
        pending_set = ["SUBMITTED", "PENDING", "NEED_APPROVAL"]
        qs = qs.annotate(
            pending_maint=Count(
                "devices__maintenanceservice",
                filter=Q(devices__maintenanceservice__workflow_status__in=pending_set),
                distinct=True,
            ),
            pending_control=Count(
                "devices__controladjustment",
                filter=Q(devices__controladjustment__workflow_status__in=pending_set),
                distinct=True,
            ),
        ).annotate(
            pending_total=F("pending_maint") + F("pending_control")
        )

        return qs

    @admin.display(description="Багаж", ordering="device_count")
    def device_count_col(self, obj: Location):
        return getattr(obj, "device_count", 0) or 0

    @admin.display(description="Pending", ordering="pending_total")
    def pending_badge_col(self, obj: Location):
        pt = int(getattr(obj, "pending_total", 0) or 0)
        if pt <= 0:
            return format_html('<span style="color:#6b7280;">0</span>')
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'background:#f59e0b;color:#111827;font-weight:800;">{} Pending</span>',
            pt,
        )

    @admin.display(description="🗺️ Харах")
    def view_map_col(self, obj: Location):
        try:
            url = reverse("station_map_one") + f"?location_id={obj.id}"
        except Exception:
            url = ""
        return format_html('<a class="button" href="{}" target="_blank">Харах</a>', url)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Use filtered queryset from ChangeList so filters affect the map too
        try:
            cl = self.get_changelist_instance(request)
            qs = cl.get_queryset(request)
        except Exception:
            qs = self.get_queryset(request)

        extra_context["locations_json"] = json.dumps(_build_locations_payload(qs), ensure_ascii=False)
        extra_context["map_url"] = reverse("inventory:inventory_map")  # public map route (outside admin)

        return super().changelist_view(request, extra_context=extra_context)
  
   
       
    def map_view(self, request: HttpRequest):
        return TemplateResponse(request, "inventory/admin/location_map_embed.html", {
            "title": "Газрын зураг",
            "map_url": reverse("inventory:inventory_map"),
        })

    def map_one_view(self, request: HttpRequest):
        return TemplateResponse(request, "inventory/admin/location_map_one_embed.html", {
            "title": "Газрын зураг (нэг)",
            "map_url": reverse("station_map_one"),
        })


# ============================================================
# Device
# ============================================================

@admin.register(Device)
class DeviceAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "location__aimag_ref"
    sum_path = "location__sum_ref"
    kind_path = "kind"

    list_display = ("serial_number", "kind", "location", "status")
    list_filter = ("kind", "status")
    search_fields = ("serial_number", "inventory_code", "location__name")
    ordering = ("-id",)
    inlines = [MaintenanceHistoryInline, ControlHistoryInline]

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_filter_enterprise.js",
        )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("catalog-by-kind/", self.catalog_by_kind_view, name="device_catalog_by_kind"),
            path("location-options/", self.location_options_view, name="device_location_options"),
        ]
        return custom + urls

    def catalog_by_kind_view(self, request: HttpRequest):
        kind = (request.GET.get("kind") or "").strip().upper()
        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)
        if hasattr(InstrumentCatalog, "is_active"):
            qs = qs.filter(is_active=True)
        return JsonResponse({"results": [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]})

    def location_options_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag") or "").strip() or None
        sum_id = (request.GET.get("sum") or "").strip() or None
        qs = _scope_location_qs(request).order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)
        return JsonResponse([{"id": l.id, "name": l.name} for l in qs], safe=False)

    def formfield_for_foreignkey(self, db_field, request: HttpRequest, **kwargs):
        if db_field.name == "location":
            kwargs["queryset"] = _scope_location_qs(request).order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("location")
        return _scope_qs(request, qs, aimag_field="location__aimag_ref")

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser


# ============================================================
# Maintenance / Control
# ============================================================

@admin.register(MaintenanceService)
class MaintenanceServiceAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "device__location__aimag_ref"
    sum_path = "device__location__sum_ref"
    kind_path = "device__kind"

    list_display = (
        "date",
        "device",
        "workflow_status",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",
    )
    list_filter = ("workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "reason", "note")
    ordering = ("-date", "-id")
    inlines = [MaintenanceEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser


@admin.register(ControlAdjustment)
class ControlAdjustmentAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "device__location__aimag_ref"
    sum_path = "device__location__sum_ref"
    kind_path = "device__kind"

    list_display = (
        "date",
        "device",
        "result",
        "workflow_status",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",
    )
    list_filter = ("result", "workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "note")
    ordering = ("-date", "-id")
    inlines = [ControlEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser


# ============================================================
# Spare parts
# ============================================================

@admin.register(SparePartOrder)
class SparePartOrderAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "aimag"

    list_display = ("order_no", "aimag", "status", "created_at")
    list_filter = ("status", "aimag")
    search_fields = ("order_no",)
    ordering = ("-created_at", "-id")
    inlines = [SparePartItemInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        return _scope_qs(request, qs, aimag_field="aimag")


# ============================================================
# Auth / audit
# ============================================================

@admin.register(UserProfile)
class UserProfileAdmin(GlobalAdminFilterMixin, admin.ModelAdmin):
    aimag_path = "aimag"

    list_display = ("user", "aimag", "org", "must_change_password")
    list_filter = ("aimag", "must_change_password")
    search_fields = ("user__username", "user__email", "org__name", "aimag__name")
    ordering = ("user__username",)


@admin.register(AuthAuditLog)
class AuthAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "username", "user", "ip_address")
    list_filter = ("action",)
    search_fields = ("username", "user__username", "ip_address", "user_agent")
    ordering = ("-created_at", "-id")


if AuditEvent is not None:
    @admin.register(AuditEvent)
    class AuditEventAdmin(admin.ModelAdmin):
        list_display = ("created_at", "actor", "action", "model_label", "object_id", "ip_address")
        list_filter = ("action", "model_label")
        search_fields = ("actor__username", "action", "model_label", "object_id", "object_repr", "ip_address")
        ordering = ("-created_at", "-id")

inventory_admin.register_with(inventory_admin_site)
