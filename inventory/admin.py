from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect

from .models import Location, Aimag


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag_fk", "location_type", "status")
    list_filter = ("location_type", "aimag_fk")


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
