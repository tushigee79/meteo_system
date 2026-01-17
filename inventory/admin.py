from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from .models import Aimag, Soum, Location, Device, Maintenance, Calibration, UserProfile, Organization
from .views import device_import_csv

# 1. Аймгийн инженер зөвхөн өөрийн аймгийн датаг харах Mixin
class AimagScopedAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            profile = getattr(request.user, 'userprofile', None)
            if profile and profile.aimag:
                if hasattr(self.model, 'aimag_ref'):
                    return qs.filter(aimag_ref=profile.aimag)
                if hasattr(self.model, 'location'):
                    return qs.filter(location__aimag_ref=profile.aimag)
        except Exception:
            pass
        return qs

# 2. Байгууллагын админ (Шинээр нэмэгдсэн)
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")

# 3. Аймаг, Сумын админ
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)

@admin.register(Soum)
class SoumAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag", "created_at")
    list_filter = ("aimag",)
    search_fields = ("name",)

# 4. Байршил (Location) админ
@admin.register(Location)
class LocationAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    # list_display-д 'owner_org' нэмж байгууллагыг харуулна
    list_display = ("name", "location_type", "aimag_ref", "soum_ref", "owner_org", "view_on_map")
    # list_filter-д 'owner_org' нэмж байгууллагаар шүүх боломжтой болгов
    list_filter = ("location_type", "aimag_ref", "owner_org")
    search_fields = ("name", "wmo_index")
    
    def view_on_map(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="/inventory/map/?name={}" target="_blank" style="text-decoration:none;">📍 Харах</a>',
                obj.name
            )
        return "Координатгүй"
    view_on_map.short_description = "Газрын зураг"

# 5. Багаж хэрэгсэл (Device) админ
@admin.register(Device)
class DeviceAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "serial_number", "get_location", "get_aimag", "status", "last_calibration_date")
    list_filter = ("status", "location__aimag_ref")
    search_fields = ("name", "serial_number")
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(device_import_csv),
                name='inventory_device_import_csv',
            ),
        ]
        return custom_urls + urls

    def get_location(self, obj):
        return obj.location.name if obj.location else "-"
    get_location.short_description = "Байршил"

    def get_aimag(self, obj):
        return obj.location.aimag_ref.name if obj.location and obj.location.aimag_ref else "-"
    get_aimag.short_description = "Аймаг"

# 6. Засвар үйлчилгээ ба Баталгаажуулалт
@admin.register(Maintenance)
class MaintenanceAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("device", "maintenance_type", "date", "performed_by")
    list_filter = ("maintenance_type", "date")

@admin.register(Calibration)
class CalibrationAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("device", "calibration_date", "expiry_date", "is_valid")
    list_filter = ("calibration_date", "is_valid")

# 7. Хэрэглэгчийн профиль
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "role")
    list_filter = ("role", "aimag")