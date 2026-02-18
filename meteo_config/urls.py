# meteo_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, reverse

from inventory.admin_site import inventory_admin_site  # ✅ ганц эх үүсвэр
from inventory.views_qr import qr_public, qr_passport_pdf


def root_redirect(request):
    # custom AdminSite.name = "inventory_admin" тул index нь inventory_admin:index
    return redirect(reverse("inventory_admin:index"))


urlpatterns = [
    path("", root_redirect),
    path("django-admin/", inventory_admin_site.urls),

    # Public QR endpoints
    path("qr/<uuid:token>/", qr_public, name="qr_public"),
    path("qr/<uuid:token>/passport.pdf", qr_passport_pdf, name="qr_passport_pdf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
