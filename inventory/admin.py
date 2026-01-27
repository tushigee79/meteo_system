from __future__ import annotations

from typing import Any, Dict
import json

from django.contrib import admin
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
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

# Optional
try:
    from .models import AuditEvent  # type: ignore
except Exception:
    AuditEvent = None  # type: ignore


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

    sum_id = scope.get("sum_id")
    if aimag_id == 1 and sum_id:
        if aimag_field.endswith("aimag_ref") and hasattr(qs.model, "sum_ref_id"):
            qs = qs.filter(sum_ref_id=sum_id)
        elif "location__" in aimag_field:
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
class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "unit", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("kind", "code")


# ============================================================
# Location (map + cascade + device count)
# ============================================================

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
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
        "device_count_col",
        "view_map_col",
    )

    list_filter = ("location_type", "aimag_ref", "sum_ref", "owner_org")
    search_fields = ("name", "code", "wmo_index", "aimag_ref__name", "sum_ref__name", "owner_org__name")
    ordering = ("aimag_ref__name", "sum_ref__name", "name")

    class Media:
        js = ("inventory/js/admin/location_add_cascade.js",)

    # -------- queryset --------
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        qs = qs.select_related("aimag_ref", "sum_ref", "owner_org")

        qs = qs.annotate(
            device_count=Count("devices", distinct=True),

            pending_maintenance=Count(
                "devices__maintenance_services",
                filter=Q(devices__maintenance_services__workflow_status="SUBMITTED"),
                distinct=True,
            ),

            pending_control=Count(
                "devices__control_adjustments",
                filter=Q(devices__control_adjustments__workflow_status="SUBMITTED"),
                distinct=True,
            ),
        ).annotate(
            pending_total=
                Count(
                    "devices__maintenance_services",
                    filter=Q(devices__maintenance_services__workflow_status="SUBMITTED"),
                    distinct=True,
                )
                +
                Count(
                    "devices__control_adjustments",
                    filter=Q(devices__control_adjustments__workflow_status="SUBMITTED"),
                    distinct=True,
                )
        )

        return _scope_qs(request, qs, aimag_field="aimag_ref")

    # -------- columns --------
    @admin.display(description="Багаж", ordering="device_count")
    def device_count_col(self, obj: Location):
        return int(getattr(obj, "device_count", 0) or 0)

    @admin.display(description="🗺 Харах")
    def view_map_col(self, obj: Location):
        try:
            url = reverse("admin:inventory_location_map_one", args=[obj.pk])
            return format_html('<a class="button" href="{}">Харах</a>', url)
        except Exception:
            return "-"

    # -------- cascade endpoint --------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("sums-by-aimag/", self.sums_by_aimag_view, name="location_sums_by_aimag"),
            path("map/", self.admin_site.admin_view(self.map_view), name="inventory_location_map"),
            path(
                "map/<int:location_id>/",
                self.admin_site.admin_view(self.map_one_view),
                name="inventory_location_map_one",
            ),
        ]
        return custom + urls

    def sums_by_aimag_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag_id") or "").strip()
        qs = SumDuureg.objects.all().order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_id=aimag_id)
        return JsonResponse({"results": [{"id": s.id, "text": s.name} for s in qs]})

    # -------- map helpers --------
    def _build_locations_payload(self, qs: QuerySet[Location]):
        items = []
        for o in qs[:5000]:
            if o.latitude is None or o.longitude is None:
                continue
            items.append(
                {
                    "id": o.id,
                    "name": o.name,
                    "type": (o.location_type or "OTHER"),
                    "org": getattr(getattr(o, "owner_org", None), "name", "") or "",
                    "device_count": int(getattr(o, "device_count", 0) or 0),
                    "pending_maintenance": int(getattr(o, "pending_maintenance", 0) or 0),
                    "pending_control": int(getattr(o, "pending_control", 0) or 0),
                    "pending_total": int(getattr(o, "pending_total", 0) or 0),
                    "aimag": getattr(getattr(o, "aimag_ref", None), "name", "") or "",
                    "sum": getattr(getattr(o, "sum_ref", None), "name", "") or "",
                    "district": o.district_name or "",
                    "lat": float(o.latitude),
                    "lon": float(o.longitude),
                    "wmo": o.wmo_index or "",
                    "loc_admin_url": reverse("admin:inventory_location_change", args=[o.id]),
                    "device_list_url": reverse("admin:inventory_device_changelist") + f"?location__id__exact={o.id}",
                }
            )
        return items

    def changelist_view(self, request: HttpRequest, extra_context=None):
        qs = self.get_queryset(request)
        extra_context = extra_context or {}
        extra_context["locations_json"] = json.dumps(self._build_locations_payload(qs), ensure_ascii=False)
        return super().changelist_view(request, extra_context=extra_context)

    def map_view(self, request: HttpRequest):
        qs = self.get_queryset(request)
        ctx = dict(
            self.admin_site.each_context(request),
            title="Станцуудын байршил (Газрын зураг)",
            locations_json=json.dumps(self._build_locations_payload(qs), ensure_ascii=False),
        )
        return render(request, "inventory/location_map.html", ctx)

    def map_one_view(self, request: HttpRequest, location_id: int):
        qs = self.get_queryset(request).filter(id=location_id)
        ctx = dict(
            self.admin_site.each_context(request),
            title="Байршил (Газрын зураг)",
            locations_json=json.dumps(self._build_locations_payload(qs), ensure_ascii=False),
            focus_id=location_id,
        )
        return render(request, "inventory/location_map.html", ctx)


# ============================================================
# Device
# ============================================================

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
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
        return JsonResponse(
            {"results": [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]}
        )

    def location_options_view(self, request: HttpRequest):
        aimag_id = (request.GET.get("aimag") or "").strip() or None
        sum_id = (request.GET.get("sum") or "").strip() or None
        qs = _scope_location_qs(request).order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)
        return JsonResponse([{"id": l.id, "name": l.name} for l in qs], safe=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "location":
            kwargs["queryset"] = _scope_location_qs(request).order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("location")
        return _scope_qs(request, qs, aimag_field="location__aimag_ref")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ============================================================
# Maintenance / Control
# ============================================================

@admin.register(MaintenanceService)
class MaintenanceServiceAdmin(admin.ModelAdmin):
    list_display = ("date", "device", "workflow_status", "performer_type", "performer_engineer_name", "performer_org_name")
    list_filter = ("workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "reason", "note")
    ordering = ("-date", "-id")
    inlines = [MaintenanceEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ControlAdjustment)
class ControlAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("date", "device", "result", "workflow_status", "performer_type", "performer_engineer_name", "performer_org_name")
    list_filter = ("result", "workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "note")
    ordering = ("-date", "-id")
    inlines = [ControlEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ============================================================
# Spare parts
# ============================================================

@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
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
class UserProfileAdmin(admin.ModelAdmin):
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
    @admin.register(AuditEvent)  # type: ignore
    class AuditEventAdmin(admin.ModelAdmin):
        list_display = ("created_at", "actor", "action", "model_label", "object_id", "ip_address")
        list_filter = ("action", "model_label")
        search_fields = ("actor__username", "action", "model_label", "object_id", "object_repr", "ip_address")
        ordering = ("-created_at", "-id")
