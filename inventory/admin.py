from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path
from .models import *
from .views import device_import_csv

# A. Суурь эрхийн класс - ЦУОШГ болон БОХЗТЛ-ийн хяналтыг нэгтгэв
class BaseAimagAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            profile = request.user.userprofile
            if profile.role in ['NAMEM_HQ', 'LAB_RIC']:
                return qs
            return qs.filter(location__aimag_ref=profile.aimag)
        except UserProfile.DoesNotExist:
            return qs.none() if not request.user.is_superuser else qs

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# --- Inline бүртгэлүүд ---

class DeviceAttachmentInline(admin.TabularInline):
    model = DeviceAttachment
    extra = 1

class CalibrationRecordInline(admin.TabularInline):
    model = CalibrationRecord
    extra = 1

class DeviceFaultInline(admin.TabularInline):
    model = DeviceFault
    extra = 1
    verbose_name = "Эвдрэлийн түүх"
    verbose_name_plural = "Эвдрэлийн түүхүүд"

# --- Үндсэн Admin классууд ---

@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag")
    list_filter = ("aimag",)
    search_fields = ("name",)

@admin.register(Location)
class LocationAdmin(BaseAimagAdmin):
    list_display = ("name", "wmo_index", "location_type", "aimag_ref", "get_full_location", "display_owner", "view_on_map")
    list_filter = ("location_type", "aimag_ref")
    search_fields = ("name", "wmo_index")
    autocomplete_fields = ['aimag_ref', 'sum_ref'] 
    
    class Media:
        js = (
            'https://code.jquery.com/jquery-3.6.0.min.js', 
            'inventory/js/location_chained.js', 
        )

    def get_full_location(self, obj):
        # "Аймаг - Сум" хэлбэрээр харуулна
        if obj.sum_ref:
            return f"{obj.aimag_ref.name} - {obj.sum_ref.name}"
        return f"{obj.aimag_ref.name} - Сум тодорхойгүй"
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
    # Fieldsets ашиглан "Бусад" талбарыг тод харуулж, бүтцийг зохион байгуулав
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('master_device', 'other_device_name', 'serial_number', 'device_type', 'location', 'status')
        }),
        ('Ашиглалт ба Баталгаажуулалт', {
            'fields': ('installation_date', 'lifespan_years', 'valid_until')
        }),
    )
    list_display = ("serial_number", "display_device_name", "location", "status", "lifespan_status", "calibration_status")
    list_filter = ("status", "device_type", "location__aimag_ref")
    search_fields = ("serial_number", "master_device__name", "other_device_name")
    inlines = [DeviceAttachmentInline, CalibrationRecordInline, DeviceFaultInline]

    def display_device_name(self, obj):
        # Хэрэв гараар нэр оруулсан бол цэнхэр курсивээр харуулна
        if obj.other_device_name:
            return format_html('<i style="color: blue;">{} (Бусад)</i>', obj.other_device_name)
        return str(obj.master_device)
    display_device_name.short_description = "Төрөл (Загвар)"

    def lifespan_status(self, obj):
        expiry = obj.lifespan_expiry
        if not expiry: return "-"
        today = timezone.now().date()
        if expiry < today:
            return format_html('<b style="color:red;">Дууссан ({})</b>', expiry)
        if expiry <= today + timezone.timedelta(days=180):
            return format_html('<b style="color:orange;">Шинэчлэх дөхсөн ({})</b>', expiry)
        return f"{expiry} хүртэл"
    lifespan_status.short_description = "Ашиглалтын хугацаа"

    def calibration_status(self, obj):
        if not obj.valid_until: return format_html('<span style="color:gray;">Мэдээлэлгүй</span>')
        diff = (obj.valid_until - timezone.now().date()).days
        color = "red" if diff <= 0 else "orange" if diff <= 60 else "green"
        text = f"Хэтэрсэн ({abs(diff)} х)" if diff <= 0 else f"Дуусах дөхсөн ({diff} х)" if diff <= 60 else "Хэвийн"
        return format_html('<b style="color: {};">{}</b>', color, text)
    calibration_status.short_description = "Баталгаажуулалт"

    def get_urls(self):
        urls = super().get_urls()
        return [path('import-csv/', self.admin_site.admin_view(device_import_csv), name='inventory_device_import_csv')] + urls

@admin.register(StandardInstrument)
class StandardInstrumentAdmin(admin.ModelAdmin):
    # "Бусад" талбарыг жагсаалт болон засварлах цонхонд нэмэв
    list_display = ("name", "other_standard_name", "serial_number", "accuracy_class", "last_calibration")
    fields = ("name", "other_standard_name", "serial_number", "accuracy_class", "last_calibration")
    search_fields = ("name", "other_standard_name", "serial_number")

@admin.register(CalibrationRecord)
class CalibrationRecordAdmin(admin.ModelAdmin):
    list_display = ("device", "certificate_no", "issue_date", "expiry_date")
    search_fields = ("certificate_no", "device__serial_number")

@admin.register(DeviceFault)
class DeviceFaultAdmin(admin.ModelAdmin):
    list_display = ("device", "reported_date", "is_fixed", "fixed_date")
    list_filter = ("is_fixed", "reported_date")
    search_fields = ("device__serial_number", "fault_description")

@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "aimag", "status", "created_at")
    list_filter = ("status", "aimag")

admin.site.register([Organization, MasterDevice, UserProfile, DeviceCategory])