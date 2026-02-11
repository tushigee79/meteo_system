from __future__ import annotations

from django.urls import path
from . import views
from . import reports_hub
from . import reports_hub_compat as rhc
from .views_district_api import lookup_district_api
from .views_auth import force_password_change
from .views_qr import qr_public, qr_passport_pdf

app_name = "inventory"

urlpatterns = [
    # --- Dashboards & Workflow (Centralized Logic) ---
    # These all currently point to the same view; consider if they should be consolidated 
    # or if they are placeholders for future distinct logic.
    path("workflow/pending/", reports_hub.workflow_pending_dashboard, name="reports_hub"),
    path("workflow/pending-v2/", reports_hub.workflow_pending_dashboard, name="workflow_pending"),
    path("workflow/audit/", reports_hub.workflow_pending_dashboard, name="workflow_audit"),
    path("dashboard/home/", reports_hub.workflow_pending_dashboard, name="dashboard_home"),
    path("dashboard/general/", reports_hub.workflow_pending_dashboard, name="dashboard_general"),
    path("dashboard/table/", reports_hub.workflow_pending_dashboard, name="dashboard_table"),
    path("dashboard/graph/", reports_hub.workflow_pending_dashboard, name="dashboard_graph"),
    path("admin/data-entry/", reports_hub.workflow_pending_dashboard, name="admin_data_entry"),

    # --- API & AJAX Helpers ---
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),
    path("api/reports/sums/", rhc.reports_sums_by_aimag, name="reports-sums-json"),
    path("api/reports/charts/", rhc.reports_chart_json, name="reports-chart-json"),
    path("ajax/load-sums/", views.load_sums, name="ajax_load_sums"),
    
    # --- Map Views ---
    path("map/", views.location_map, name="inventory_map"),
    
    # --- QR & Public Access ---
    path("qr/device/<uuid:token>/", views.qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/passport.pdf", qr_passport_pdf, name="qr_device_public_passport_pdf"),

    # --- Authentication ---
    path("auth/force-password-change/", force_password_change, name="force_password_change"),
]