from __future__ import annotations

import io
import uuid
import zipfile
from datetime import timedelta
from typing import Any, Dict, Optional

from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.admin.utils import unquote
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import DeviceAdminForm
from .models import (
    Aimag,
    ControlAdjustment,
    ControlEvidence,
    Device,
    DeviceMovement,
    InstrumentCatalog,
    Location,
    MaintenanceEvidence,
    MaintenanceService,
    Organization,
    SparePartItem,
    SparePartOrder,
    SumDuureg,
    UserProfile,
)
from .views_dashboard_general import general_dashboard_view
from . import reports_hub_compat as rhc
from . import views_admin_workflow as wf


AIMAG_ENGINEER_GROUP = "AimagEngineer"
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

try:
    pdfmetrics.registerFont(TTFont("Arial", "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", "Arial-Bold.ttf"))
    FONT_REG = "Arial"
    FONT_BOLD = "Arial-Bold"
except Exception:
    pass


def _safe_profile(user):
    return getattr(user, "userprofile", None) or getattr(user, "profile", None)


def _get_scope(request: HttpRequest) -> Dict[str, Any]:
    u = getattr(request, "user", None)
    if not u or getattr(u, "is_superuser", False):
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = _safe_profile(u)
    if not prof:
        return {"all": False, "aimag_id": None, "sum_id": None}

    return {
        "all": False,
        "aimag_id": getattr(prof, "aimag_id", None),
        "sum_id": getattr(prof, "sumduureg_id", None) or getattr(prof, "sum_ref_id", None),
    }


def get_ub_aimag_id() -> Optional[int]:
    key = "inventory:ub_aimag_id:v1"
    v = cache.get(key)
    if v is not None:
        return int(v) if v else None
    try:
        ub = Aimag.objects.get(name__icontains="улаанбаатар")
        cache.set(key, int(ub.id), 86400)
        return int(ub.id)
    except Exception:
        cache.set(key, 0, 3600)
        return None


def _scope_qs(request: HttpRequest, qs: QuerySet, *, aimag_field: str) -> QuerySet:
    scope = _get_scope(request)
    if scope.get("all"):
        return qs

    aimag_id = scope.get("aimag_id")
    if not aimag_id:
        return qs.none()

    qs = qs.filter(**{f"{aimag_field}_id": aimag_id})

    ub_id = get_ub_aimag_id()
    sum_id = scope.get("sum_id")
    if ub_id is not None and aimag_id == ub_id and sum_id:
        model = qs.model
        names = {f.name for f in model._meta.get_fields() if hasattr(f, "name")}
        if "sum_ref" in names:
            qs = qs.filter(sum_ref_id=sum_id)
        elif "location" in names:
            qs = qs.filter(location__sum_ref_id=sum_id)
        elif "device" in names:
            qs = qs.filter(device__location__sum_ref_id=sum_id)
    return qs


def _device_next_verif_field() -> Optional[str]:
    candidates = ("next_verification_date", "next_calibration_date", "next_due_date", "next_verif_date")
    names = {f.name for f in Device._meta.get_fields() if hasattr(f, "name")}
    for c in candidates:
        if c in names:
            return c
    return None


def _verification_state(obj: Device) -> tuple[str, str]:
    field = _device_next_verif_field()
    if not field:
        return ("secondary", "N/A")

    value = getattr(obj, field, None)
    if not value:
        return ("secondary", "Unknown")

    today = timezone.localdate()
    if value < today:
        return ("danger", "Expired")
    if value <= today + timedelta(days=30):
        return ("warning", "Due 30")
    if value <= today + timedelta(days=90):
        return ("info", "Due 90")
    return ("success", "OK")


def _pdf_table(data):
    table = Table(data, colWidths=[5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT_REG),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def generate_device_passport_pdf_bytes(device: Device) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="MnTitle", parent=styles["Heading1"], fontName=FONT_BOLD, alignment=1)
    elements = [
        Paragraph("ТЕХНИКИЙН ПАСПОРТ", title_style),
        Spacer(1, 0.5 * cm),
    ]

    rows = [
        ["Үзүүлэлт", "Мэдээлэл"],
        ["Серийн дугаар", getattr(device, "serial_number", "") or "---"],
        ["Төхөөрөмжийн нэр", getattr(device, "other_name", "") or "---"],
        ["Төрөл", getattr(device, "kind", "") or "---"],
        ["Инвентар код", getattr(device, "inventory_code", "") or "---"],
        ["Байршил", getattr(getattr(device, "location", None), "name", "Тодорхойгүй")],
        ["Статус", getattr(device, "status", "") or "---"],
        ["Ашиглалтад орсон", str(getattr(device, "commissioned_date", None) or getattr(device, "installation_date", None) or "---")],
    ]
    elements.append(_pdf_table(rows))
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


class SumDuuregByAimagFilter(admin.SimpleListFilter):
    title = "Сум/Дүүрэг"
    parameter_name = "sum_ref__id__exact"

    def lookups(self, request, model_admin):
        aimag_id = (request.GET.get("aimag_ref__id__exact") or request.GET.get("aimag") or "").strip()
        if not aimag_id:
            return []
        qs = SumDuureg.objects.filter(aimag_id=aimag_id).order_by("name")
        return [(str(o.id), str(o)) for o in qs[:500]]

    def queryset(self, request, queryset):
        val = self.value()
        return queryset.filter(sum_ref_id=val) if val else queryset


class LocationTypeFilter(admin.SimpleListFilter):
    title = "Байршлын төрөл"
    parameter_name = "location_type"

    def lookups(self, request, model_admin):
        return [
            ("WEATHER", "Цаг уур"),
            ("AWS", "AWS"),
            ("RADAR", "Радар"),
            ("HYDRO", "Ус судлал"),
            ("AEROLOGY", "Аэрологи"),
            ("AGRO", "ХАА"),
            ("ETALON", "Эталон"),
            ("OTHER", "Бусад"),
        ]

    def queryset(self, request, queryset):
        v = self.value()
        return queryset.filter(location_type=v) if v else queryset


class VerificationBucketFilter(admin.SimpleListFilter):
    title = "Калибровка"
    parameter_name = "verification"

    def lookups(self, request, model_admin):
        return (
            ("expired", "⛔ Дууссан"),
            ("due_30", "⚠️ 30 хоног"),
            ("due_90", "🔵 90 хоног"),
            ("ok", "✅ Хэвийн"),
        )

    def queryset(self, request, queryset):
        field = _device_next_verif_field()
        if not field or not self.value():
            return queryset

        today = timezone.localdate()
        if self.value() == "expired":
            return queryset.filter(**{f"{field}__lt": today})
        if self.value() == "due_30":
            return queryset.filter(**{f"{field}__range": [today, today + timedelta(days=30)]})
        if self.value() == "due_90":
            return queryset.filter(**{f"{field}__range": [today + timedelta(days=31), today + timedelta(days=90)]})
        if self.value() == "ok":
            return queryset.filter(**{f"{field}__gt": today + timedelta(days=90)})
        return queryset


@admin.action(description="🔳 QR үүсгэх / шинэчлэх")
def generate_qr(modeladmin, request: HttpRequest, queryset: QuerySet):
    try:
        import qrcode
    except ImportError:
        modeladmin.message_user(request, "pip install qrcode[pil] шаардлагатай.", level=messages.ERROR)
        return

    public = request.GET.get("public") == "1"
    for d in queryset:
        if not getattr(d, "qr_token", None):
            d.qr_token = uuid.uuid4()

        route_name = "qr_device_public" if public else "qr_device_lookup"
        url = request.build_absolute_uri(reverse(route_name, args=[d.qr_token]))
        qr = qrcode.make(url)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        if hasattr(d, "qr_image"):
            d.qr_image.save(f"qr_{d.pk}.png", ContentFile(buf.getvalue()), save=False)
        d.save()

    modeladmin.message_user(request, "QR амжилттай үүсгэлээ.")


@admin.action(description="⛔ QR хүчингүй болгох")
def revoke_qr(modeladmin, request: HttpRequest, queryset: QuerySet):
    if hasattr(Device, "qr_revoked_at"):
        queryset.update(qr_revoked_at=timezone.now())
        modeladmin.message_user(request, "QR хүчингүй болголоо.")
    else:
        modeladmin.message_user(request, "qr_revoked_at field алга.", level=messages.WARNING)


@admin.action(description="📄 Техник паспорт (PDF/ZIP)")
def download_device_passport(modeladmin, request: HttpRequest, queryset: QuerySet):
    devices = list(queryset)
    if len(devices) == 1:
        pdf_bytes = generate_device_passport_pdf_bytes(devices[0])
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="passport_{devices[0].pk}.pdf"'
        return resp

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for d in devices:
            zf.writestr(f"passport_{d.pk}.pdf", generate_device_passport_pdf_bytes(d))

    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = 'attachment; filename="passports.zip"'
    return resp


class MaintenanceEvidenceInline(admin.TabularInline):
    model = MaintenanceEvidence
    extra = 1


class ControlEvidenceInline(admin.TabularInline):
    model = ControlEvidence
    extra = 1


class MaintenanceHistoryInline(admin.TabularInline):
    model = MaintenanceService
    extra = 0
    readonly_fields = ("date", "reason", "workflow_status")
    show_change_link = True


class ControlHistoryInline(admin.TabularInline):
    model = ControlAdjustment
    extra = 0
    readonly_fields = ("date", "result", "workflow_status")
    show_change_link = True


class DeviceMovementInline(admin.TabularInline):
    model = DeviceMovement
    extra = 0
    readonly_fields = ("moved_at", "from_location", "to_location", "reason")
    show_change_link = True


class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1


class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")


class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("aimag", "name")
    list_filter = ("aimag",)
    search_fields = ("name",)


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "aimag")
    search_fields = ("name",)
    list_filter = ("org_type", "aimag")


class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")


class LocationAdmin(admin.ModelAdmin):
    change_list_template = "inventory/admin/location_changelist_with_map.html"
    list_display = ("name", "location_type", "aimag_ref", "device_count_col", "view_on_map")
    list_filter = ("aimag_ref", SumDuuregByAimagFilter, LocationTypeFilter)
    search_fields = ("name", "wmo_index", "district_name")

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(device_count=Count("devices", distinct=True))
        return _scope_qs(request, qs, aimag_field="aimag_ref")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("map/", self.admin_site.admin_view(self.map_view), name="inventory_location_map"),
            path("<path:object_id>/map-one/", self.admin_site.admin_view(self.map_one_view), name="inventory_location_map_one"),
        ]
        return custom + urls

    def map_view(self, request):
        return render(request, "inventory/location_map.html", {"locations_json": "[]"})

    def map_one_view(self, request, object_id):
        try:
            location_id = int(unquote(object_id))
        except Exception:
            location_id = object_id
        return render(request, "inventory/location_map.html", {"focus_id": location_id})

    @admin.display(description="Багаж")
    def device_count_col(self, obj):
        return getattr(obj, "device_count", 0)

    @admin.display(description="Байршил")
    def view_on_map(self, obj):
        if not getattr(obj, "latitude", None):
            return "—"
        url = reverse(f"{self.admin_site.name}:inventory_location_map_one", args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">📍 Харах</a>', url)


class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    actions = [generate_qr, revoke_qr, download_device_passport]
    inlines = [MaintenanceHistoryInline, ControlHistoryInline, DeviceMovementInline]

    list_display = (
        "serial_number",
        "kind",
        "status",
        "location",
        "location_map",
        "verification_badge",
        "qr_preview",
    )
    list_filter = ("kind", "status", VerificationBucketFilter)
    search_fields = ("serial_number", "inventory_code", "other_name", "location__name")
    readonly_fields = ("qr_preview",)
    ordering = ("-id",)

    fieldsets = (
        ("Ерөнхий", {
            "fields": (
                "catalog_item",
                "other_name",
                "serial_number",
                "inventory_code",
                "kind",
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
            )
        }),
        ("QR", {
            "fields": ("qr_preview",)
        }),
    )

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_cascade.js",
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related(
            "location",
            "location__aimag_ref",
            "location__sum_ref",
        )
        return _scope_qs(request, qs, aimag_field="location__aimag_ref")

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class RequestForm(Form):
            def __init__(self2, *args, **kw):
                kw["request"] = request
                super().__init__(*args, **kw)

        return RequestForm

    def location_options_view(self, request):
        from .views import location_options
        return location_options(request)

    def catalog_by_kind_view(self, request):
        from .views import catalog_by_kind
        return catalog_by_kind(request)

    def passport_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not obj:
            return HttpResponse("Not found", status=404)

        pdf_bytes = generate_device_passport_pdf_bytes(obj)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="passport_{obj.pk}.pdf"'
        return response

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "location-options/",
                self.admin_site.admin_view(self.location_options_view),
                name="inventory_device_device_location_options",
            ),
            path(
                "catalog-by-kind/",
                self.admin_site.admin_view(self.catalog_by_kind_view),
                name="inventory_device_device_catalog_by_kind",
            ),
            path(
                "<int:object_id>/passport/",
                self.admin_site.admin_view(self.passport_view),
                name="inventory_device_passport",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Газрын зураг")
    def location_map(self, obj):
        loc = getattr(obj, "location", None)
        if not loc or not getattr(loc, "latitude", None):
            return "—"
        url = reverse(f"{self.admin_site.name}:inventory_location_map_one", args=[loc.id])
        return format_html('<a class="button" href="{}" target="_blank">📍</a>', url)

    @admin.display(description="Калибровка")
    def verification_badge(self, obj):
        color, label = _verification_state(obj)
        return format_html('<span class="badge badge-{}">{}</span>', color, label)

    @admin.display(description="QR")
    def qr_preview(self, obj):
        img = getattr(obj, "qr_image", None)
        if img and getattr(img, "url", None):
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:contain;border:1px solid #ddd;padding:2px;border-radius:4px;"/>',
                img.url,
            )
        tok = getattr(obj, "qr_token", None)
        if tok:
            return format_html("<code>{}</code>", tok)
        return "—"

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class MaintenanceServiceAdmin(admin.ModelAdmin):
    list_display = ("device", "date", "workflow_status")
    list_filter = ("workflow_status",)
    search_fields = ("device__serial_number", "reason")
    inlines = [MaintenanceEvidenceInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")


class ControlAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("device", "date", "workflow_status")
    list_filter = ("workflow_status",)
    search_fields = ("device__serial_number", "result")
    inlines = [ControlEvidenceInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("device", "device__location")
        return _scope_qs(request, qs, aimag_field="device__location__aimag_ref")


class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "aimag", "created_at", "status")
    list_filter = ("status", "aimag")
    inlines = [SparePartItemInline]

    def get_queryset(self, request):
        return _scope_qs(request, super().get_queryset(request), aimag_field="aimag")


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "org", "must_change_password")
    list_filter = ("aimag", "org", "must_change_password")
    search_fields = ("user__username", "user__first_name", "user__last_name")


class DeviceMovementAdmin(admin.ModelAdmin):
    list_display = ("device", "from_location", "to_location", "moved_at")
    search_fields = ("device__serial_number",)


class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ систем"
    site_title = "БҮРТГЭЛ"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        return redirect(reverse(f"{self.name}:dashboard_general"))

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        preferred = [
            "inventory.location",
            "inventory.device",
            "inventory.instrumentcatalog",
            "inventory.maintenanceservice",
            "inventory.controladjustment",
            "inventory.sparepartorder",
            "inventory.userprofile",
            "inventory.aimag",
            "inventory.sumduureg",
            "inventory.organization",
        ]

        def model_rank(m):
            obj = (m.get("object_name") or m.get("name") or "").lower()
            key = f"{m.get('app_label')}.{obj}"
            for i, p in enumerate(preferred):
                if key == p:
                    return i
            return 999

        for app in app_list:
            app["models"].sort(key=model_rank)
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/general/", self.admin_view(general_dashboard_view), name="dashboard_general"),

            path(
                "reports/",
                self.admin_view(lambda request: rhc.reports_hub_view(request, admin_site=self)),
                name="reports-hub",
            ),
            path("api/reports/charts/", self.admin_view(rhc.reports_chart_json), name="reports-chart-json"),
            path("api/reports/sums/", self.admin_view(rhc.reports_sums_by_aimag), name="reports-sums-by-aimag"),
            path("reports/export/devices.csv", self.admin_view(rhc.reports_export_devices_csv), name="reports-export-devices-csv"),
            path("reports/export/locations.csv", self.admin_view(rhc.reports_export_locations_csv), name="reports-export-locations-csv"),
            path("reports/export/maintenance.csv", self.admin_view(rhc.reports_export_maintenance_csv), name="reports-export-maintenance-csv"),
            path("reports/export/movements.csv", self.admin_view(rhc.reports_export_movements_csv), name="reports-export-movements-csv"),

            path("workflow/", self.admin_view(wf.workflow_pending_dashboard), name="workflow-pending-dashboard"),
            path("workflow/pending/", self.admin_view(wf.workflow_pending_dashboard), name="workflow-pending"),
            path("workflow/pending-counts/", self.admin_view(wf.workflow_pending_counts), name="workflow-pending-counts"),
            path("workflow/review/", self.admin_view(wf.workflow_review_action), name="workflow-review-queue"),
            path("workflow/audit/", self.admin_view(wf.workflow_audit_log), name="workflow-audit-history"),

            # Legacy compatibility routes
            path(
                "data-entry/",
                self.admin_view(lambda request: redirect(reverse(f"{self.name}:inventory_device_changelist"))),
                name="admin-data-entry",
            ),
            path(
                "dashboard/table/",
                self.admin_view(lambda request: redirect(reverse(f"{self.name}:reports-hub"))),
                name="dashboard-table",
            ),
            path(
                "dashboard/graph/",
                self.admin_view(lambda request: redirect(reverse(f"{self.name}:dashboard_general"))),
                name="dashboard-graph",
            ),
            path(
                "map/",
                self.admin_view(lambda request: redirect(reverse(f"{self.name}:inventory_location_map"))),
                name="dashboard-map",
            ),
        ]
        return custom_urls + urls


inventory_admin_site = InventoryAdminSite(name="inventory_admin")

inventory_admin_site.register(Aimag, AimagAdmin)
inventory_admin_site.register(SumDuureg, SumDuuregAdmin)
inventory_admin_site.register(Organization, OrganizationAdmin)
inventory_admin_site.register(InstrumentCatalog, InstrumentCatalogAdmin)
inventory_admin_site.register(Location, LocationAdmin)
inventory_admin_site.register(Device, DeviceAdmin)
inventory_admin_site.register(MaintenanceService, MaintenanceServiceAdmin)
inventory_admin_site.register(ControlAdjustment, ControlAdjustmentAdmin)
inventory_admin_site.register(SparePartOrder, SparePartOrderAdmin)
inventory_admin_site.register(DeviceMovement, DeviceMovementAdmin)
inventory_admin_site.register(UserProfile, UserProfileAdmin)