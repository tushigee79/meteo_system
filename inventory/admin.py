from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from .models import Aimag, Soum, Location, Device, Maintenance, Calibration, UserProfile, Organization
from .views import device_import_csv

# 1. Байгууллагын админ
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")

# 2. Аймаг, Сумын админ
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)

@admin.register(Soum)
class SoumAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag", "created_at")
    list_filter = ("aimag",)
    search_fields = ("name",)

# 3. Байршил (Location) админ
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # 'owner_org'-ыг 'display_owner_org' функцээр сольсон
    list_display = ("name", "location_type", "aimag_ref", "display_owner_org", "view_on_map")
    list_filter = ("location_type", "aimag_ref", "owner_org")
    search_fields = ("name", "wmo_index")
    
    def display_owner_org(self, obj):
        """Байгууллагыг автоматаар нэрлэх логик"""
        if obj.owner_org:
            return obj.owner_org.name
        if obj.aimag_ref:
            # Аймаг сонгогдсон бол автоматаар 'УЦУОШТ' залгана
            return f"{obj.aimag_ref.name} УЦУОШТ"
        return "-"
    display_owner_org.short_description = "Эзэмшигч байгууллага"
    
    def view_on_map(self, obj):
        if obj.latitude and obj.longitude:
            url = reverse('inventory:location_map') + f"?name={obj.name}"
            return format_html('<a href="{}" target="_blank" style="text-decoration:none;">📍 Харах</a>', url)
        return "Координатгүй"
    view_on_map.short_description = "Газрын зураг"

# 4. Багаж хэрэгсэл (Device) админ
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "serial_number", "status", "last_calibration_date")
    list_filter = ("status", "location__aimag_ref")
    search_fields = ("name", "serial_number")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(device_import_csv), name='inventory_device_import_csv'),
        ]
        return custom_urls + urls

# 5. Засвар үйлчилгээ ба Баталгаажуулалт
@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ("device", "maintenance_type", "date", "performed_by")
    list_filter = ("maintenance_type", "date")

@admin.register(Calibration)
class CalibrationAdmin(admin.ModelAdmin):
    list_display = ("device", "calibration_date", "expiry_date", "is_valid")
    list_filter = ("calibration_date", "is_valid")

# 6. Хэрэглэгчийн профиль
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "role")
    list_filter = ("role", "aimag")