from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path
from .models import *
from .views import device_import_csv

# A. Суурь эрхийн класс
class BaseAimagAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser: 
            return qs
        return qs.filter(location__aimag_ref=request.user.userprofile.aimag)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class DeviceAttachmentInline(admin.TabularInline):
    model = DeviceAttachment
    extra = 1

@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",) # Autocomplete-д заавал хэрэгтэй

@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag")
    list_filter = ("aimag",)
    search_fields = ("name",) # Autocomplete-д заавал хэрэгтэй

@admin.register(Location)
class LocationAdmin(BaseAimagAdmin):
    # 'get_full_location' нэгтгэсэн баганыг 'sum_ref'-ийн оронд нэмэв
    list_display = ("name", "location_type", "aimag_ref", "get_full_location", "display_owner", "view_on_map")
    list_filter = ("location_type", "aimag_ref")
    search_fields = ("name",)
    autocomplete_fields = ['aimag_ref', 'sum_ref'] 
    
    # Динамик шүүлтүүр (Aimag -> Sum & Org) JavaScript холболт
    class Media:
        js = (
            'https://code.jquery.com/jquery-3.6.0.min.js', 
            'inventory/js/location_chained.js', 
        )

    # Станцын нэрийг Сумтай нь давхар оруулж харуулах логик
    def get_full_location(self, obj):
        if obj.sum_ref:
            return f"{obj.aimag_ref.name} - {obj.sum_ref.name}"
        return "-"
    get_full_location.short_description = "Сум/Дүүрэг"

    def display_owner(self, obj):
        if obj.owner_org: 
            return obj.owner_org.name
        return f"{obj.aimag_ref.name} УЦУОШТ" if obj.aimag_ref else "-"
    display_owner.short_description = "Эзэмшигч байгууллага"

    def view_on_map(self, obj):
        if obj.latitude and obj.longitude:
            url = f"/inventory/map/?name={obj.name}"
            return format_html('<a href="{}" target="_blank" style="text-decoration:none;">📍 Харах</a>', url)
        return "Координатгүй"
    view_on_map.short_description = "Газрын зураг"

@admin.register(Device)
class DeviceAdmin(BaseAimagAdmin):
    list_display = ("get_name", "serial_number", "get_device_owner", "calibration_status")
    inlines = [DeviceAttachmentInline]

    def get_urls(self):
        urls = super().get_urls()
        return [path('import-csv/', self.admin_site.admin_view(device_import_csv), name='inventory_device_import_csv')] + urls

    def get_name(self, obj): return str(obj)
    
    def get_device_owner(self, obj):
        if not obj.location: return "-"
        if obj.location.owner_org: 
            return obj.location.owner_org.name
        return f"{obj.location.aimag_ref.name} УЦУОШТ" if obj.location.aimag_ref else "-"
    get_device_owner.short_description = "Эзэмшигч байгууллага"

    def calibration_status(self, obj):
        if not obj.valid_until: 
            return format_html('<span style="color:gray;">Мэдээлэлгүй</span>')
        diff = (obj.valid_until - timezone.now().date()).days
        color = "red" if diff <= 0 else "orange" if diff <= 30 else "blue" if diff <= 90 else "green"
        text = f"Хэтэрсэн ({abs(diff)} х)" if diff <= 0 else f"Шар ({diff} х)" if diff <= 30 else f"Цэнхэр ({diff} х)" if diff <= 90 else "Хэвийн"
        return format_html('<b style="color: {};">{}</b>', color, text)

@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "aimag", "status", "created_at")
    list_filter = ("status", "aimag")

admin.site.register([Organization, MasterDevice, UserProfile])