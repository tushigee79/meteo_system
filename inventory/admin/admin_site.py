from django.contrib.admin import AdminSite
from django.http import HttpResponse
from django.urls import path

from inventory.models import Device, Location

from .admin_dashboard import (
    dashboard_general_view,
    dashboard_graph_view,
    dashboard_home_view,
    dashboard_legacy_view,
    dashboard_map_json,
    dashboard_summary_json,
    dashboard_table_view,
    workflow_pending_dashboard,
    workflow_pending_counts_json,
)
from .admin_devices import DeviceAdmin
from .admin_locations import LocationAdmin


def reports_hub_view(request):
    return HttpResponse("Reports Hub (coming soon)")


class InventoryAdminSite(AdminSite):
    site_header = "БҮРТГЭЛ систем"
    site_title = "БҮРТГЭЛ систем"
    index_title = "Удирдлагын самбар"

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            # Home / dashboard
            path("", self.admin_view(dashboard_home_view), name="index"),
            path("dashboard/", self.admin_view(dashboard_home_view), name="dashboard_home"),
            path("dashboard/legacy/", self.admin_view(dashboard_legacy_view), name="dashboard_legacy"),
            path("dashboard/general/", self.admin_view(dashboard_general_view), name="dashboard_general"),
            path("dashboard/table/", self.admin_view(dashboard_table_view), name="dashboard_table"),
            path("dashboard/graph/", self.admin_view(dashboard_graph_view), name="dashboard_graph"),

            # Dashboard JSON APIs
            path(
                "dashboard/api/summary/",
                self.admin_view(dashboard_summary_json),
                name="dashboard_summary_json",
            ),
            path(
                "dashboard/api/map/",
                self.admin_view(dashboard_map_json),
                name="dashboard_map_json",
            ),

            # Workflow
            path(
                "inventory/workflow/pending/",
                self.admin_view(workflow_pending_dashboard),
                name="workflow_pending_dashboard",
            ),
            path(
                "inventory/workflow/pending-counts/",
                self.admin_view(workflow_pending_counts_json),
                name="workflow_pending_counts_json",
            ),

            # Reports hub placeholder
            path(
                "reports/",
                self.admin_view(reports_hub_view),
                name="reports_hub",
            ),
        ]

        return custom_urls + urls


inventory_admin_site = InventoryAdminSite(name="inventory_admin")

# Register models only here
inventory_admin_site.register(Device, DeviceAdmin)
inventory_admin_site.register(Location, LocationAdmin)