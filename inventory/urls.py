# inventory/urls.py
from django.urls import path
from . import views
from .views_district_api import lookup_district_api
from .views_auth import force_password_change
from .views_qr import qr_public, qr_passport_pdf
from .admin_dashboard import dashboard_table_view, dashboard_graph_view, chart_status_json, chart_workflow_json
from . import reports_hub_compat as rhc

urlpatterns = [
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),
    path("api/reports/sums/", rhc.reports_sums_by_aimag, name="reports-sums-json"),
    path("api/reports/charts/", rhc.reports_chart_json, name="reports-chart-json"),
    path("ajax/load-sums/", views.load_sums, name="ajax_load_sums"),
    path("ajax/location-options/", views.location_options, name="ajax_location_options"),
    path("ajax/location-by-sum/", views.location_by_sum, name="ajax_location_by_sum"),

    path("admin/dashboard/table/", dashboard_table_view, name="dashboard_table"),
    path("admin/dashboard/graph/", dashboard_graph_view, name="dashboard_graph"),
    path("admin/dashboard/charts/status.json", chart_status_json, name="chart_status_json"),
    path("admin/dashboard/charts/workflow.json", chart_workflow_json, name="chart_workflow_json"),
    path("admin/data-entry/", views.admin_data_entry, name="admin_data_entry"),

    path("inventory/map/", views.location_map, name="inventory_map"),
    path("inventory/map/<int:location_id>/", views.location_map, name="inventory_map_one"),

    path("qr/device/<uuid:token>/", views.qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/", qr_public, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", qr_passport_pdf, name="qr_device_public_passport_pdf"),

    path("accounts/force-password-change/", force_password_change, name="inventory_force_password_change"),
]
