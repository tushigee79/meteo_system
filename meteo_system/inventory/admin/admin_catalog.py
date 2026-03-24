from django.contrib import admin
from .admin_site import inventory_admin_site
from ..models import InstrumentCatalog


@admin.register(InstrumentCatalog, site=inventory_admin_site)
class InstrumentCatalogAdmin(admin.ModelAdmin):
    list_display = ("name_mn", "model", "kind", "verification_cycle_months")
    list_filter = ("kind",)
    search_fields = ("name_mn", "model")