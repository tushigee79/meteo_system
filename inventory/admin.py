# inventory/admin.py
from __future__ import annotations

import io
import json
import logging
import uuid
from typing import Any, Dict, Optional

import qrcode
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.exceptions import FieldError
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse, request
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify
from .admin_site import inventory_admin_site


from .forms import DeviceAdminForm
from .models import (
    Aimag, SumDuureg, Organization, Location, InstrumentCatalog,
    Device, MaintenanceService, ControlAdjustment, MaintenanceEvidence,
    ControlEvidence, SparePartOrder, SparePartItem, UserProfile, AuthAuditLog,
)

# Optional
try:
    from .models import AuditEvent  # type: ignore
except Exception:
    AuditEvent = None  # type: ignore

# Optional PDF passport
try:
    from .pdf_passport import generate_device_passport_pdf_bytes
except Exception:
    generate_device_passport_pdf_bytes = None  # type: ignore

logger = logging.getLogger(__name__)


# ============================================================
# Helpers: scope (аймгийн инженер зөвхөн өөрийн аймаг)
# ============================================================

def _get_scope(request: HttpRequest) -> Dict[str, Any]:
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


def _scope_qs(request: HttpRequest, qs: QuerySet, *, aimag_field: str) -> QuerySet:
    scope = _get_scope(request)
    if scope.get("all"):
        return qs

    aimag_id = scope.get("aimag_id")
    if not aimag_id:
        return qs.none()

    qs = qs.filter(**{f"{aimag_field}_id": aimag_id})

    # УБ бол сум/дүүргээр нарийвчлах боломж (байвал)
    sum_id = scope.get("sum_id")
    if sum_id and "sum_ref" in aimag_field:
        try:
            qs = qs.filter(sum_ref_id=sum_id)
        except Exception:
            pass
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
# Forms
# ============================================================

class DeviceAdminForm(forms.ModelForm):
    admin_aimag = forms.ModelChoiceField(
        queryset=Aimag.objects.all(),
        required=False,
        label="Аймаг / Улаанбаатар",
    )
    admin_sum = forms.ModelChoiceField(
        queryset=SumDuureg.objects.none(),
        required=False,
        label="Сум / Дүүрэг",
    )

    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # ===== Аймгийн инженер =====
        scope = _get_scope(self.request) if self.request else {}
        if not scope.get("all"):
            aimag_id = scope.get("aimag_id")
            if aimag_id:
                self.fields["admin_aimag"].queryset = Aimag.objects.filter(id=aimag_id)
                self.fields["admin_aimag"].initial = aimag_id
                self.fields["admin_aimag"].disabled = True

                self.fields["admin_sum"].queryset = SumDuureg.objects.filter(
                    aimag_ref_id=aimag_id
                )

        # ===== Edit үед location-оос initial тааруулах =====
        if self.instance and self.instance.location_id:
            loc = self.instance.location
            self.fields["admin_aimag"].initial = loc.aimag_ref_id
            self.fields["admin_sum"].queryset = SumDuureg.objects.filter(
                aimag_ref_id=loc.aimag_ref_id
            )
            self.fields["admin_sum"].initial = loc.sum_ref_id


# ============================================================
# Admin list filters
# ============================================================

class SumDuuregByAimagFilter(admin.SimpleListFilter):
    title = "Сум/Дүүрэг"
    parameter_name = "sum_ref__id__exact"

    def lookups(self, request, model_admin):
        aimag_id = (request.GET.get("aimag_ref__id__exact") or "").strip()
        if not aimag_id:
            return []
        qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name")
        return [(str(o.id), getattr(o, "name_mn", None) or str(o)) for o in qs[:500]]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(sum_ref_id=val)
        return queryset


class LocationTypeFilter(admin.SimpleListFilter):
    title = "Байршлын төрөл"
    parameter_name = "location_type"

    def lookups(self, request, model_admin):
        choices = getattr(Location, "LOCATION_TYPE_CHOICES", None) or getattr(Location, "TYPE_CHOICES", None)
        if choices:
            return [(val, label) for (val, label) in choices]

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

    def queryset(self, request, queryset):
        v = self.value()
        return queryset if not v else queryset.filter(location_type=v)


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


class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1
    verbose_name = "Сэлбэг"
    verbose_name_plural = "Сэлбэгүүд"


# Optional: movement inline (байхгүй бол import-гүй)
try:
    from .models import DeviceMovement  # type: ignore

    class DeviceMovementInline(admin.TabularInline):
        model = DeviceMovement
        extra = 0
        can_delete = False
        show_change_link = False
        readonly_fields = ("moved_at", "from_location", "to_location", "reason", "moved_by")
        fields = readonly_fields
        ordering = ("-moved_at", "-id")
except Exception:
    DeviceMovementInline = None  # type: ignore


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


# ============================================================
# Actions (QR + Passport)
# ============================================================

@admin.action(description="✅ QR үүсгэх")
def generate_qr(modeladmin, request: HttpRequest, queryset: QuerySet[Device]):
    if not hasattr(Device, "qr_token"):
        modeladmin.message_user(request, "Device дээр qr_token талбар алга байна.", level=messages.WARNING)
        return

    base = request.build_absolute_uri("/")[:-1]
    n = 0

    for d in queryset:
        # token
        if not getattr(d, "qr_token", None):
            import uuid
            d.qr_token = uuid.uuid4()

        url = f"{base}{reverse('qr_device_public', args=[d.qr_token])}"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        serial = (getattr(d, "serial_number", "") or "").strip()
        base_name = slugify(serial)[:40] if serial else f"device_{d.pk}"
        filename = f"qr/devices/{base_name}_{d.qr_token}.png"

        if getattr(d, "qr_image", None) is not None:
            d.qr_image.save(filename, ContentFile(buf.getvalue()), save=False)

        update_fields = []
        for f in ("qr_token", "qr_image", "qr_revoked_at", "qr_expires_at"):
            if hasattr(d, f):
                update_fields.append(f)
        d.save(update_fields=update_fields or None)
        n += 1

    modeladmin.message_user(request, f"QR үүсгэлээ: {n} багаж", level=messages.SUCCESS)


@admin.action(description="⛔ QR хүчингүй болгох")
def revoke_qr(modeladmin, request: HttpRequest, queryset: QuerySet[Device]):
    if not hasattr(Device, "qr_revoked_at"):
        modeladmin.message_user(request, "Device дээр qr_revoked_at талбар алга байна.", level=messages.WARNING)
        return
    now = timezone.now()
    queryset.update(qr_revoked_at=now)
    modeladmin.message_user(request, f"QR хүчингүй болголоо: {queryset.count()} багаж", level=messages.SUCCESS)


@admin.action(description="📄 Device Passport (PDF) татах")
def download_device_passport(modeladmin, request: HttpRequest, queryset: QuerySet[Device]):
    if not generate_device_passport_pdf_bytes:
        modeladmin.message_user(request, "pdf_passport.generate_device_passport_pdf_bytes олдсонгүй.", level=messages.ERROR)
        return
    if queryset.count() != 1:
        modeladmin.message_user(request, "Нэг л төхөөрөмж сонгоод дахин оролдоорой.", level=messages.WARNING)
        return

    device = queryset.first()
    data = generate_device_passport_pdf_bytes(device, request=request)

    filename = f"device_passport_{device.pk}.pdf"
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ============================================================
# Admin classes
# ============================================================

class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    ordering = ("name",)


class SumDuuregAdmin(admin.ModelAdmin):
    # NOTE: SumDuureg model uses aimag_ref FK (not 'aimag').
    list_display = ("aimag_ref", "name")
    list_filter = ("aimag_ref",)
    search_fields = ("name", "aimag_ref__name")
    ordering = ("aimag_ref__name", "name")


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "aimag", "is_ub")
    list_filter = ("org_type", "is_ub", "aimag")
    search_fields = ("name", "aimag__name")
    ordering = ("aimag__name", "name")


class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "unit", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("kind", "code")


class LocationAdmin(admin.ModelAdmin):
    change_list_template = "inventory/admin/location_changelist_with_map.html"

    list_display = (
        "name",
        "location_type",
        "aimag_ref",
        "sum_ref",
        "owner_org",
        "wmo_index",
        "latitude",
        "longitude",
        "device_count_col",
        "pending_badge_col",
        "open_map_col",
    )
    list_filter = ("aimag_ref", SumDuuregByAimagFilter, LocationTypeFilter)
    search_fields = ("name", "code", "wmo_index")
    ordering = ("aimag_ref__name", "sum_ref__name", "name")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("aimag_ref", "sum_ref", "owner_org")

        # scope
        qs = _scope_qs(request, qs, aimag_field="aimag_ref")

        # counts (production-safe: FieldError гарвал 0 болгож fallback)
        qs = qs.annotate(device_count=Count("devices", distinct=True))

        try:
            PENDING_SET = ["SUBMITTED", "PENDING", "NEED_APPROVAL"]
            qs = qs.annotate(
                pending_maint=Count(
                    "devices__maintenanceservice",
                    filter=Q(devices__maintenanceservice__workflow_status__in=PENDING_SET),
                    distinct=True,
                ),
                pending_control=Count(
                    "devices__controladjustment",
                    filter=Q(devices__controladjustment__workflow_status__in=PENDING_SET),
                    distinct=True,
                ),
            )
        except FieldError:
            qs = qs.annotate(pending_maint=Count("pk") * 0, pending_control=Count("pk") * 0)

        return qs

    @admin.display(description="Багаж", ordering="device_count")
    def device_count_col(self, obj):
        return int(getattr(obj, "device_count", 0) or 0)

    @admin.display(description="Pending")
    def pending_badge_col(self, obj):
        pm = int(getattr(obj, "pending_maint", 0) or 0)
        pc = int(getattr(obj, "pending_control", 0) or 0)
        pt = pm + pc
        if pt <= 0:
            return format_html('<span style="color:#6b7280;">0</span>')
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'background:#f59e0b;color:#111827;font-weight:800;">{} Pending</span>',
            pt,
        )

    @admin.display(description="🗺️ Map")
    def open_map_col(self, obj):
        # ✅ map нь admin site дээр: /django-admin/map/
        url = reverse("admin:inventory_map") + f"?location_id={obj.pk}"
        return format_html('<a class="button" href="{}" target="_blank" rel="noopener">Нээх</a>', url)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    actions = [generate_qr, revoke_qr, download_device_passport]

    inlines = [MaintenanceHistoryInline, ControlHistoryInline]
    if DeviceMovementInline:
        inlines.append(DeviceMovementInline)

    list_display = (
        "serial_number",
        "kind",
        "status",
        "location",
        "qr_preview",
    )
    list_filter = ("kind", "status")
    search_fields = ("serial_number", "inventory_code", "other_name", "location__name")
    ordering = ("-id",)

    readonly_fields = (
        "qr_preview",
        "location_latitude",
        "location_longitude",
    )

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_filter_enterprise.js",
        )

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class RequestForm(Form):
            def __init__(self2, *args, **kw):
                kw["request"] = request
                super().__init__(*args, **kw)

        return RequestForm

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = (
            super()
            .get_queryset(request)
            .select_related("location", "location__aimag_ref", "location__sum_ref")
        )
        return _scope_qs(request, qs, aimag_field="location__aimag_ref")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "location":
            kwargs["queryset"] = _scope_location_qs(request).order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="QR")
    def qr_preview(self, obj: Device):
        img = getattr(obj, "qr_image", None)
        if img:
            try:
                return format_html(
                    '<img src="{}" style="height:64px;width:64px;object-fit:contain;border:1px solid #ddd;border-radius:6px;" />',
                    img.url,
                )
            except Exception:
                pass

        tok = getattr(obj, "qr_token", None)
        if tok:
            return format_html("<code>{}</code>", tok)

        return "-"

    @admin.display(description="Өргөрөг")
    def location_latitude(self, obj):
        if obj and obj.location:
            return getattr(obj.location, "latitude", "-")
        return "-"

    @admin.display(description="Уртраг")
    def location_longitude(self, obj):
        if obj and obj.location:
            return getattr(obj.location, "longitude", "-")
        return "-"

    def passport_view(self, request: HttpRequest, object_id: int):
        from .pdf_passport import generate_device_passport_pdf_bytes

        device = get_object_or_404(Device, pk=object_id)
        data = generate_device_passport_pdf_bytes(device, request=request)
        if not data:
            return HttpResponse("PDF generator not available", status=500)

        filename = f"device_passport_{device.pk}.pdf"
        resp = HttpResponse(data, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp

    def catalog_by_kind_view(self, request: HttpRequest):
        kind = (request.GET.get("kind") or "").strip().upper()
        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)

        return JsonResponse(
            {"results": [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]},
            json_dumps_params={"ensure_ascii": False},
        )

    def location_options_view(self, request: HttpRequest):
        raw_aimag_id = (request.GET.get("aimag") or "").strip()
        raw_sum_id = (request.GET.get("sum") or "").strip()

        try:
            aimag_id = int(raw_aimag_id) if raw_aimag_id else None
        except (TypeError, ValueError):
            aimag_id = None

        try:
            sum_id = int(raw_sum_id) if raw_sum_id else None
        except (TypeError, ValueError):
            sum_id = None

        qs = _scope_location_qs(request).order_by("name")

        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)

        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)

        data = [{"id": l.id, "name": l.name} for l in qs[:500]]
        return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})

    def load_sums_view(self, request: HttpRequest):
        raw_aimag_id = (request.GET.get("aimag_id") or "").strip()

        try:
            aimag_id = int(raw_aimag_id) if raw_aimag_id else None
        except (TypeError, ValueError):
            aimag_id = None

        if not aimag_id:
            return JsonResponse([], safe=False, json_dumps_params={"ensure_ascii": False})

        qs = SumDuureg.objects.filter(aimag_ref_id=aimag_id).order_by("name")
        data = [{"id": s.id, "name": s.name} for s in qs]
        return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "catalog-by-kind/",
                self.admin_site.admin_view(self.catalog_by_kind_view),
                name="device_catalog_by_kind",
            ),
            path(
                "location-options/",
                self.admin_site.admin_view(self.location_options_view),
                name="device_location_options",
            ),
            path(
                "load-sums/",
                self.admin_site.admin_view(self.load_sums_view),
                name="device_load_sums",
            ),
            path(
                "<path:object_id>/passport/",
                self.admin_site.admin_view(self.passport_view),
                name="device_passport_view",
            ),
        ]
        return custom + urls

    fieldsets = (
        ("Ерөнхий мэдээлэл", {
            "fields": (
                "catalog_item",
                "other_name",
                "serial_number",
                "inventory_code",
                "kind",
                "system",
                "status",
                "installation_date",
                "lifespan_years",
            )
        }),
        ("Байршил", {
            "fields": (
                "admin_aimag",
                "admin_sum",
                "location",
                "location_latitude",
                "location_longitude",
            )
        }),
        ("QR", {
            "fields": (
                "qr_image",
                "qr_preview",
            )
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class MaintenanceServiceAdmin(admin.ModelAdmin):
    list_display = (
        "date", 
        "device", 
        "reason", 
        "workflow_status", 
        "performer_type", 
        "performer_engineer_name", 
        "performer_org_name"
    )
    list_filter = ("reason", "workflow_status", "performer_type")
    search_fields = (
        "device__serial_number", 
        "device__inventory_code", 
        "note"
    )
    ordering = ("-date", "-id")
    inlines = [MaintenanceEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related(
            "device", 
            "device__location", 
            "device__location__aimag_ref", 
            "device__location__sum_ref"
        )
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
class ControlAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("date", "device", "result", "workflow_status", "performer_type", "performer_engineer_name", "performer_org_name")
    list_filter = ("result", "workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "note")
    ordering = ("-date", "-id")
    inlines = [ControlEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location", "device__location__aimag_ref", "device__location__sum_ref")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "aimag", "status", "created_at")
    list_filter = ("status", "aimag")
    search_fields = ("order_no",)
    ordering = ("-created_at", "-id")
    fieldsets = (
        ("Ерөнхий мэдээлэл", {
            "fields": ("order_no", "aimag", "status"),
        }),
    )
    inlines = [SparePartItemInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        return _scope_qs(request, qs, aimag_field="aimag")


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "org", "must_change_password")
    list_filter = ("aimag", "must_change_password")
    search_fields = ("user__username", "user__email", "org__name", "aimag__name")
    ordering = ("user__username",)


class AuthAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "username", "user", "ip_address")
    list_filter = ("action",)
    search_fields = ("username", "user__username", "ip_address", "user_agent")
    ordering = ("-created_at", "-id")


# ============================================================
# ✅ Register logic (Файлын төгсгөлд байрлана)
# ============================================================
from django.contrib.admin.sites import AlreadyRegistered

def register_with(site):
    """Бүх моделиудыг заасан админ сайт руу бүртгэх функц"""
    models_to_register = [
        (Aimag, AimagAdmin),
        (SumDuureg, SumDuuregAdmin),
        (Organization, OrganizationAdmin),
        (Location, LocationAdmin),
        (InstrumentCatalog, InstrumentCatalogAdmin),
        (Device, DeviceAdmin),
        (MaintenanceService, MaintenanceServiceAdmin),
        (ControlAdjustment, ControlAdjustmentAdmin),
        (SparePartOrder, SparePartOrderAdmin),
        (UserProfile, UserProfileAdmin),
        (AuthAuditLog, AuthAuditLogAdmin),
    ]

    for model, admin_class in models_to_register:
        try:
            site.register(model, admin_class)
        except AlreadyRegistered:
            pass

    # AuditEvent бүртгэл (байвал)
    if AuditEvent is not None:
        try:
            class AuditEventAdmin(admin.ModelAdmin):
                ordering = ("-id",)
                list_display = ("id", "created_at") if hasattr(AuditEvent, "created_at") else ("id",)
                search_fields = ("id",)
                
            site.register(AuditEvent, AuditEventAdmin)
        except AlreadyRegistered:
            pass

# ✅ ХАМГИЙН СҮҮЛД: Бүх зүйл зарлагдсаны дараа бүртгэлийг эхлүүлнэ
register_with(inventory_admin_site)