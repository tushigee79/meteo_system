from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect

from .models import Location, Aimag, Soum, UserProfile, InternalMessage


class SoumByAimagFilter(admin.SimpleListFilter):
    title = "Сум / Дүүрэг"
    parameter_name = "soum_ref__id__exact"   # ✅ Location.soum_ref

    def lookups(self, request, model_admin):
        aimag_id = request.GET.get("aimag_ref__id__exact")  # ✅ Location.aimag_ref

        qs = Soum.objects.all()
        if aimag_id:
            # ✅ Soum model дээр аймаг FK-ийн талбарын нэр ихэвчлэн "aimag"
            qs = qs.filter(aimag_id=aimag_id)

        return [(s.id, str(s)) for s in qs.order_by("name")]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(soum_ref_id=val)
        return queryset


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag_ref", "soum_ref", "location_type", "wmo_index")
    list_filter = ("location_type", "aimag_ref", SoumByAimagFilter)
    search_fields = ("name", "wmo_index", "wigos_id")


@admin.register(Aimag)
class AimagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Soum)
class SoumAdmin(admin.ModelAdmin):
    list_display = ("name", "aimag")
    list_filter = ("aimag",)
    search_fields = ("name", "aimag__name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "aimag", "is_engineer")
    list_filter = ("is_engineer", "aimag")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(InternalMessage)
class InternalMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__username", "receiver__username", "message")


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
