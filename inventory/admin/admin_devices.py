from django import forms
from django.contrib import admin
from django.utils.html import format_html

from inventory.models import Device, Location, InstrumentCatalog
from .admin_site import inventory_admin_site
from .admin_filters import AimagListFilter, SumListFilter, VerificationBucketFilter
from .admin_qr import generate_qr_token, revoke_qr_token, qr_preview
from .admin_passport import download_device_passport


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = getattr(self, "instance", None)

        if "sum" in self.fields and "aimag" in self.fields:
            aimag_id = None

            if self.data.get("aimag"):
                aimag_id = self.data.get("aimag")
            elif instance and getattr(instance, "aimag_id", None):
                aimag_id = instance.aimag_id
            elif instance and getattr(instance, "location_id", None) and getattr(instance.location, "aimag_id", None):
                aimag_id = instance.location.aimag_id

            if aimag_id and self.fields.get("sum"):
                self.fields["sum"].queryset = self.fields["sum"].queryset.filter(aimag_id=aimag_id)
            elif self.fields.get("sum"):
                self.fields["sum"].queryset = self.fields["sum"].queryset.none()

        if "location" in self.fields:
            qs = Location.objects.select_related("aimag", "sum").all()
            aimag_id = self.data.get("aimag") or getattr(instance, "aimag_id", None)
            sum_id = self.data.get("sum") or getattr(instance, "sum_id", None)

            if aimag_id:
                qs = qs.filter(aimag_id=aimag_id)
            if sum_id:
                qs = qs.filter(sum_id=sum_id)

            self.fields["location"].queryset = qs.order_by("name")

    class Media:
        js = (
            "admin/js/device_location_cascade.js",
        )


@admin.register(Device, site=inventory_admin_site)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm

    list_display = (
        "name",
        "serial_number",
        "kind",
        "location",
        "status",
        "next_verification_date",
        "verification_badge",
        "qr_short",
    )
    list_filter = (
        "kind",
        "status",
        AimagListFilter,
        SumListFilter,
        VerificationBucketFilter,
    )
    search_fields = (
        "name",
        "serial_number",
        "inventory_code",
    )
    autocomplete_fields = ("catalog", "location")
    actions = (
        generate_qr_token,
        revoke_qr_token,
        download_device_passport,
    )
    list_per_page = 50

    fieldsets = (
        ("Үндсэн мэдээлэл", {
            "fields": (
                "name",
                "catalog",
                "kind",
                "serial_number",
                "inventory_code",
                "status",
            )
        }),
        ("Байршил", {
            "fields": (
                "aimag",
                "sum",
                "location",
            )
        }),
        ("Калибровка", {
            "fields": (
                "last_verification_date",
                "next_verification_date",
            )
        }),
        ("QR", {
            "fields": ("qr_token",),
            "classes": ("collapse",),
        }),
    )
@admin.register(Device, site=inventory_admin_site)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm

    list_display = (
        "name",
        "serial_number",
        "kind",
        "location",
        "status",
        "next_verification_date",
        "verification_badge",
        "qr_short",
    )

    list_filter = (
        "kind",
        "status",
        AimagListFilter,
        SumListFilter,
        VerificationBucketFilter,
    )

    search_fields = (
        "name",
        "serial_number",
        "inventory_code",
    )

    autocomplete_fields = ("catalog", "location")

    actions = (
        generate_qr_token,
        revoke_qr_token,
        download_device_passport,
    )

    def render_change_form(self, request, context, *args, **kwargs):
        context["device_sums_url"] = "/ajax/load-sums/"
        context["device_locations_url"] = "/ajax/location-options/"
        return super().render_change_form(request, context, *args, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("location", "catalog")

    def qr_short(self, obj):
        return qr_preview(obj)

    qr_short.short_description = "QR"
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("location", "catalog")

    def qr_short(self, obj):
        return qr_preview(obj)

    qr_short.short_description = "QR"

    def verification_badge(self, obj):
        date = getattr(obj, "next_verification_date", None)
        if not date:
            return "—"

        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        if date < today:
            return format_html('<span style="color:#b91c1c;font-weight:600;">Expired</span>')
        if date <= today + timedelta(days=30):
            return format_html('<span style="color:#b45309;font-weight:600;">30 days</span>')
        if date <= today + timedelta(days=90):
            return format_html('<span style="color:#1d4ed8;font-weight:600;">90 days</span>')
        return format_html('<span style="color:#15803d;font-weight:600;">OK</span>')

    verification_badge.short_description = "Төлөв"

    def save_model(self, request, obj, form, change):
        if getattr(obj, "location_id", None):
            if hasattr(obj, "aimag_id") and not obj.aimag_id and getattr(obj.location, "aimag_id", None):
                obj.aimag_id = obj.location.aimag_id
            if hasattr(obj, "sum_id") and not obj.sum_id and getattr(obj.location, "sum_id", None):
                obj.sum_id = obj.location.sum_id
        super().save_model(request, obj, form, change)