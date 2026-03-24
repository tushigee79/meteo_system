# inventory/admin/admin_devices.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from inventory.models import Device
from .admin_filters import AimagListFilter, SumListFilter


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def clean_serial_number(self):
        serial = (self.cleaned_data.get("serial_number") or "").strip()
        if not serial:
            return serial

        qs = Device.objects.filter(serial_number=serial)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ижил серийн дугаартай багаж аль хэдийн бүртгэлтэй байна.")
        return serial


class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm

    list_display = (
        "id",
        "serial_number",
        "kind",
        "status_badge",
        "location",
        "manufacturer_safe",
        "verification_badge",
    )
    list_filter = (
        "kind",
        "status",
        AimagListFilter,
        SumListFilter,
    )
    search_fields = (
        "serial_number",
        "manufacturer",
        "model",
    )
    autocomplete_fields = (
        "location",
    )
    readonly_fields = (
        "qr_preview",
    )
    ordering = ("-id",)
    list_per_page = 50

    fieldsets = (
        ("Үндсэн мэдээлэл", {
            "fields": (
                "kind",
                "status",
                "serial_number",
            )
        }),
        ("Үйлдвэрлэгч / Загвар", {
            "fields": (
                "manufacturer",
                "model",
            )
        }),
        ("Байршил", {
            "fields": (
                "location",
            )
        }),
        ("Баталгаажуулалт / Калибровка", {
            "fields": (
                "last_verification_date",
                "next_verification_date",
            ),
            "classes": ("collapse",),
        }),
        ("QR", {
            "fields": (
                "qr_preview",
            ),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Төлөв")
    def status_badge(self, obj):
        status = (getattr(obj, "status", "") or "").lower()

        label_map = {
            "active": ("#198754", "Ашиглагдаж буй"),
            "broken": ("#dc3545", "Эвдрэлтэй"),
            "repair": ("#fd7e14", "Засварт"),
            "spare": ("#0d6efd", "Нөөц"),
            "retired": ("#6c757d", "Хасагдсан"),
        }

        color, label = label_map.get(status, ("#6c757d", getattr(obj, "status", "-") or "-"))
        return format_html(
            '<span style="padding:4px 8px;border-radius:12px;background:{};color:white;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Үйлдвэрлэгч")
    def manufacturer_safe(self, obj):
        return getattr(obj, "manufacturer", "") or "-"

    @admin.display(description="Баталгаажуулалт")
    def verification_badge(self, obj):
        next_date = getattr(obj, "next_verification_date", None)
        if not next_date:
            return "-"

        try:
            from django.utils import timezone
            today = timezone.localdate()
            diff = (next_date - today).days

            if diff < 0:
                color = "#dc3545"
                label = f"Хугацаа дууссан ({abs(diff)} хоног)"
            elif diff <= 30:
                color = "#ffc107"
                label = f"{diff} хоног үлдсэн"
            elif diff <= 90:
                color = "#0dcaf0"
                label = f"{diff} хоног үлдсэн"
            else:
                color = "#198754"
                label = f"{diff} хоног үлдсэн"

            return format_html(
                '<span style="padding:4px 8px;border-radius:12px;background:{};color:black;">{}</span>',
                color,
                label,
            )
        except Exception:
            return str(next_date)

    @admin.display(description="QR")
    def qr_preview(self, obj):
        token = getattr(obj, "public_token", None)
        if not obj.pk or not token:
            return "Хадгалсны дараа QR харагдана"

        url = f"/qr/public/{token}/"
        return format_html('<a href="{}" target="_blank">Нээлттэй QR хуудас</a>', url)