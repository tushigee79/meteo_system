# meteo_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, include

from inventory.admin import inventory_admin_site

urlpatterns = [
    # 1) APP routes (namespace = inventory)
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # 2) Admin site
    path("django-admin/", inventory_admin_site.urls),

    # 3) Redirect shortcuts
    path("admin/login/",  lambda request: redirect("/django-admin/login/", permanent=False)),
    path("admin/logout/", lambda request: redirect("/django-admin/logout/", permanent=False)),
    path("admin/",        lambda request: redirect("/django-admin/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
