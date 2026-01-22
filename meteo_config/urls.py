# meteo_config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from inventory.admin_dashboard import (
    dashboard_table_view,
    dashboard_graph_view,
    export_devices_csv,
)

from inventory.views import location_map, station_map_view
from inventory.views_district_api import lookup_district_api
from inventory.views_auth import force_password_change

urlpatterns = [
    # =========================
    # 1) API
    # =========================
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),

    # =========================
    # 2) DASHBOARDS
    # =========================
    path("admin/dashboard/table/", dashboard_table_view, name="dashboard_table"),
    path("admin/dashboard/graph/", dashboard_graph_view, name="dashboard_graph"),
    path("admin/dashboard/export/devices.csv/", export_devices_csv, name="export_devices_csv"),
    path("admin/dashboard/", lambda request: redirect("/admin/dashboard/graph/", permanent=False)),

    # =========================
    # 3) SHORTCUT REDIRECTS
    # =========================
    path("admin/", lambda request: redirect("/django-admin/", permanent=False)),
    path("admin/login/", lambda request: redirect("/django-admin/login/", permanent=False)),
    path("admin/logout/", lambda request: redirect("/django-admin/logout/", permanent=False)),

    # =========================
    # 4) INVENTORY URLS (✅ эндээс API ажиллана)
    # =========================
    path("inventory/", include("inventory.urls")),

    # =========================
    # 5) MAP (хуучин замаа хадгалж үлдээлээ)
    # =========================
    path("inventory/map/", location_map, name="station_map"),
    path("inventory/map/one/", station_map_view, name="station_map_one"),

    # =========================
    # 6) FORCE PASSWORD CHANGE
    # =========================
    path("accounts/force-password-change/", force_password_change, name="inventory_force_password_change"),

    # =========================
    # 7) DJANGO ADMIN (main)
    # =========================
    path("django-admin/", admin.site.urls),
]

# =========================
# Static / Media (DEBUG үед)
# =========================
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
