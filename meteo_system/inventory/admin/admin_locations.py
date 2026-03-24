from django.contrib import admin
from django import forms
from inventory.models import Location, Device
from .admin_site import inventory_admin_site


@admin.register(Location, site=inventory_admin_site)
class LocationAdmin(admin.ModelAdmin):
    pass


@admin.register(Device, site=inventory_admin_site)
class DeviceAdmin(admin.ModelAdmin):
    pass

class LocationAdminForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = "__all__"

    class Media:
        js = (
            "admin/js/location_cascade.js",
        )


@admin.register(Location, site=inventory_admin_site)
class LocationAdmin(admin.ModelAdmin):
    form = LocationAdminForm

    list_display = (
        "name",
        "location_type",
        "aimag",
        "sum",
        "latitude",
        "longitude",
        "is_active",
    )
    list_filter = (
        "location_type",
        "is_active",
        AimagListFilter,
        SumListFilter,
    )
    search_fields = (
        "name",
        "code",
        "wigos_id",
    )
    autocomplete_fields = ()
    list_per_page = 50

    fieldsets = (
        ("Үндсэн мэдээлэл", {
            "fields": ("name", "code", "location_type", "is_active"),
        }),
        ("Захиргааны байршил", {
            "fields": ("aimag", "sum"),
        }),
        ("Координат", {
            "fields": ("latitude", "longitude", "elevation_m"),
        }),
        ("WMO / OSCAR", {
            "fields": ("wigos_id",),
            "classes": ("collapse",),
        }),
    )