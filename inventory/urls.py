from django.urls import path
from . import views

# app_name заавал байх ёстой бөгөөд include дотор дахин urls-ээ дуудаж болохгүй
app_name = "inventory"

urlpatterns = [
    # 1. Админ панелын CSV импорт товчтой холбогдох URL
    path("device/import-csv/", views.device_import_csv, name="inventory_device_import_csv"),
    
    # 2. Газрын зураг
    path("map/", views.location_map, name="location_map"),
]