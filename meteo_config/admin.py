import json
from django.contrib.admin import AdminSite
from django.contrib import admin
from .models import Location # Модел үүсгэсний дараа ажиллана

class BurtgelAdminSite(AdminSite):
    site_header = "NAMEM БҮРТГЭЛ"
    index_template = "admin/index.html" #

    def each_context(self, request):
        ctx = super().each_context(request)
        # Координаттай байршлуудыг шүүж авах
        locations = Location.objects.filter(latitude__isnull=False, longitude__isnull=False)
        loc_payload = [{"name": l.name_mn, "lat": float(l.latitude), "lon": float(l.longitude)} for l in locations]
        ctx["locations_json"] = json.dumps(loc_payload, ensure_ascii=False)
        return ctx

admin_site = BurtgelAdminSite(name="admin_site")