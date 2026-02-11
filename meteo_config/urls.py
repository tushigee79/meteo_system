# meteo_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, include

from inventory.views_qr import qr_public, qr_passport_pdf
from inventory.admin_site import inventory_admin_site  # ✅ ганц эх үүсвэр

urlpatterns = [
    # App routes
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # Custom Admin site
    path("django-admin/", inventory_admin_site.urls),

    # Redirect shortcuts
    path("admin/login/",  lambda request: redirect("/django-admin/login/", permanent=False)),
    path("admin/logout/", lambda request: redirect("/django-admin/logout/", permanent=False)),
    path("admin/",        lambda request: redirect("/django-admin/", permanent=False)),

    # Public QR
    path("qr/public/<uuid:token>/", qr_public, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", qr_passport_pdf, name="qr_device_public_passport_pdf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
