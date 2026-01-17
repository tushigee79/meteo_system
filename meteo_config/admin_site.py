from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import redirect

class MeteoAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ систем"
    site_title = "БҮРТГЭЛ"
    index_title = "Удирдлагын самбар"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("map/", self.admin_view(lambda request: redirect("/inventory/map/")), name="map"),
        ]
        return custom + urls

admin_site = MeteoAdminSite(name="meteo_admin")
