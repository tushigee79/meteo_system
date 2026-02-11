# inventory/admin_site.py
from django.contrib.admin import AdminSite
from django.urls import path

from . import views_admin          # reports_sums_by_aimag + dashboard_* энд байна (та баталсан)
from . import admin_dashboard as ad  # dashboard_graph_view + workflow_pending_counts энд байна
from . import reports_hub as rh      # workflow_pending_dashboard/counts/review_action/audit_log энд байна

class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ админ"
    site_title = "БҮРТГЭЛ"
    index_title = "Админ"

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            # --- AJAX helper ---
            path("reports/sums-by-aimag/", self.admin_view(views_admin.reports_sums_by_aimag),
                 name="reports-sums-by-aimag"),

            # --- Dashboards (views_admin.py) ---
            path("dashboard/", self.admin_view(views_admin.dashboard_home), name="dashboard_home"),
            path("dashboard/table/", self.admin_view(views_admin.dashboard_table), name="dashboard_table"),
            path("dashboard/graph/", self.admin_view(views_admin.dashboard_graph), name="dashboard_graph"),
            path("dashboard/general/", self.admin_view(views_admin.dashboard_general), name="dashboard_general"),
            path("data-entry/", self.admin_view(views_admin.admin_data_entry), name="admin_data_entry"),

            # --- Graph API / payload view (admin_dashboard.py) ---
            # (Хэрэв dashboard_graph_view-г ашиглахгүй бол энэ мөрийг авч болно)
            path("dashboard/graph-data/", self.admin_view(ad.dashboard_graph_view), name="dashboard_graph_view"),

            # --- Workflow (reports_hub.py) ---
            path("inventory/workflow/pending/", self.admin_view(rh.workflow_pending_dashboard),
                 name="workflow_pending"),
            path("inventory/workflow/review-action/", self.admin_view(rh.workflow_review_action),
                 name="workflow_review_action"),
            path("inventory/workflow/audit/", self.admin_view(rh.workflow_audit_log),
                 name="workflow_audit"),

            # --- Pending counts (admin_dashboard.py) ---
            path("inventory/workflow/pending-counts/", self.admin_view(ad.workflow_pending_counts),
                 name="workflow_pending_counts_live"),
        ]

        return my_urls + urls

inventory_admin_site = InventoryAdminSite(name="inventory_admin")
