# meteo_config/urls.py
from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path

from inventory.admin import inventory_admin_site

urlpatterns = [
    # Inventory public urls (namespace="inventory")
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # Custom admin site
    path("django-admin/", inventory_admin_site.urls),

    # Shortcuts
    path("admin/login/", lambda request: redirect("/django-admin/login/", permanent=False)),
    path("admin/logout/", lambda request: redirect("/django-admin/logout/", permanent=False)),
    path("admin/", lambda request: redirect("/django-admin/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
