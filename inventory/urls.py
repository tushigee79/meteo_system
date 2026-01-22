from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # API (dependent dropdown)
    path("api/sum-duureg/", views.api_sum_duureg, name="api_sum_duureg"),
    path("api/catalog/", views.api_catalog_items, name="api_catalog_items"),

    # Map
    path("map/", views.location_map, name="station_map"),
    path("map/one/", views.station_map_view, name="station_map_one"),

    # CSV импорт
    path("import-csv/", views.device_import_csv, name="device_import_csv"),
]
