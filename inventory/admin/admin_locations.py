# inventory/admin/admin_locations.py
from django.contrib import admin

from inventory.models import Location


class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "location_type",
        "aimag_ref",
        "sum_ref",
        "latitude",
        "longitude",
        "device_count",
    )
    list_filter = (
        "location_type",
        "aimag_ref",
        "sum_ref",
    )
    search_fields = (
        "name",
        "code",
        "wigos_id",
    )
    ordering = ("name",)
    list_per_page = 50

    fieldsets = (
        ("Үндсэн мэдээлэл", {
            "fields": (
                "name",
                "code",
                "location_type",
                "organization",
            )
        }),
        ("Байршил", {
            "fields": (
                "aimag_ref",
                "sum_ref",
                "latitude",
                "longitude",
                "elevation",
            )
        }),
        ("WMO / Metadata", {
            "fields": (
                "wigos_id",
            ),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Багажийн тоо")
    def device_count(self, obj):
        try:
            return obj.device_set.count()
        except Exception:
            return 0