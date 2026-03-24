from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin as django_default_admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from inventory.admin import inventory_admin_site

urlpatterns = [
    path("", include(("inventory.urls", "inventory"), namespace="inventory")),

    # Main custom admin
    path("admin/", inventory_admin_site.urls),

    # Legacy redirects
    path(
        "django-admin/",
        RedirectView.as_view(url="/admin/", permanent=False),
    ),
    re_path(
        r"^django-admin/(?P<extra>.*)$",
        RedirectView.as_view(url="/admin/%(extra)s", permanent=False),
    ),

    # Default Django admin
    path("system-admin/", django_default_admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)