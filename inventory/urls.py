# inventory/urls.py (clean) - 2026-01-31
from django.urls import path

from .admin_dashboard import (
    dashboard_table_view,
    dashboard_graph_view,
    export_devices_csv,
    export_devices_xlsx,
    export_maintenance_csv,
    export_movements_csv,
    chart_status_json,
    chart_workflow_json,
)
from .views import (
    # maps + admin hub
    location_map,
    station_map_view,
    admin_data_entry,

    # QR
    qr_device_lookup,
    qr_device_public_view,
    qr_device_public_passport_pdf,
)
from .views_district_api import lookup_district_api
from .views_auth import force_password_change
from . import views_admin_workflow as wf

app_name = "inventory"

urlpatterns = [
    # =========================
    # 1) API
    # =========================
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),

    # =========================
    # 2) DASHBOARDS / REPORTS (outside admin site)
    # =========================
    path("admin/dashboard/table/", dashboard_table_view, name="dashboard_table"),
    path("admin/dashboard/graph/", dashboard_graph_view, name="dashboard_graph"),

    # Exports
    path("admin/dashboard/export/devices.csv/", export_devices_csv, name="export_devices_csv"),
    path("admin/dashboard/export/devices.xlsx/", export_devices_xlsx, name="export_devices_xlsx"),
    path("admin/dashboard/export/maintenance.csv/", export_maintenance_csv, name="export_maintenance_csv"),
    path("admin/dashboard/export/movements.csv/", export_movements_csv, name="export_movements_csv"),

    # Chart JSON
    path("admin/dashboard/charts/status.json", chart_status_json, name="chart_status_json"),
    path("admin/dashboard/charts/workflow.json", chart_workflow_json, name="chart_workflow_json"),

    # =========================
    # 3) Admin data entry hub
    # =========================
    path("admin/data-entry/", admin_data_entry, name="admin_data_entry"),

    # =========================
    # 4) MAP
    # =========================
    path("inventory/map/", location_map, name="inventory_map"),
    path("inventory/map/one/", station_map_view, name="station_map_one"),

    # =========================
    # 5) QR
    # =========================
    path("qr/device/<uuid:token>/", qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/", qr_device_public_view, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", qr_device_public_passport_pdf, name="qr_device_public_passport_pdf"),
    path("qr/device/public/<uuid:token>/", qr_device_public_view, name="qr_device_public_legacy"),

    # =========================
    # 6) FORCE PASSWORD CHANGE
    # =========================
    path("accounts/force-password-change/", force_password_change, name="inventory_force_password_change"),

    # =========================
    # 7) WORKFLOW endpoints (called from admin UI)
    # ⚠️ NOTE: DO NOT prefix with "django-admin/" here.
    # If you need admin auth protection, register these under InventoryAdminSite.get_urls with self.admin_view.
    # =========================
    
]
