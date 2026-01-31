# meteo_config/urls.py (clean) - 2026-01-31
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.shortcuts import redirect

from inventory.admin import inventory_admin_site


urlpatterns = [
    # All app URLs are namespaced under "inventory:"
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # Custom admin site (namespace = "admin")
    path("django-admin/", inventory_admin_site.urls),

    # Shortcuts
    path("admin/", lambda request: redirect("/django-admin/", permanent=False)),
    path("admin/login/", lambda request: redirect("/django-admin/login/", permanent=False)),
    path("admin/logout/", lambda request: redirect("/django-admin/logout/", permanent=False)),
]

# Static / Media (DEBUG үед)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
