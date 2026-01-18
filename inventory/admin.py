import json
import datetime
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string

# PDF үүсгэх сан (pip install xhtml2pdf)
from xhtml2pdf import pisa 

# Моделиуд болон Харагдацуудыг импортлох
from .models import (
    Aimag, SumDuureg, Organization, Location, Device, 
    MasterDevice, UserProfile, DeviceCategory, 
    StandardInstrument, CalibrationRecord, DeviceFault, 
    SparePartOrder, SparePartItem
)
from .views import (
    device_import_csv, national_dashboard, download_aimag_template,
    import_engineers_from_csv, download_retired_archive
)

# Админ панелийн нүүрийг Dashboard болгох
admin.site.index = national_dashboard

# --- A. Суурь эрхийн класс ---
class BaseAimagAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser: return qs
        try:
            profile = request.user.userprofile
            if profile.role in ['NAMEM_HQ', 'LAB_RIC']: return qs
            if self.model == Location:
                return qs.filter(aimag_ref=profile.aimag)
            return qs.filter(location__aimag_ref=profile.aimag)
        except UserProfile.DoesNotExist: return qs.none() if not request.user.is_superuser else qs

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# --- B. Сэлбэг захиалгын Инлайн тохиргоо ---
class SparePartItemInline(admin.TabularInline):
    model = SparePartItem
    extra = 1
    autocomplete_fields = ['device_type']

# --- C. Үндсэн Админ классууд ---

@admin.register(MasterDevice)
class MasterDeviceAdmin(admin.ModelAdmin):
    search_fields = ("name", "category__name")
    list_display = ("name", "category")

@admin.register(Location)
class LocationAdmin(BaseAimagAdmin):
    list_display = ("name", "location_type", "aimag_ref", "sum_ref", "wmo_index", "view_on_map")
    list_filter = ("location_type", "aimag_ref", "sum_ref") # Шүүлтүүрүүд
    search_fields = ("name", "wmo_index")
    autocomplete_fields = ['aimag_ref', 'sum_ref']
    change_list_template = "admin/inventory/location/change_list.html"

    def view_on_map(self, obj):
        if obj.latitude and obj.longitude:
            url = f"/inventory/map/?name={obj.name}"
            return format_html('<a href="{}" target="_blank" style="color: #e83e8c; font-weight: bold;">📍 Харах</a>', url)
        return format_html('<span style="color: #999;">Координатгүй</span>')
    
    view_on_map.short_description = "Газрын зураг"

    def changelist_view(self, request, extra_context=None):
        # 1. Ерөнхий response авах
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            # 2. Sidebar шүүлтүүрээр шүүгдсэн queryset-ийг авч байна
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        # 3. Зөвхөн шүүгдсэн станцуудыг газрын зурагт зориулж бэлдэх
        map_data = [{
            'id': loc.id,
            'name': loc.name,
            'lat': loc.latitude,
            'lon': loc.longitude,
            'type': loc.location_type,
            'aimag_id': loc.aimag_ref.id,
            'sum_id': loc.sum_ref.id if loc.sum_ref else None,
        } for loc in qs.exclude(latitude__isnull=True, longitude__isnull=True)]

        # 4. Хайлтын системд зориулсан Аймаг, Сумын жагсаалт
        aimags = list(Aimag.objects.values('id', 'name'))
        sums = list(SumDuureg.objects.values('id', 'name', 'aimag_id'))

        # 5. Context-ийг шинэчлэн дамжуулах
        response.context_data.update({
            'locations_json': json.dumps(map_data),
            'aimags_json': json.dumps(aimags),
            'sums_json': json.dumps(sums),
        })
        return response

@admin.register(Device)
class DeviceAdmin(BaseAimagAdmin):
    list_display = ("serial_number", "master_device", "location", "status")
    change_list_template = "admin/inventory/device/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(device_import_csv), name='inventory_device_import_csv'),
        ]
        return custom_urls + urls

@admin.register(SparePartOrder)
class SparePartOrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'aimag', 'station', 'status', 'print_button')
    list_filter = ('status', 'aimag', 'created_at')
    inlines = [SparePartItemInline]
    readonly_fields = ('order_no',)

    def save_model(self, request, obj, form, change):
        if not obj.order_no:
            last_order = SparePartOrder.objects.all().order_by('id').last()
            new_id = (last_order.id + 1) if last_order else 1
            obj.order_no = f"REQ-{datetime.date.today().year}-{new_id:04d}"
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/print/', self.admin_site.admin_view(self.print_order), name='print_spare_order'),
        ]
        return custom_urls + urls

    def print_button(self, obj):
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #447e9b; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">🖨 Хэвлэх</a>',
            reverse('admin:print_spare_order', args=[obj.pk])
        )

    def print_order(self, request, order_id):
        order = SparePartOrder.objects.get(pk=order_id)
        items = order.items.all()
        context = {'order': order, 'items': items, 'today': timezone.now()}
        html = render_to_string('admin/inventory/spare_order_print.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="Order_{order.order_no}.pdf"'
        pisa.CreatePDF(html, dest=response)
        return response

# --- D. Туслах модулиудыг бүртгэх ---
@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(SumDuureg)
class SumDuuregAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "aimag")

admin.site.register([
    Organization, UserProfile, DeviceCategory, 
    StandardInstrument, CalibrationRecord, DeviceFault
])