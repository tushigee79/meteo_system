# inventory/urls.py
from django.urls import path
from . import views
from . import reports_hub as rh
from .views_district_api import lookup_district_api
from .views_auth import force_password_change
from .admin_dashboard import (
    dashboard_table_view, dashboard_graph_view, chart_status_json, chart_workflow_json
)

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
    load_sums,  # <-- Бидний нэмсэн функц
)

urlpatterns = [
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),
    path("api/reports/sums/", rh.reports_sums_json, name="reports-sums-json"),
    path("api/reports/charts/", rh.reports_chart_json, name="reports-chart-json"),
    path("ajax/load-sums/", views.load_sums, name="ajax_load_sums"),

    path("admin/dashboard/table/", dashboard_table_view, name="dashboard_table"),
    path("admin/dashboard/graph/", dashboard_graph_view, name="dashboard_graph"),
    path("admin/dashboard/charts/status.json", chart_status_json, name="chart_status_json"),
    path("admin/dashboard/charts/workflow.json", chart_workflow_json, name="chart_workflow_json"),

    path("admin/data-entry/", views.admin_data_entry, name="admin_data_entry"),

    # ✅ map
    path("inventory/map/", views.location_map, name="inventory_map"),
    path("inventory/map/<int:location_id>/", views.location_map, name="inventory_map_one"),

    # ✅ QR
    path("qr/device/<uuid:token>/", views.qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/", views.qr_device_public_view, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", views.qr_device_public_passport_pdf, name="qr_device_public_passport_pdf"),

    path("accounts/force-password-change/", force_password_change, name="inventory_force_password_change"),
]
