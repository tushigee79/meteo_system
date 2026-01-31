# inventory/admin.py (production-ready) - 2026-01-31
from __future__ import annotations

import io
import json
import logging
import uuid
import zipfile
from datetime import date, timedelta
from typing import Any, Dict, Optional

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db.models import Count, Q, QuerySet
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify

from . import views_admin_workflow as wf
from .device_passport_pdf import generate_device_passport_pdf
from .pdf_passport import generate_device_passport_pdf_bytes
from .reports_hub import (
    reports_hub_view,
    reports_chart_json,
    reports_sums_by_aimag,
    reports_export_csv,  # legacy (devices)
    reports_export_devices_csv,
    reports_export_locations_csv,
    reports_export_maintenance_csv,
    reports_export_control_csv,
    reports_export_movements_csv,
    reports_export_spareparts_csv,
    reports_export_auth_audit_csv,
)
from .models import (
    Aimag,
    SumDuureg,
    Organization,
    Location,
    InstrumentCatalog,
    Device,
    DeviceMovement,
    MaintenanceService,
    ControlAdjustment,
    MaintenanceEvidence,
    ControlEvidence,
    SparePartOrder,
    SparePartItem,
    UserProfile,
    AuthAuditLog,
)

# Optional model (if exists in your branch)
try:
    from .models import AuditEvent  # type: ignore
except Exception:  # pragma: no cover
    AuditEvent = None  # type: ignore

logger = logging.getLogger(__name__)


# ============================================================
# QR Actions (lazy-import qrcode)
# ============================================================

@admin.action(description="🔳 QR үүсгэх / шинэчлэх")
def generate_qr(modeladmin, request: HttpRequest, queryset: QuerySet):
    """Selected device-үүдэд QR token + зураг (PNG) үүсгэнэ/шинэчилнэ.

    ⚠️ qrcode сан суусан байх ёстой:
        pip install qrcode[pil]
    """
    try:
        import qrcode  # type: ignore
        from qrcode.constants import ERROR_CORRECT_M  # type: ignore
    except Exception:
        modeladmin.message_user(
            request,
            "QR үүсгэхэд шаардлагатай 'qrcode[pil]' сан суусангүй. "
            "Terminal дээр: pip install qrcode[pil]",
            level=messages.ERROR,
        )
        return

    for d in queryset:
        # token
        if not getattr(d, "qr_token", None):
            d.qr_token = uuid.uuid4()

        # activate flags if fields exist
        if hasattr(d, "qr_revoked_at"):
            d.qr_revoked_at = None
        if hasattr(d, "qr_expires_at"):
            d.qr_expires_at = timezone.now() + timedelta(days=365)

        # URL (respects app namespace)
        try:
            rel = reverse("inventory:qr_device_lookup", args=[d.qr_token])
        except Exception:
            rel = f"/qr/device/{d.qr_token}/"
        url = request.build_absolute_uri(rel)

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
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

        # save only existing fields
        update_fields = []
        for f in ("qr_token", "qr_image", "qr_revoked_at", "qr_expires_at"):
            if hasattr(d, f):
                update_fields.append(f)
        d.save(update_fields=update_fields or None)

    modeladmin.message_user(request, f"QR үүсгэлээ: {queryset.count()} багаж", level=messages.SUCCESS)


@admin.action(description="⛔ QR хүчингүй болгох")
def revoke_qr(modeladmin, request: HttpRequest, queryset: QuerySet):
    if not hasattr(Device, "qr_revoked_at"):
        modeladmin.message_user(request, "Device дээр qr_revoked_at талбар алга байна.", level=messages.WARNING)
        return
    now = timezone.now()
    queryset.update(qr_revoked_at=now)
    modeladmin.message_user(request, f"QR хүчингүй болголоо: {queryset.count()} багаж", level=messages.SUCCESS)


# ============================================================
# Helpers
# ============================================================

def get_ub_aimag_id() -> Optional[int]:
    """Return Ulaanbaatar Aimag ID without hardcoding. Cached."""
    key = "inventory:ub_aimag_id:v1"
    v = cache.get(key)
    if v is not None:
        return int(v) if v else None
    try:
        ub = Aimag.objects.get(name__icontains="улаанбаатар")
        cache.set(key, int(ub.id), 86400)
        return int(ub.id)
    except Exception:
        logger.warning("UB aimag not found by name__icontains='улаанбаатар'.")
        cache.set(key, 0, 3600)
        return None


def _get_scope(request: HttpRequest) -> Dict[str, Any]:
    """Аймгийн инженер -> зөвхөн өөрийн аймаг (мөн УБ бол дүүргээр нарийвчилж болно)."""
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

    # UB district narrowing (optional)
    ub_id = get_ub_aimag_id()
    sum_id = scope.get("sum_id")
    if ub_id is not None and aimag_id == ub_id and sum_id:
        # if qs model has sum_ref_id (Location)
        if hasattr(qs.model, "sum_ref_id"):
            qs = qs.filter(sum_ref_id=sum_id)
    return qs


def _scope_location_qs(request: HttpRequest) -> QuerySet[Location]:
    qs = Location.objects.all()
    scope = _get_scope(request)
    if scope["all"]:
        return qs
    if not scope["aimag_id"]:
        return qs.none()
    qs = qs.filter(aimag_ref_id=scope["aimag_id"])
    ub_id = get_ub_aimag_id()
    if ub_id is not None and scope["aimag_id"] == ub_id and scope["sum_id"]:
        qs = qs.filter(sum_ref_id=scope["sum_id"])
    return qs


def _device_next_verif_field() -> Optional[str]:
    """Return the best field name for next verification date if it exists."""
    candidates = ("next_verification_date", "next_calibration_date", "next_verif_date")
    try:
        names = {f.name for f in Device._meta.get_fields()}
    except Exception:
        names = set()
    for c in candidates:
        if c in names:
            return c
    return None


# ============================================================
# Filters
# ============================================================

class SumDuuregByAimagFilter(admin.SimpleListFilter):
    title = "Сум/Дүүрэг"
    parameter_name = "sum_ref__id__exact"

    def lookups(self, request, model_admin):
        aimag_id = (request.GET.get("aimag_ref__id__exact") or "").strip()
        if not aimag_id:
            return []
        qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name")

        # If model has is_ub_district and aimag is UB, show only districts; else show non-district sums.
        try:
            ub_id = get_ub_aimag_id()
            is_ub = (ub_id is not None and str(ub_id) == str(aimag_id))
            if hasattr(SumDuureg, "is_ub_district"):
                qs = qs.filter(is_ub_district=True) if is_ub else qs.filter(is_ub_district=False)
        except Exception:
            pass

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
        if not v:
            return queryset
        return queryset.filter(location_type=v)


class VerificationBucketFilter(admin.SimpleListFilter):
    """Expired / 30 / 90 bucket filter based on Device.<next_verification_date>."""
    title = "Калибровка"
    parameter_name = "verification"

    def lookups(self, request, model_admin):
        return (
            ("expired", "⛔ Дууссан"),
            ("due_30", "⚠️ 30 хоногт дуусах"),
            ("due_90", "🔵 90 хоногт дуусах"),
            ("ok", "✅ Хэвийн"),
            ("unknown", "❓ Огноо байхгүй"),
        )

    def queryset(self, request, queryset):
        field = _device_next_verif_field()
        if not field:
            return queryset  # no-op if field doesn't exist

        val = self.value()
        if not val:
            return queryset

        today = timezone.localdate()

        if val == "unknown":
            return queryset.filter(**{f"{field}__isnull": True})

        if val == "expired":
            return queryset.filter(**{f"{field}__isnull": False, f"{field}__lt": today})

        if val == "due_30":
            return queryset.filter(
                **{
                    f"{field}__isnull": False,
                    f"{field}__gte": today,
                    f"{field}__lte": today + timedelta(days=30),
                }
            )

        if val == "due_90":
            return queryset.filter(
                **{
                    f"{field}__isnull": False,
                    f"{field}__gte": today,
                    f"{field}__lte": today + timedelta(days=90),
                }
            )

        if val == "ok":
            return queryset.filter(**{f"{field}__isnull": False, f"{field}__gt": today + timedelta(days=90)})

        return queryset


# ============================================================
# Device Passport action (PDF / ZIP)
# ============================================================

@admin.action(description="📄 Техник паспорт (PDF/ZIP)")
def download_device_passport(modeladmin, request: HttpRequest, queryset: QuerySet):
    devices = list(queryset)
    if not devices:
        return None

    # ✅ Single device -> PDF
    if len(devices) == 1:
        d = devices[0]
        pdf_bytes = generate_device_passport_pdf_bytes(d)
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="device_passport_{d.pk}.pdf"'
        return resp

    # ✅ Multi-select -> ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in devices:
            try:
                pdf_bytes = generate_device_passport_pdf_bytes(d)
                serial = (getattr(d, "serial_number", "") or "").strip()
                base = f"{d.pk}"
                if serial:
                    base = f"{d.pk}_{slugify(serial)[:40]}"
                zf.writestr(f"device_passport_{base}.pdf", pdf_bytes)
            except Exception:
                logger.exception("Passport PDF failed for device_id=%s", getattr(d, "pk", None))

    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = 'attachment; filename="device_passports.zip"'
    return resp


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


class DeviceMovementInline(admin.TabularInline):
    model = DeviceMovement
    extra = 0
    can_delete = False
    show_change_link = False
    readonly_fields = ("moved_at", "from_location", "to_location", "reason", "moved_by")
    fields = readonly_fields
    ordering = ("-moved_at", "-id")


class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1


# ============================================================
# Admin classes
# ============================================================

class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    ordering = ("name",)


class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("aimag", "name")
    list_filter = ("aimag",)
    search_fields = ("name", "aimag__name")
    ordering = ("aimag__name", "name")


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
        "district_name",
        "owner_org",
        "wmo_index",
        "latitude",
        "longitude",
        "device_count_col",
        "view_map_col",
    )

    list_filter = (
        "aimag_ref",
        SumDuuregByAimagFilter,
        LocationTypeFilter,
    )
    search_fields = ("name", "code", "wmo_index", "aimag_ref__name", "sum_ref__name", "owner_org__name")
    ordering = ("aimag_ref__name", "sum_ref__name", "name")

    class Media:
        js = ("inventory/js/admin/location_add_cascade.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("aimag_ref", "sum_ref", "owner_org")

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

    @admin.display(description="Багаж", ordering="device_count")
    def device_count_col(self, obj: Location):
        return int(getattr(obj, "device_count", 0) or 0)

    @admin.display(description="🗺 Харах")
    def view_map_col(self, obj: Location):
        try:
            url = reverse(f"{self.admin_site.name}:inventory_location_map_one", args=[obj.pk])
            return format_html('<a class="button" href="{}">Харах</a>', url)
        except Exception:
            return "-"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "sums-by-aimag/",
                self.admin_site.admin_view(self.sums_by_aimag_view),
                name="location_sums_by_aimag",
            ),
            path(
                "map/",
                self.admin_site.admin_view(self.map_view),
                name="inventory_location_map",
            ),
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
        results = [{"id": s.id, "name": s.name, "text": s.name} for s in qs]
        return JsonResponse({"results": results})

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
                    "kind": (o.location_type or "OTHER"),
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
                    "loc_admin_url": reverse(f"{self.admin_site.name}:inventory_location_change", args=[o.id]),
                    "device_list_url": reverse(f"{self.admin_site.name}:inventory_device_changelist") + f"?location__id__exact={o.id}",
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


class DeviceAdminForm(forms.ModelForm):
    """Admin form нэмэлт талбар: location өөрчлөх үед movement reason хадгална."""
    movement_reason = forms.CharField(
        label="Шилжилтийн шалтгаан",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ж: Эвдэрсэн тул нөөц станц руу шилжүүлэв"}),
        help_text="Зөвхөн байршил өөрчлөгдөх үед DeviceMovement түүхэнд хадгалагдана.",
    )

    class Meta:
        model = Device
        fields = "__all__"


class DeviceMovementAdmin(admin.ModelAdmin):
    date_hierarchy = "moved_at"
    list_display = ("moved_at", "device", "device_kind", "from_location", "to_location", "aimag_col", "reason", "moved_by")
    list_select_related = ("device", "from_location", "to_location", "to_location__aimag_ref")
    list_filter = (("moved_at", admin.DateFieldListFilter), "device__kind", "to_location__aimag_ref")
    search_fields = ("device__serial_number", "reason")
    ordering = ("-moved_at", "-id")
    autocomplete_fields = ("device", "from_location", "to_location", "moved_by")

    @admin.display(description="Төрөл")
    def device_kind(self, obj: DeviceMovement):
        try:
            return obj.device.kind
        except Exception:
            return ""

    @admin.display(description="Аймаг")
    def aimag_col(self, obj: DeviceMovement):
        try:
            loc = obj.to_location or obj.from_location
            return getattr(getattr(loc, "aimag_ref", None), "name", "") if loc else ""
        except Exception:
            return ""


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """
    Device admin (production-ready):
    - QR preview
    - QR actions
    - Device passport (action + per-device view)
    - Movement auto-log via movement_reason
    - Calibration warning badge + VerificationBucketFilter
    """

    form = DeviceAdminForm
    actions = [generate_qr, revoke_qr, download_device_passport]

    inlines = [MaintenanceHistoryInline, ControlHistoryInline, DeviceMovementInline]

    list_display = (
        "serial_number",
        "kind",
        "status",
        "location",
        "verification_badge",
        "qr_preview",
    )
    list_filter = ("kind", "status", VerificationBucketFilter)
    search_fields = ("serial_number", "inventory_code", "other_name", "location__name")
    ordering = ("-id",)

    readonly_fields = ("qr_preview",)

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_filter_enterprise.js",
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("location", "location__aimag_ref", "location__sum_ref")
        return _scope_qs(request, qs, aimag_field="location__aimag_ref")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "location":
            kwargs["queryset"] = _scope_location_qs(request).order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="QR")
    def qr_preview(self, obj: Device):
        img = getattr(obj, "qr_image", None)
        if not img:
            return "-"
        try:
            url = img.url
        except Exception:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" style="height:48px;border:1px solid #ccc;border-radius:4px" />'
            "</a>",
            url,
            url,
        )

    @admin.display(description="Калибровка")
    def verification_badge(self, obj: Device):
        field = _device_next_verif_field()
        if not field:
            return format_html('<span style="color:#666">—</span>')

        d = getattr(obj, field, None)
        if not d:
            return format_html('<span style="color:#6c757d;font-weight:600">❓ Огноо байхгүй</span>')

        today = timezone.localdate()
        if d < today:
            return format_html('<span style="color:#dc3545;font-weight:700">⛔ Дууссан</span>')

        left = (d - today).days
        left_i = int(left or 0)

        if left_i <= 30:
            return format_html(
                '<span style="color:#fd7e14;font-weight:700">⚠️ ≤30 ({} өдөр)</span>',
                left_i,
            )
        if left_i <= 90:
            return format_html(
                '<span style="color:#0d6efd;font-weight:700">🔵 ≤90 ({} өдөр)</span>',
                left_i,
            )

        return format_html(
            '<span style="color:#198754;font-weight:700">✅ OK ({} өдөр)</span>',
            left_i,
        )



    def get_urls(self):
        urls = super().get_urls()
        custom = [
            # ✅ Template: opts|admin_urlname:'passport'
            path(
                "<int:object_id>/passport/",
                self.admin_site.admin_view(self.passport_view),
                name="inventory_device_passport",
            ),
            # Dynamic selects
            path("catalog-by-kind/", self.admin_site.admin_view(self.catalog_by_kind_view), name="device_catalog_by_kind"),
            path("location-options/", self.admin_site.admin_view(self.location_options_view), name="device_location_options"),
        ]
        return custom + urls

    def passport_view(self, request: HttpRequest, object_id: int):
        device = get_object_or_404(Device, pk=object_id)
        pdf_obj = generate_device_passport_pdf(device, request=request)

        if hasattr(pdf_obj, "read"):
            fp = pdf_obj
            try:
                fp.seek(0)
            except Exception:
                pass
        else:
            fp = io.BytesIO(pdf_obj)
            fp.seek(0)

        filename = f"device_passport_{(device.serial_number or device.pk)}.pdf"
        return FileResponse(fp, as_attachment=True, filename=filename, content_type="application/pdf")

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

    def save_model(self, request: HttpRequest, obj: Device, form, change: bool) -> None:
        old_loc_id = None
        if change and obj.pk:
            try:
                old_loc_id = Device.objects.filter(pk=obj.pk).values_list("location_id", flat=True).first()
            except Exception:
                old_loc_id = None

        super().save_model(request, obj, form, change)

        # movement auto-log
        try:
            new_loc_id = obj.location_id
            if change and old_loc_id != new_loc_id:
                prof = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
                moved_by = getattr(prof, "pk", None)
                reason = ""
                try:
                    reason = (form.cleaned_data.get("movement_reason") or "").strip()
                except Exception:
                    reason = ""
                DeviceMovement.objects.create(
                    device=obj,
                    from_location_id=old_loc_id,
                    to_location_id=new_loc_id,
                    moved_by_id=moved_by,
                    reason=reason,
                )
        except Exception:
            logger.exception("DeviceMovement auto-log failed for device_id=%s", obj.pk)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class MaintenanceServiceAdmin(admin.ModelAdmin):
    list_display = ("date", "device", "workflow_status", "performer_type", "performer_engineer_name", "performer_org_name")
    list_filter = ("workflow_status", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "reason", "note")
    ordering = ("-date", "-id")
    inlines = [MaintenanceEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related("device", "device__location", "device__location__aimag_ref", "device__location__sum_ref")
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


if AuditEvent is not None:
    class AuditEventAdmin(admin.ModelAdmin):
        list_display = ("created_at", "actor", "action", "model_label", "object_id", "ip_address")
        list_filter = ("action", "model_label")
        search_fields = ("actor__username", "action", "model_label", "object_id", "object_repr", "ip_address")
        ordering = ("-created_at", "-id")
else:
    AuditEventAdmin = None  # type: ignore


# ============================================================
# Custom AdminSite (/django-admin/) — ReportsHub + Workflow URLs
# ============================================================

class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ - Админ"
    site_title = "БҮРТГЭЛ"
    index_title = "Удирдлага"

    def get_urls(self):
        urls = super().get_urls()

        custom = [
            # ReportsHub UI
            path("reports/", self.admin_view(reports_hub_view), name="reports-hub"),
            path("reports/chart.json/", self.admin_view(reports_chart_json), name="reports-chart-json"),
            path("reports/sums.json/", self.admin_view(reports_sums_by_aimag), name="reports-sums-json"),

            # WORKFLOW (admin-only)
            path("inventory/workflow/pending/", self.admin_view(wf.workflow_pending_dashboard), name="workflow_pending_dashboard"),
            path("inventory/workflow/pending-counts/", self.admin_view(wf.workflow_pending_counts), name="workflow_pending_counts"),
            path("inventory/workflow/review/", self.admin_view(wf.workflow_review_action), name="workflow_review_action"),
            path("inventory/workflow/audit/", self.admin_view(wf.workflow_audit_log), name="workflow_audit_log"),

            # Exports
            path("reports/export/devices.csv", self.admin_view(reports_export_devices_csv), name="reports-export-devices-csv"),
            path("reports/export/locations.csv", self.admin_view(reports_export_locations_csv), name="reports-export-locations-csv"),
            path("reports/export/maintenance.csv", self.admin_view(reports_export_maintenance_csv), name="reports-export-maintenance-csv"),
            path("reports/export/control.csv", self.admin_view(reports_export_control_csv), name="reports-export-control-csv"),
            path("reports/export/movements.csv", self.admin_view(reports_export_movements_csv), name="reports-export-movements-csv"),
            path("reports/export/spareparts.csv", self.admin_view(reports_export_spareparts_csv), name="reports-export-spareparts-csv"),
            path("reports/export/auth_audit.csv", self.admin_view(reports_export_auth_audit_csv), name="reports-export-auth-audit-csv"),
            path("reports/export.csv/", self.admin_view(reports_export_csv), name="reports-export-csv"),
        ]

        return custom + urls


# ✅ singleton instance (imported by meteo_config/urls.py)
inventory_admin_site = InventoryAdminSite(name="inventory_admin")

# ============================================================
# Register ALL admins to the custom site
# ============================================================
inventory_admin_site.register(Aimag, AimagAdmin)
inventory_admin_site.register(SumDuureg, SumDuuregAdmin)
inventory_admin_site.register(Organization, OrganizationAdmin)
inventory_admin_site.register(InstrumentCatalog, InstrumentCatalogAdmin)
inventory_admin_site.register(Location, LocationAdmin)
inventory_admin_site.register(DeviceMovement, DeviceMovementAdmin)
inventory_admin_site.register(Device, DeviceAdmin)
inventory_admin_site.register(MaintenanceService, MaintenanceServiceAdmin)
inventory_admin_site.register(ControlAdjustment, ControlAdjustmentAdmin)
inventory_admin_site.register(SparePartOrder, SparePartOrderAdmin)
inventory_admin_site.register(UserProfile, UserProfileAdmin)
inventory_admin_site.register(AuthAuditLog, AuthAuditLogAdmin)
if AuditEvent is not None and AuditEventAdmin is not None:
    inventory_admin_site.register(AuditEvent, AuditEventAdmin)
