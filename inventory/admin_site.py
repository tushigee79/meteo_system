# inventory/admin_site.py
from __future__ import annotations

from django.contrib.admin import AdminSite
from django.http import HttpResponse, JsonResponse
from django.urls import path
from . import views_admin_workflow as wf
from . import reports_hub_compat as rhc





class InventoryAdminSite(AdminSite):
    site_header = "УС ЦАГ УУРЫН БҮРТГЭЛ"
    site_title = "БҮРТГЭЛ"
    index_title = "Удирдлагын хэсэг"
    name = "inventory_admin"

    def get_urls(self):
        from . import views_admin as va
        from . import reports_hub_compat as rhc
        from . import views as public_views

        urls = super().get_urls()

        def _missing(msg):
            return lambda r: HttpResponse(f"Error: {msg}", status=404)

        custom_urls = [
            # ✅ Charts endpoint
            path("dashboard/charts/", self.admin_view(va.dashboard_charts), name="dashboard_charts"),

            # Workflow (✅ зөв файл руу)
            path("inventory/workflow/pending/", self.admin_view(wf.workflow_pending_dashboard), name="workflow_pending"),
            path("inventory/workflow/audit-log/", self.admin_view(wf.workflow_audit_log), name="workflow_audit"),
            path("inventory/workflow/pending-counts/", self.admin_view(wf.workflow_pending_counts), name="workflow_pending_counts"),
            path("inventory/workflow/review/", self.admin_view(wf.workflow_review_action), name="workflow_review"),


            # Dashboards
            path("dashboard/table/", self.admin_view(va.dashboard_table), name="dashboard_table"),
            path("dashboard/graph/", self.admin_view(va.dashboard_graph), name="dashboard_graph"),
            path("dashboard/general/", self.admin_view(va.dashboard_general), name="dashboard_general"),
            path("data-entry/", self.admin_view(va.admin_data_entry), name="admin_data_entry"),
            path("dashboard/graph/data/", self.admin_view(va.dashboard_graph_data), name="dashboard_graph_data"),

            # Map
            path("inventory/map/", self.admin_view(public_views.location_map), name="inventory_map"),
        ]

        return custom_urls + urls


# ✅ энэ бол зөв: энд instance-ээ үүсгэнэ (өөрөөсөө импортлохгүй!)
inventory_admin_site = InventoryAdminSite(name="inventory_admin")
