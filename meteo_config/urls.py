# meteo_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from inventory.admin import inventory_admin_site
from django.contrib import admin as django_default_admin # Import-ыг дээр гаргалаа

urlpatterns = [
    # 1. Апп-ын үндсэн замууд
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # 2. Тусгай админ сайт
    path("admin/", inventory_admin_site.urls),

    # 3. Стандарт Django админ
    path("system-admin/", django_default_admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)