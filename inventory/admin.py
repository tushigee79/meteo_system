from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect

from .models import Location, Aimag, Soum


# ============================
# Changelist filter: Soum depends on Aimag
# ============================

class SoumByAimagFilter(admin.SimpleListFilter):
    title = "Сум / Дүүрэг"
    parameter_name = "soum_fk__id__exact"

    def lookups(self, request, model_admin):
        aimag_id = request.GET.get("aimag_fk__id__exact")

        qs = Soum.objects.all()
        if aimag_id:
            qs = qs.filter(aimag_id=aimag_id)  # Soum.aimag FK

        return [(s.id, str(s)) for s in qs.order_by("name")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(soum_fk_id=val)
        return queryset


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag_fk", "soum_fk", "location_type", "status")
    list_filter = ("location_type", "aimag_fk", SoumByAimagFilter, "status")
    search_fields = ("name", "wmo_index", "wigos_id")


@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


# ============================
# Admin branding
# ============================
admin.site.site_header = "БҮРТГЭЛ систем"
admin.site.site_title = "БҮРТГЭЛ"
admin.site.index_title = "Удирдлагын самбар"


# ============================
# Safe admin URL extension
# ============================

def map_view(request):
    return redirect("/inventory/map/")


_original_get_urls = admin.site.get_urls

def get_urls():
    urls = _original_get_urls()
    custom = [
        path("map/", admin.site.admin_view(map_view), name="inventory-map"),
    ]
    return custom + urls


admin.site.get_urls = get_urls
