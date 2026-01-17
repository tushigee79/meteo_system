from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # CSV импорт (admin template-тэй таарах нэр)
    path("device/import-csv/", views.device_import_csv, name="inventory_device_import_csv"),

    # 🗺 Газрын зураг
    path("map/", views.location_map, name="location_map"),
]
