# -*- coding: utf-8 -*-
# inventory/admin.py  (ENTERPRISE FINAL CLEAN)

from __future__ import annotations

from datetime import date
from io import BytesIO
import csv

from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from openpyxl import Workbook

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import (
    # core refs
    Aimag, SumDuureg, Organization, Location, InstrumentCatalog,
    # devices + workflow
    Device, MaintenanceService, ControlAdjustment,
    MaintenanceEvidence, ControlEvidence,
    # auth/audit
    UserProfile,
)

# ============================================================
# Scope helpers (Аймгийн инженер зөвхөн өөрийн аймгийн data)
# ============================================================

UB_AIMAG_ID = 1  # танайд УБ=1 гэж тохирсон гэж үзэв


def _get_scope(request: HttpRequest) -> dict:
    """
    Enterprise scope:
      - superuser => all
      - other => UserProfile.aimag дээр тулгуурлана
      - УБ дээр (aimag_id==UB_AIMAG_ID) profile дээр district/sum байвал түүгээр нарийсгана
    """
    u = getattr(request, "user", None)
    if not u or u.is_superuser:
        return {"all": True, "aimag_id": None, "sum_id": None}

    prof = getattr(u, "profile", None) or getattr(u, "userprofile", None)
    aimag_id = getattr(prof, "aimag_id", None)

    # UB district/sum (байвал)
    sum_id = (
        getattr(prof, "sumduureg_id", None)
        or getattr(prof, "sum_ref_id", None)
        or getattr(prof, "district_id", None)
    )

    return {"all": False, "aimag_id": aimag_id, "sum_id": sum_id}


def _scope_location_qs(request: HttpRequest):
    scope = _get_scope(request)
    qs = Location.objects.all()

    if scope["all"]:
        return qs

    if not scope["aimag_id"]:
        return qs.none()

    qs = qs.filter(aimag_ref_id=scope["aimag_id"])

    if scope["aimag_id"] == UB_AIMAG_ID and scope["sum_id"]:
        qs = qs.filter(sum_ref_id=scope["sum_id"])

    return qs


def _scope_device_qs(request: HttpRequest):
    scope = _get_scope(request)
    qs = Device.objects.select_related("location", "location__aimag_ref", "location__owner_org")

    if scope["all"]:
        return qs

    if not scope["aimag_id"]:
        return qs.none()

    qs = qs.filter(location__aimag_ref_id=scope["aimag_id"])

    if scope["aimag_id"] == UB_AIMAG_ID and scope["sum_id"]:
        qs = qs.filter(location__sum_ref_id=scope["sum_id"])

    return qs


def _deny_delete_for_scoped_users(request: HttpRequest) -> bool:
    """superuser биш бол delete хориглоно (таны шаардлагын дагуу)."""
    u = getattr(request, "user", None)
    return bool(u and not u.is_superuser)


# ============================================================
# Mixins (FK scope хамгаалалт)
# ============================================================

class ScopedDeviceFKMixin:
    """
    MaintenanceService / ControlAdjustment дээр Device FK сонголтыг scope-оор хязгаарлана.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device":
            kwargs["queryset"] = _scope_device_qs(request).order_by("-id")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


# ============================================================
# Inlines (Evidence + History)
# ============================================================

class MaintenanceEvidenceInline(admin.TabularInline):
    model = MaintenanceEvidence
    extra = 1
    fields = ("file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class ControlEvidenceInline(admin.TabularInline):
    model = ControlEvidence
    extra = 1
    fields = ("file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class MaintenanceHistoryInline(admin.TabularInline):
    model = MaintenanceService
    fk_name = "device"
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "date",
        "reason",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",)
    readonly_fields = fields
    ordering = ("-date", "-id")


class ControlHistoryInline(admin.TabularInline):
    model = ControlAdjustment
    fk_name = "device"
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "date",
        "result",
        "performer_type",
        "performer_engineer_name",
        "performer_org_name",
    )
    readonly_fields = fields
    ordering = ("-date", "-id")


# ============================================================
# Reference admins (basic, safe)
# ============================================================

@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "aimag")
    list_filter = ("aimag",)
    search_fields = ("name",)
    ordering = ("aimag__name", "name")

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "aimag", "org_type", "is_ub")
    list_filter = ("aimag", "org_type", "is_ub")
    search_fields = ("name",)
    ordering = ("aimag__name", "name")

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location_type", "aimag_ref", "sum_ref", "owner_org")
    list_filter = ("location_type", "aimag_ref")
    search_fields = ("name",)
    ordering = ("aimag_ref__name", "name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        scope = _get_scope(request)
        if scope["all"]:
            return qs
        if not scope["aimag_id"]:
            return qs.none()
        qs = qs.filter(aimag_ref_id=scope["aimag_id"])
        if scope["aimag_id"] == UB_AIMAG_ID and scope["sum_id"]:
            qs = qs.filter(sum_ref_id=scope["sum_id"])
        return qs

    def save_model(self, request, obj, form, change):
        # owner_org хоосон үед л автоматаар бөглөнө (танай өмнөх шаардлага)
        if not getattr(obj, "owner_org_id", None) and getattr(obj, "aimag_ref_id", None):
            org = Organization.objects.filter(
                aimag_id=obj.aimag_ref_id,
                org_type="OBS_CENTER",
                is_ub=False
            ).order_by("id").first()

            if not org:
                org = Organization.objects.filter(
                    aimag_id=obj.aimag_ref_id,
                    name__icontains="УЦУОШТ"
                ).order_by("id").first()

            if org:
                obj.owner_org = org

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(InstrumentCatalog)
class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_mn", "kind", "unit", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name_mn")
    ordering = ("kind", "code")

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)


# ============================================================
# Workflow admins (Maintenance/Control)
# ============================================================

@admin.register(MaintenanceService)
class MaintenanceServiceAdmin(ScopedDeviceFKMixin, admin.ModelAdmin):
    list_display = ("id", "device", "date", "reason", "performer_type")
    list_filter = ("date", "performer_type")
    search_fields = ("device__serial_number", "device__inventory_code", "reason")
    ordering = ("-date", "-id")
    inlines = [MaintenanceEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)


@admin.register(ControlAdjustment)
class ControlAdjustmentAdmin(ScopedDeviceFKMixin, admin.ModelAdmin):
    list_display = ("id", "device", "date", "result", "performer_type")
    list_filter = ("date", "performer_type", "result")
    search_fields = ("device__serial_number", "device__inventory_code")
    ordering = ("-date", "-id")
    inlines = [ControlEvidenceInline]

    class Media:
        js = ("inventory/js/admin/performer_toggle.js",)


# ============================================================
# Device admin (Enterprise)
# - Scope enforced (queryset + FK)
# - Kind -> InstrumentCatalog filter endpoint
# - Aimag/Sum -> Location filter endpoint (enterprise; edit хадгална)
# - Report dashboard + CSV/XLSX/PDF export
# - Inline history (Maintenance + Control)
# ============================================================

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "kind", "catalog_item", "location", "status")
    list_filter = ("kind", "status")
    search_fields = ("serial_number", "inventory_code", "location__name", "catalog_item__code", "catalog_item__name_mn")
    ordering = ("-id",)
    inlines = [MaintenanceHistoryInline, ControlHistoryInline]

    class Media:
        js = (
            "inventory/js/admin/device_kind_filter.js",
            "inventory/js/admin/device_location_filter_enterprise.js",
        )

    # ---------- Scope ----------
    def get_queryset(self, request):
        return _scope_device_qs(request)

    def has_delete_permission(self, request, obj=None):
        if _deny_delete_for_scoped_users(request):
            return False
        return super().has_delete_permission(request, obj=obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Location FK dropdown дээр scope-оор хязгаарлах (JS-гүй үед ч хамгаална)
        if db_field.name == "location":
            kwargs["queryset"] = _scope_location_qs(request).order_by("name")

        # Catalog FK dropdown дээр kind-ээр шүүхийг JS хийнэ,
        # гэхдээ base байдлаар active-ыг л үлдээнэ (байвал).
        if db_field.name in ("catalog_item", "instrument_catalog", "catalog"):
            qs = InstrumentCatalog.objects.all()
            if hasattr(InstrumentCatalog, "is_active"):
                qs = qs.filter(is_active=True)
            kwargs["queryset"] = qs.order_by("kind", "code")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ---------- Custom URLs ----------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("catalog-by-kind/", self.catalog_by_kind_view, name="device_catalog_by_kind"),
            path("location-options/", self.location_options_view, name="device_location_options"),
            path("reports/", self.device_reports_view, name="device_reports"),
        ]
        return custom + urls

    def catalog_by_kind_view(self, request: HttpRequest):
        """
        Return InstrumentCatalog options filtered by Device.kind
        GET: ?kind=WEATHER|HYDRO|AWS|ETALON|RADAR|AEROLOGY|AGRO|OTHER
        Response: [{"id":..,"name":..}, ...]
        """
        kind = (request.GET.get("kind") or "").strip().upper()

        qs = InstrumentCatalog.objects.all()
        if hasattr(InstrumentCatalog, "is_active"):
            qs = qs.filter(is_active=True)
        if kind:
            qs = qs.filter(kind=kind)

        data = [{"id": o.id, "name": str(o)} for o in qs.order_by("code")]
        return JsonResponse(data, safe=False)

    def location_options_view(self, request: HttpRequest):
        """
        Return Location options filtered by aimag/sum + user scope
        GET: ?aimag=<id>&sum=<id>&selected=<location_id>
        Response: [{"id":..,"name":..}, ...]
        """
        aimag_id = request.GET.get("aimag") or None
        sum_id = request.GET.get("sum") or None
        selected_id = request.GET.get("selected") or None

        qs = _scope_location_qs(request)

        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)

        extra = []
        if selected_id:
            selected_obj = Location.objects.filter(id=selected_id).first()
            if selected_obj and not qs.filter(id=selected_obj.id).exists():
                extra.append({"id": selected_obj.id, "name": f"{selected_obj.name} (одоогийн)"})

        data = extra + [{"id": l.id, "name": l.name} for l in qs.order_by("name")]
        return JsonResponse(data, safe=False)

    # ---------- Reports ----------
    def device_reports_view(self, request: HttpRequest):
        """
        Admin dashboard: Device counts with filters + export CSV/XLSX/PDF
        Filters (GET):
          - aimag: Aimag.id
          - org: Organization.id (Location.owner_org)
          - kind: Device.kind
          - status: Device.status
          - format: csv|xlsx|pdf
        """
        qs = _scope_device_qs(request).select_related("location", "location__aimag_ref", "location__owner_org")

        aimag_id = (request.GET.get("aimag") or "").strip()
        org_id = (request.GET.get("org") or "").strip()
        kind = (request.GET.get("kind") or "").strip()
        status = (request.GET.get("status") or "").strip()
        out_fmt = (request.GET.get("format") or "").strip().lower()

        if aimag_id:
            qs = qs.filter(location__aimag_ref_id=aimag_id)
        if org_id:
            qs = qs.filter(location__owner_org_id=org_id)
        if kind:
            qs = qs.filter(kind=kind)
        if status:
            qs = qs.filter(status=status)

        # агрегат хүснэгт
        rows = (
            qs.values(
                "location__aimag_ref__name",
                "location__owner_org__name",
                "kind",
                "status",
            )
            .annotate(cnt=Count("id"))
            .order_by("location__aimag_ref__name", "location__owner_org__name", "kind", "status")
        )

        # totals
        total_devices = qs.count()

        # export helpers
        def _as_table_data():
            header = ["Аймаг", "Байгууллага", "Төрөл", "Төлөв", "Тоо"]
            body = [
                [
                    r["location__aimag_ref__name"] or "",
                    r["location__owner_org__name"] or "",
                    r["kind"] or "",
                    r["status"] or "",
                    r["cnt"],
                ]
                for r in rows
            ]
            return header, body

        if out_fmt == "csv":
            resp = HttpResponse(content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = 'attachment; filename="device_report.csv"'
            w = csv.writer(resp)
            header, body = _as_table_data()
            w.writerow(header)
            for b in body:
                w.writerow(b)
            return resp

        if out_fmt == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = "Device Report"
            header, body = _as_table_data()
            ws.append(header)
            for b in body:
                ws.append(b)
            ws.append([])
            ws.append(["НИЙТ", "", "", "", total_devices])

            bio = BytesIO()
            wb.save(bio)
            bio.seek(0)

            resp = HttpResponse(
                bio.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = 'attachment; filename="device_report.xlsx"'
            return resp

        if out_fmt == "pdf":
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elems = []

            elems.append(Paragraph("Device Report", styles["Title"]))
            elems.append(Paragraph(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
            elems.append(Spacer(1, 12))

            header, body = _as_table_data()
            table_data = [header] + body + [["НИЙТ", "", "", "", total_devices]]

            t = Table(table_data, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                    ]
                )
            )
            elems.append(t)

            doc.build(elems)
            pdf = buffer.getvalue()
            buffer.close()

            resp = HttpResponse(pdf, content_type="application/pdf")
            resp["Content-Disposition"] = 'attachment; filename="device_report.pdf"'
            return resp

        # HTML view (no custom template required; use minimal render)
        aimags = Aimag.objects.order_by("name")
        orgs = Organization.objects.order_by("name")

        context = {
            **admin.site.each_context(request),
            "title": "Device Reports",
            "aimags": aimags,
            "orgs": orgs,
            "filters": {
                "aimag": aimag_id,
                "org": org_id,
                "kind": kind,
                "status": status,
            },
            "rows": list(rows),
            "total_devices": total_devices,
        }
        # NOTE: Танайд template байхгүй бол асуудал гаргахгүй гэж "admin/base_site.html" дээр шууд minimal html хийхгүй.
        # Энэ view-д зориулж доорх template-ийг 1 удаа нэмэхийг зөвлөе:
        # templates/admin/inventory/device/reports.html
        return render(request, "admin/inventory/device/reports.html", context)


# ============================================================
# Minimal report template fallback note:
# - Дээрх reports view ажиллахын тулд template хэрэгтэй.
# - Хэрэв одоохондоо template нэмэхгүйгээр ажиллуулах бол
#   device_reports_view дотор render-ийн оронд HttpResponse(html) хийж болно.
# ============================================================
