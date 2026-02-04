# inventory/urls.py
from django.urls import path

from . import views
from . import reports_hub as rh

# Admin dashboard views
from .admin_dashboard import (
    dashboard_table_view,
    dashboard_graph_view,
    chart_status_json,
    chart_workflow_json,
)

# Other views
from .views import (
    location_map,
    station_map_view,
    admin_data_entry,
    qr_device_lookup,
    qr_device_public_view,
    qr_device_public_passport_pdf,
)

from .views_district_api import lookup_district_api
from .views_auth import force_password_change

app_name = "inventory"

urlpatterns = [
    # =====================================================
    # 1) API
    # =====================================================
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),
    path("api/reports/sums/", rh.reports_sums_json, name="reports-sums-json"),
    path("api/reports/charts/", rh.reports_chart_json, name="reports-chart-json"),

    # =====================================================
    # 2) REPORTS HUB & EXPORTS
    # =====================================================
    # CSV
    path("admin/reports/export/devices.csv/", rh.reports_export_devices_csv, name="reports-export-devices-csv"),
    path("admin/reports/export/maintenance.csv/", rh.reports_export_maintenance_csv, name="reports-export-maintenance-csv"),
    path("admin/reports/export/movements.csv/", rh.reports_export_movements_csv, name="reports-export-movements-csv"),
    path("admin/reports/export/locations.csv/", rh.reports_export_locations_csv, name="reports-export-locations-csv"),

    # XLSX
    path("admin/reports/export/devices.xlsx/", rh.reports_export_devices_xlsx, name="reports-export-devices-xlsx"),
    path("admin/reports/export/maintenance.xlsx/", rh.reports_export_maintenance_xlsx, name="reports-export-maintenance-xlsx"),
    path("admin/reports/export/movements.xlsx/", rh.reports_export_movements_xlsx, name="reports-export-movements-xlsx"),

    # =====================================================
    # 3) ADMIN DASHBOARD
    # =====================================================
    path("admin/dashboard/table/", dashboard_table_view, name="dashboard_table"),
    path("admin/dashboard/graph/", dashboard_graph_view, name="dashboard_graph"),
    path("admin/dashboard/charts/status.json", chart_status_json, name="chart_status_json"),
    path("admin/dashboard/charts/workflow.json", chart_workflow_json, name="chart_workflow_json"),

    # =====================================================
    # 4) ADMIN DATA ENTRY & MAP
    # =====================================================
    path("admin/data-entry/", admin_data_entry, name="admin_data_entry"),
    path("inventory/map/", location_map, name="inventory_map"),
    path("inventory/map/one/", station_map_view, name="station_map_one"),

    # =====================================================
    # 5) QR (public + device)
    # =====================================================
    path("qr/device/<uuid:token>/", qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/", qr_device_public_view, name="qr_device_public"),
    path(
        "qr/public/<uuid:token>/passport.pdf",
        qr_device_public_passport_pdf,
        name="qr_device_public_passport_pdf",
    ),

    # =====================================================
    # 6) AUTH
    # =====================================================
    path(
        "accounts/force-password-change/",
        force_password_change,
        name="inventory_force_password_change",
    ),
]
