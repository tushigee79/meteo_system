from django.contrib import admin
from django.utils.html import format_html
from .models import Aimag, Soum, Location, Device, Maintenance, Calibration, UserProfile, Organization
from .views import device_import_csv

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # Байгууллага (owner_org)-ыг жагсаалтад нэмсэн
    list_display = ("name", "location_type", "aimag_ref", "owner_org", "view_on_map")
    list_filter = ("location_type", "aimag_ref", "owner_org") # Шүүлтүүрт байгууллага нэмсэн
    search_fields = ("name", "wmo_index")
    
    def view_on_map(self, obj):
        if obj.latitude and obj.longitude:
            return format_html('<a href="/inventory/map/?name={}" target="_blank">📍 Харах</a>', obj.name)
        return "Координатгүй"
    view_on_map.short_description = "Газрын зураг"

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "serial_number", "status", "last_calibration_date")
    list_filter = ("status", "location__aimag_ref")