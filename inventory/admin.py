# inventory/admin.py (production-ready)
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
from .views_dashboard_general import general_dashboard_view
from django.contrib import messages
from django.utils import timezone
from . import views_admin_workflow as wf
from . import views_admin as va
from . import admin_dashboard
from . import views_admin as views



from .pdf_passport import generate_device_passport_pdf_bytes

# ✅ Тайлан/Reports: нэг л газраас импортло (давхардуулахгүй)
from .reports_hub_compat import (
    reports_hub_view,
    reports_chart_json,
    reports_sums_by_aimag,
    reports_export_devices_csv,
    reports_export_locations_csv,
    reports_export_maintenance_csv,
    reports_export_control_csv,
    reports_export_movements_csv,
    reports_export_spareparts_csv,
    reports_export_auth_audit_csv,
    reports_table_json,
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

KIND_TO_LOCATION_TYPE = {
    "WEATHER": ["WEATHER", "METEO"],
    "HYDRO": ["HYDRO"],
    "AWS": ["AWS"],
    "RADAR": ["RADAR"],
    "AEROLOGY": ["AEROLOGY"],
    "AGRO": ["AGRO"],
    "ETALON": ["ETALON"],
    "OTHER": ["OTHER"],
}

# Optional model (if exists in your branch)
try:
    from .models import AuditEvent  # type: ignore
except Exception:  # pragma: no cover
    AuditEvent = None  # type: ignore


def _model_field_names(model) -> set[str]:
    try:
        return {f.name for f in model._meta.get_fields() if hasattr(f, "name")}
    except Exception:
        return set()


def _add_if_exists(dst: list[str], names: set[str], *candidates: str) -> None:
    for c in candidates:
        if c in names:
            dst.append(c)
            return


def _add_search(dst: list[str], names: set[str], *candidates: str) -> None:
    """
    Search fields are either direct fields or FK traversals (e.g. actor__username).
    We'll only add FK traversals if base FK exists.
    """
    for c in candidates:
        if "__" in c:
            base = c.split("__", 1)[0]
            if base in names:
                dst.append(c)
                return
        else:
            if c in names:
                dst.append(c)
                return


if AuditEvent is not None:
    _AE_FIELDS = _model_field_names(AuditEvent)

    # --- list_display: хамгийн нийтлэг + хамгийн хэрэгтэйг боломжтой үед нь
    _ld: list[str] = []

    # time
    _add_if_exists(_ld, _AE_FIELDS, "created_at", "timestamp", "time", "created", "occurred_at")
    # actor/user
    _add_if_exists(_ld, _AE_FIELDS, "actor", "user", "created_by", "performed_by")
    # action/event
    _add_if_exists(_ld, _AE_FIELDS, "action", "event", "event_type", "verb")
    # model/object pointers
    _add_if_exists(_ld, _AE_FIELDS, "model_label", "content_type", "model", "model_name")
    _add_if_exists(_ld, _AE_FIELDS, "object_id", "obj_id", "target_id")
    _add_if_exists(_ld, _AE_FIELDS, "ip_address", "ip", "remote_addr")

    # Хэрвээ хоосон бол дор хаяж id-г үзүүлнэ
    if not _ld:
        _ld = ["id"] if "id" in _AE_FIELDS else []

    # --- list_filter
    _lf: list[str] = []
    _add_if_exists(_lf, _AE_FIELDS, "action", "event", "event_type", "verb")
    _add_if_exists(_lf, _AE_FIELDS, "model_label", "content_type", "model", "model_name")
    _add_if_exists(_lf, _AE_FIELDS, "created_at", "timestamp", "time", "created", "occurred_at")

    # --- search_fields (FK traversals + direct text fields)
    _sf: list[str] = []
    # actor/user name traversals (only if base FK exists)
    _add_search(_sf, _AE_FIELDS, "actor__username", "actor__email", "actor__first_name", "actor__last_name")
    _add_search(_sf, _AE_FIELDS, "user__username", "user__email", "user__first_name", "user__last_name")
    _add_search(_sf, _AE_FIELDS, "created_by__username", "performed_by__username")

    # direct fields
    _add_search(_sf, _AE_FIELDS, "action", "event", "event_type", "verb")
    _add_search(_sf, _AE_FIELDS, "model_label", "model", "model_name")
    _add_search(_sf, _AE_FIELDS, "object_id", "obj_id", "target_id")
    _add_search(_sf, _AE_FIELDS, "object_repr", "obj_repr", "target_repr", "message", "detail", "payload")
    _add_search(_sf, _AE_FIELDS, "ip_address", "ip", "remote_addr")

    # --- ordering
    _ord: tuple[str, ...] = ()
    if "created_at" in _AE_FIELDS:
        _ord = ("-created_at", "-id") if "id" in _AE_FIELDS else ("-created_at",)
    elif "timestamp" in _AE_FIELDS:
        _ord = ("-timestamp", "-id") if "id" in _AE_FIELDS else ("-timestamp",)
    elif "time" in _AE_FIELDS:
        _ord = ("-time", "-id") if "id" in _AE_FIELDS else ("-time",)
    else:
        _ord = ("-id",) if "id" in _AE_FIELDS else ()

    class AuditEventAdmin(admin.ModelAdmin):
        list_display = tuple(_ld)
        list_filter = tuple(_lf)
        search_fields = tuple(_sf)
        ordering = _ord

    
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
    
@admin.action(description="Workflow → Submit (DRAFT → SUBMITTED)")
def submit_maintenance_to_workflow(modeladmin, request, queryset):
    qs = queryset.filter(workflow_status=WorkflowStatus.DRAFT)
    n = qs.update(
        workflow_status=WorkflowStatus.SUBMITTED,
        submitted_at=timezone.now(),
    )
    messages.success(request, f"{n} maintenance хүсэлт SUBMITTED боллоо.")


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
    change_form_template = "admin/inventory/workflow_change_form.html"
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

def response_change(self, request, obj):
    if request.POST.get("_submit_to_workflow") == "1" and obj.workflow_status == WorkflowStatus.DRAFT:
        obj.workflow_status = WorkflowStatus.SUBMITTED
        if hasattr(obj, "submitted_at"):
            obj.submitted_at = timezone.now()
        obj.save()
        self.message_user(request, "Workflow → SUBMITTED боллоо.", level=messages.SUCCESS)
    return super().response_change(request, obj)

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
        "name", "location_type", "aimag_ref", "sum_ref", "owner_org", 
        "wmo_index", "latitude", "longitude", "device_count_col"
    )
    list_filter = ("aimag_ref", SumDuuregByAimagFilter, LocationTypeFilter)
    search_fields = ("name", "code", "wmo_index")

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(
            device_count=Count("devices", distinct=True),
            pending_total=Count("devices__maintenance_services", filter=Q(devices__maintenance_services__workflow_status="SUBMITTED"), distinct=True) +
                          Count("devices__control_adjustments", filter=Q(devices__control_adjustments__workflow_status="SUBMITTED"), distinct=True)
        )
        return _scope_qs(request, qs, aimag_field="aimag_ref")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("sums-by-aimag/", self.admin_site.admin_view(self.sums_by_aimag_view), name="locations-sums-by-aimag"),
            path("map/", self.admin_site.admin_view(self.map_view), name="inventory_location_map"),
            path("<int:location_id>/map-one/", self.admin_site.admin_view(self.map_one_view), name="inventory_location_map_one"),
        ]
        return custom + urls

    @staticmethod
    def _safe_int(v):
        try:
            return int(v)
        except Exception:
            return None

    def sums_by_aimag_view(self, request):
        aimag_id = self._safe_int(request.GET.get("aimag_id"))
        qs = SumDuureg.objects.all()
        if aimag_id:
            qs = qs.filter(aimag_id=aimag_id)
        qs = qs.order_by("name")
        results = [{"id": s.id, "text": s.name} for s in qs]
        return JsonResponse({"results": results})

    def _build_locations_payload(self, qs):
        items = []
        for o in qs:
            if o.latitude and o.longitude:
                items.append({"id": o.id, "name": o.name, "lat": float(o.latitude), "lon": float(o.longitude)})
        return items

    def map_view(self, request):
        ctx = dict(
            self.admin_site.each_context(request),
            locations_json=json.dumps(self._build_locations_payload(self.get_queryset(request))),
        )
        return render(request, "inventory/location_map.html", ctx)

    def map_one_view(self, request, location_id):
        qs = self.get_queryset(request).filter(id=location_id)
        ctx = dict(
            self.admin_site.each_context(request),
            locations_json=json.dumps(self._build_locations_payload(qs)),
            focus_id=location_id,
        )
        return render(request, "inventory/location_map.html", ctx)

    
    @admin.display(description="Багаж")
    def device_count_col(self, obj): return getattr(obj, "device_count", 0)

# inventory/admin.py

# inventory/admin.py

# 1. Форм тодорхойлох (NameError-оос сэргийлнэ)
class DeviceAdminForm(forms.ModelForm):
    movement_reason = forms.CharField(
        label="Шилжилтийн шалтгаан",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ж: Эвдэрсэн тул нөөц станц руу шилжүүлэв"}),
        help_text="Зөвхөн байршил өөрчлөгдөх үед DeviceMovement түүхэнд хадгалагдана."
    )

    class Meta:
        model = Device
        fields = "__all__"

class DeviceAdmin(admin.ModelAdmin):
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

    def get_urls(self):
        urls = super().get_urls()
        # Давхардлыг арилгаж, нэршлийг темплэйттэй нийцүүлэв
        custom = [
            path(
                "subcategory-options/", 
                self.admin_site.admin_view(self.catalog_by_kind_view), 
                name="instrumentcatalog_subcategory_options"
            ),
            path(
                "sums-by-aimag/", 
                self.admin_site.admin_view(self.sums_by_aimag_view), 
                name="device_sums_by_aimag"
            ),
            path(
                "location-options/", 
                self.admin_site.admin_view(self.location_options_view), 
                name="device_location_options"
            ),
            path(
                "reports/", 
                self.admin_site.admin_view(wf.reports_hub_view), 
                name="reports-hub"
            ),
            path(
                "<int:object_id>/passport/",
                self.admin_site.admin_view(self.passport_view),
                name="inventory_device_passport",
            ),
            path(
                "instrumentcatalog/subcategory-options/",
                self.admin_view,
                name="instrumentcatalog_subcategory_options",
            ),
        ]
        return custom + urls

    # --- AJAX View функцүүд ---

    def catalog_by_kind_view(self, request: HttpRequest):
        """Төхөөрөмжийн төрлөөр каталог шүүх"""
        kind = (request.GET.get("kind") or "").strip().upper()
        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)
        if hasattr(InstrumentCatalog, "is_active"):
            qs = qs.filter(is_active=True)
        results = [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]
        return JsonResponse({"results": results})

    def sums_by_aimag_view(self, request: HttpRequest):
        """Аймаг сонгоход сумдыг ачаалах"""
        aimag_id = request.GET.get("aimag_id")
        qs = SumDuureg.objects.all().order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_id=aimag_id)
        results = [{"id": s.id, "text": s.name} for s in qs]
        return JsonResponse({"results": results})

    def location_options_view(self, request: HttpRequest):
        """Аймаг/Сум болон төрлөөр байршлыг шүүх"""
        kind = (request.GET.get("kind") or "").strip().upper()
        aimag_id = request.GET.get("aimag")
        sum_id = request.GET.get("sum")

        qs = _scope_location_qs(request) # Эрхийн хүрээгээр шүүх

        if kind:
            allowed = KIND_TO_LOCATION_TYPE.get(kind, [kind]) #
            qs = qs.filter(location_type__in=allowed)
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)

        results = [{"id": l.id, "text": l.name} for l in qs.order_by("name")]
        return JsonResponse({"results": results})

    def passport_view(self, request: HttpRequest, object_id: int):
        """Төхөөрөмжийн паспорт PDF үүсгэх"""
        device = get_object_or_404(Device, pk=object_id)
        pdf_bytes = generate_device_passport_pdf_bytes(device) #
        return HttpResponse(pdf_bytes, content_type="application/pdf")
           
    
        return custom + urls

    # --- AJAX View функцүүд (Бүрэн хувилбар) ---

    def catalog_by_kind_view(self, request):
        kind = request.GET.get("kind", "").upper()
        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)
        results = [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]
        return JsonResponse({"results": results})

    def sums_by_aimag_view(self, request):
        aimag_id = request.GET.get("aimag_id")
        qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name") if aimag_id else SumDuureg.objects.none()
        results = [{"id": s.id, "text": s.name} for s in qs]
        return JsonResponse({"results": results})

    def location_options_view(self, request):
        aimag_id = request.GET.get("aimag")
        sum_id = request.GET.get("sum")
        kind = request.GET.get("kind", "").upper()
        
        qs = _scope_location_qs(request)
        if kind:
            allowed = KIND_TO_LOCATION_TYPE.get(kind, [kind])
            qs = qs.filter(location_type__in=allowed)
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)
            
        results = [{"id": l.id, "text": l.name} for l in qs.order_by("name")]
        return JsonResponse({"results": results})

    def passport_view(self, request, object_id):
        device = get_object_or_404(Device, pk=object_id)
        pdf_bytes = generate_device_passport_pdf_bytes(device)
        return HttpResponse(pdf_bytes, content_type="application/pdf")

    def location_options_view(self, request: HttpRequest):
        """Байршлуудын жагсаалтыг JSON-оор буцаах (kind/aimag/sum filter)."""
        kind = (request.GET.get("kind") or "").strip().upper()
        aimag_id = self._safe_int(request.GET.get("aimag"))
        sum_id = self._safe_int(request.GET.get("sum"))

        # ✅ эхлээд scope (эрхийн шүүлт)
        qs = _scope_location_qs(request)

        # ✅ дараа нь kind -> location_type mapping
        if kind:
            allowed = KIND_TO_LOCATION_TYPE.get(kind, [kind])
            qs = qs.filter(location_type__in=allowed)

        # ✅ aimag/sum filter
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)

        qs = qs.order_by("name")[:2000]
        results = [{"id": l.id, "text": l.name} for l in qs]
        return JsonResponse({"results": results})
    
    def catalog_by_kind_view(self, request):
        kind = request.GET.get("kind", "").upper()
        qs = InstrumentCatalog.objects.all()
        if kind:
            qs = qs.filter(kind=kind)
        results = [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs.order_by("code")]
        return JsonResponse({"results": results})

    def passport_view(self, request: HttpRequest, object_id: int):
        device = get_object_or_404(Device, pk=object_id)
        pdf_bytes = generate_device_passport_pdf_bytes(device)
        return FileResponse(io.BytesIO(pdf_bytes), as_attachment=True, filename=f"passport_{device.pk}.pdf")

    @admin.display(description="QR")
    def qr_preview(self, obj):
        if obj.qr_image:
            return format_html(
                '<img src="{}" style="height:48px;border:1px solid #ccc;border-radius:4px" />',
                obj.qr_image.url,
            )
        return "-"

    @admin.display(description="Калибровка")
    def verification_badge(self, obj):
        d = getattr(obj, "next_verification_date", None)
        if not d:
            return "❓"
        today = timezone.localdate()
        if d < today:
            return format_html('<b style="color:red">⛔ Дууссан</b>')
        return format_html('<b style="color:green">✅ OK</b>')

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


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/passport/",
                self.admin_site.admin_view(self.passport_view),
                name="inventory_device_passport",
            ),
            path("catalog-by-kind/", self.admin_site.admin_view(self.catalog_by_kind_view), name="device_catalog_by_kind"),
            # Энэ мөр танд алдаа өгч байсан, одоо зөв болсон
            path("location-options/", self.admin_site.admin_view(self.location_options_view), name="device_location_options"),
        ]
        return custom + urls

    # --- Custom Views ---

    def catalog_by_kind_view(self, request: HttpRequest):
        """Device.kind-аар InstrumentCatalog жагсаалтыг JSON-оор буцаана."""
        kind = (request.GET.get("kind") or "").strip().upper()
        qs = InstrumentCatalog.objects.all()

        # kind зөв утга биш бол хоосон буцаая
        valid_kinds = {k for (k, _lbl) in getattr(InstrumentCatalog.Kind, "choices", [])} if hasattr(InstrumentCatalog, "Kind") else set()
        
        if kind and valid_kinds and kind not in valid_kinds:
            # Valid төрөл биш бол юу ч буцаахгүй
            pass
        elif kind:
            qs = qs.filter(kind=kind)

        if hasattr(InstrumentCatalog, "is_active"):
            qs = qs.filter(is_active=True)

        qs = qs.order_by("code")
        results = [{"id": x.id, "text": f"{x.code} - {x.name_mn}"} for x in qs]
        return JsonResponse({"results": results})

    def location_options_view(self, request: HttpRequest):
        """Байршлуудыг JSON-оор буцаах (AJAX)"""
        aimag_id = (request.GET.get("aimag") or "").strip() or None
        sum_id = (request.GET.get("sum") or "").strip() or None
        
        qs = _scope_location_qs(request).order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)
            
        # Select2-т тохирсон бүтэц: id, text (name биш)
        results = [{"id": l.id, "text": l.name} for l in qs]
        return JsonResponse({"results": results})

    def passport_view(self, request: HttpRequest, object_id: int):
        device = get_object_or_404(Device, pk=object_id)
        # generate_device_passport_pdf функцээ зөв import хийсэн эсэхээ шалгаарай
        pdf_obj = generate_device_passport_pdf(device, request=request)

        if hasattr(pdf_obj, "read"):
            fp = pdf_obj
            try: fp.seek(0)
            except Exception: pass
        else:
            fp = io.BytesIO(pdf_obj)
            fp.seek(0)

        filename = f"device_passport_{(device.serial_number or device.pk)}.pdf"
        return FileResponse(fp, as_attachment=True, filename=filename, content_type="application/pdf")

    # --- Display Methods ---

    @admin.display(description="QR")
    def qr_preview(self, obj: Device):
        img = getattr(obj, "qr_image", None)
        if not img: return "-"
        try: url = img.url
        except Exception: return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" style="height:48px;border:1px solid #ccc;border-radius:4px" />'
            "</a>", url, url
        )

    @admin.display(description="Калибровка")
    def verification_badge(self, obj: Device):
        field = _device_next_verif_field()
        if not field: return format_html('<span style="color:#666">—</span>')
        d = getattr(obj, field, None)
        if not d: return format_html('<span style="color:#6c757d;font-weight:600">❓ Огноо байхгүй</span>')
        
        today = timezone.localdate()
        if d < today:
            return format_html('<span style="color:#dc3545;font-weight:700">⛔ Дууссан</span>')
            
        left = (d - today).days
        if left <= 30:
            return format_html('<span style="color:#fd7e14;font-weight:700">⚠️ ≤30 ({} өдөр)</span>', left)
        if left <= 90:
            return format_html('<span style="color:#0d6efd;font-weight:700">🔵 ≤90 ({} өдөр)</span>', left)
            
        return format_html('<span style="color:#198754;font-weight:700">✅ OK ({} өдөр)</span>', left)

    def save_model(self, request: HttpRequest, obj: Device, form, change: bool) -> None:
        old_loc_id = None
        if change and obj.pk:
            try:
                old_loc_id = Device.objects.filter(pk=obj.pk).values_list("location_id", flat=True).first()
            except Exception:
                old_loc_id = None

        super().save_model(request, obj, form, change)

        # Movement auto-log
        try:
            new_loc_id = obj.location_id
            if change and old_loc_id != new_loc_id:
                prof = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
                moved_by = getattr(prof, "pk", None)
                reason = ""
                try: reason = (form.cleaned_data.get("movement_reason") or "").strip()
                except Exception: reason = ""
                
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
    change_form_template = "admin/inventory/workflow_change_form.html"

@admin.action(description="Workflow → Submit (DRAFT → SUBMITTED)")
def submit_control_to_workflow(modeladmin, request, queryset):
    qs = queryset.filter(workflow_status=WorkflowStatus.DRAFT)
    n = qs.update(
        workflow_status=WorkflowStatus.SUBMITTED,
        submitted_at=timezone.now(),
    )
    messages.success(request, f"{n} control хүсэлт SUBMITTED боллоо.")


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

   
# ============================================================
# Custom AdminSite (/django-admin/) — ReportsHub + Workflow URLs
# ============================================================

class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ админ"

    def device_location_options_proxy(self, request: HttpRequest) -> JsonResponse:
        from .models import Device
        ma = self._registry.get(Device)
        if not ma or not hasattr(ma, "location_options_view"):
            return JsonResponse({"results": []})
        return ma.location_options_view(request)

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path("debug-hello/", self.admin_view(lambda r: HttpResponse("HELLO")), name="debug_hello"),
            path("reports/sums-by-aimag/", self.admin_view(views_admin.reports_sums_by_aimag),name="reports-sums-by-aimag"),
       

            # Dashboards
            path("dashboard/", self.admin_view(va.dashboard_home), name="dashboard_home"),
            path("dashboard/table/", self.admin_view(va.dashboard_table), name="dashboard_table"),
            path("dashboard/graph/", self.admin_view(admin_dashboard.dashboard_graph_view), name="dashboard_graph"),
            path("dashboard/general/", self.admin_view(va.dashboard_general), name="dashboard_general"),
            path("data-entry/", self.admin_view(va.admin_data_entry), name="admin_data_entry"),

            # Workflow
            path("inventory/workflow/pending/", self.admin_view(wf.workflow_pending_dashboard), name="workflow_pending_dashboard"),
            path("inventory/workflow/pending-counts/", self.admin_view(wf.workflow_pending_counts), name="workflow_pending_counts_live"),
            path("inventory/workflow/pending-counts-legacy/", self.admin_view(wf.workflow_pending_counts), name="workflow_pending_counts"),
            path("inventory/workflow/review/", self.admin_view(wf.workflow_review_action), name="workflow_review_action"),
            path("inventory/workflow/audit/", self.admin_view(wf.workflow_audit_log), name="workflow_audit_log"),

            # Location options (Device form ajax)
            path("inventory/device/location-options/", self.admin_view(self.device_location_options_proxy), name="inventory_device_device_location_options"),

            # Reports (single)
            path("reports/", self.admin_view(reports_hub_view), name="reports_hub"),
            path("api/reports/charts/", self.admin_view(reports_chart_json), name="reports_chart_json"),
            path("api/reports/sums/", self.admin_view(reports_sums_by_aimag), name="reports_sums_by_aimag"),
            path("api/reports/table/", self.admin_view(reports_table_json), name="reports_table_json"),
        ]

        return my_urls + urls

# 2. Одоо классыг ашиглан объект (instance) үүсгэхэд алдаа гарахгүй
inventory_admin_site = InventoryAdminSite(name="admin")

# 3. Моделиудыг бүртгэх
inventory_admin_site.register(Aimag)
inventory_admin_site.register(SumDuureg)
inventory_admin_site.register(Location, LocationAdmin)
inventory_admin_site.register(InstrumentCatalog)
inventory_admin_site.register(Device, DeviceAdmin)
inventory_admin_site.register(MaintenanceService)
inventory_admin_site.register(ControlAdjustment)
inventory_admin_site.register(UserProfile)

# Optional: AuditEvent (if exists)
if AuditEvent is not None:

    class AuditEventAdmin(admin.ModelAdmin):
        # minimal safe defaults (won't crash even if fields differ)
        ordering = ("-id",)
        list_display = ("id",)
        search_fields = ("id",)

    inventory_admin_site.register(AuditEvent, AuditEventAdmin)


