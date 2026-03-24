from django.urls import path
from . import views
from .views_district_api import lookup_district_api
from .views_auth import force_password_change
from . import reports_hub_compat as rhc

urlpatterns = [
    path("api/geo/lookup-district/", lookup_district_api, name="lookup_district_api"),
    path("api/reports/sums/", rhc.reports_sums_by_aimag, name="reports-sums-json"),
    path("api/reports/charts/", rhc.reports_chart_json, name="reports-chart-json"),

    path("ajax/load-sums/", views.load_sums, name="ajax_load_sums"),
    path("ajax/location-options/", views.location_options, name="ajax_location_options"),
    path("ajax/location-by-sum/", views.location_by_sum, name="ajax_location_by_sum"),
    path("ajax/catalog-by-kind/", views.catalog_by_kind, name="ajax_catalog_by_kind"),

    path("admin/data-entry/", views.admin_data_entry, name="admin_data_entry"),

    path("inventory/map/", views.location_map, name="inventory_map"),
    path("inventory/map/<int:location_id>/", views.location_map, name="inventory_map_one"),

    path("qr/device/<uuid:token>/", views.qr_device_lookup, name="qr_device_lookup"),
    path("qr/public/<uuid:token>/", views.qr_device_public_view, name="qr_device_public"),
    path("qr/public/<uuid:token>/passport.pdf", views.qr_device_public_passport_pdf, name="qr_device_public_passport_pdf"),

    path("accounts/force-password-change/", force_password_change, name="inventory_force_password_change"),

    # Зассан хэсэг: Хаалт болон цэгийг зөв болгов
    path("ajax/location-options-compat/", views.location_options, name="inventory_device_device_location_options"),
    path("ajax/catalog-by-kind-compat/", views.catalog_by_kind, name="inventory_device_device_catalog_by_kind"),
]