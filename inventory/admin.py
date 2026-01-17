from django.urls import path # Импорт хэсэгт нэмээрэй
from django.shortcuts import render # Импорт хэсэгт нэмээрэй
from django import forms # Импорт хэсэгт нэмээрэй

# CSV файл сонгох форм
class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

@admin.register(Device)
class DeviceAdmin(AimagScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "serial_number", "get_location", "get_aimag")
    list_filter = ("location__aimag_ref",)
    search_fields = ("name", "serial_number")
    
    # CSV импортлох товчийг админ панелд нэмэх
    change_list_template = "admin/inventory/device_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='inventory_device_import_csv'),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            # Энд CSV унших логик бичигдэнэ
            pass
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

    @admin.display(description='Байршил')
    def get_location(self, obj):
        return obj.location.name if obj.location else "-"

    @admin.display(description='Аймаг')
    def get_aimag(self, obj):
        return obj.location.aimag_ref.name if obj.location and obj.location.aimag_ref else "-"