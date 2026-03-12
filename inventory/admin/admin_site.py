from django.contrib.admin import AdminSite
from django.urls import path


class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ систем"
    site_title = "БҮРТГЭЛ"
    index_title = "Удирдлагын хэсэг"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_admin_links"] = [
            {"title": "Dashboard", "url_name": "inventory_admin:dashboard_home"},
            {"title": "Хуучин Dashboard", "url_name": "inventory_admin:dashboard_legacy"},
            {"title": "Pending Workflow", "url_name": "inventory_admin:workflow_pending_dashboard"},
            {"title": "Тайлан", "url_name": "inventory_admin:reports_hub"},
        ]
        return context

    def get_urls(self):
        urls = super().get_urls()

        from .admin_dashboard import (
            dashboard_home_view,
            dashboard_legacy_view,
            dashboard_table_view,
            dashboard_general_view,
            workflow_pending_dashboard,
            workflow_pending_counts_json,
            dashboard_summary_json,
            dashboard_map_json,
        )
        from .admin_reports import (
            reports_hub_view,
            reports_export_devices_csv,
            reports_export_locations_csv,
            reports_table_json,
        )

        custom_urls = [
            # MAIN INDEX = NEW DASHBOARD
            path("", self.admin_view(dashboard_home_view), name="index"),
            path("dashboard/", self.admin_view(dashboard_home_view), name="dashboard_home"),

            # LEGACY
            path("dashboard/legacy/", self.admin_view(dashboard_legacy_view), name="dashboard_legacy"),

            # OTHER DASHBOARDS
            path("dashboard/table/", self.admin_view(dashboard_table_view), name="dashboard_table"),
            path("dashboard/general/", self.admin_view(dashboard_general_view), name="dashboard_general"),
            path("dashboard/summary.json", self.admin_view(dashboard_summary_json), name="dashboard_summary_json"),
            path("dashboard/map.json", self.admin_view(dashboard_map_json), name="dashboard_map_json"),

            # WORKFLOW
            path("workflow/pending/", self.admin_view(workflow_pending_dashboard), name="workflow_pending_dashboard"),
            path(
                "inventory/workflow/pending-counts/",
                self.admin_view(workflow_pending_counts_json),
                name="workflow_pending_counts_json",
            ),

            # REPORTS
            path("reports/", self.admin_view(reports_hub_view), name="reports_hub"),
            path("reports/table.json", self.admin_view(reports_table_json), name="reports_table_json"),
            path(
                "reports/export/devices.csv",
                self.admin_view(reports_export_devices_csv),
                name="reports_export_devices_csv",
            ),
            path(
                "reports/export/locations.csv",
                self.admin_view(reports_export_locations_csv),
                name="reports_export_locations_csv",
            ),
        ]
        return custom_urls + urls


inventory_admin_site = InventoryAdminSite(name="inventory_admin")