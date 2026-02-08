# meteo_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, include
from django.urls import path
from inventory.views_qr import qr_public, qr_passport_pdf

# inventory/admin.py дотор нэгтгэсэн inventory_admin_site-ийг импортлох
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
     path("qr/public/<uuid:token>/", qr_public, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", qr_passport_pdf, name="qr_device_public_passport_pdf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)