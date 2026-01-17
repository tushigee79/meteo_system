from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect, render
from django import forms
from django.contrib import messages
import csv
import io
from .models import Aimag, Soum, UserProfile, InternalMessage, Device, Location

# CSV файл сонгох форм
class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV файл сонгох")

# =====================================================
# 1. Аймгийн эрхийн Mixin (Чеклист #2)
# =====================================================
class AimagScopedAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        profile = getattr(request.user, 'profile', None)
        if profile and profile.aimag:
            if hasattr(self.model, 'aimag_ref'):
                return qs.filter(aimag_ref=profile.aimag)
            if hasattr(self.model, 'location'):
                return qs.filter(location__aimag_ref=profile.aimag)
        return qs

# =====================================================
# 2. Моделиудын бүртгэл
# =====================================================

@admin.register(Location)
class LocationAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "aimag_ref", "soum_ref", "location_type", "wmo_index")
    list_filter = ("location_type", "aimag_ref")
    search_fields = ("name", "wmo_index", "wigos_id")

@admin.register(Device)
class DeviceAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "serial_number", "get_location", "get_aimag")
    list_filter = ("location__aimag_ref",)
    search_fields = ("name", "serial_number")
    
    # CSV импортлох тохиргоо
    change_list_template = "admin/inventory/device_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='inventory_device_import_csv'),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Зөвхөн .csv файл оруулна уу.')
                return redirect("..")
            
            # Энд CSV унших логик бичиж болно
            messages.success(request, 'CSV файл амжилттай уншигдлаа (Туршилт).')
            return redirect("admin:inventory_device_changelist")

        form = CsvImportForm()
        payload = {"form": form, "opts": self.model._meta}
        return render(request, "admin/csv_form.html", payload)

    @admin.display(description='Байршил')
    def get_location(self, obj):
        return obj.location.name if obj.location else "-"

    @admin.display(description='Аймаг')
    def get_aimag(self, obj):
        return obj.location.aimag_ref.name if obj.location and obj.location.aimag_ref else "-"

@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(Soum)
class SoumAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag")
    list_filter = ("aimag",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "is_engineer")

@admin.register(InternalMessage)
class InternalMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "created_at", "is_read")
    list_filter = ("is_read", "created_at")

# =====================================================
# 3. Брэндинг
# =====================================================
admin.site.site_header = "БҮРТГЭЛ систем"
admin.site.site_title = "БҮРТГЭЛ"
admin.site.index_title = "Удирдлагын самбар"