from django.urls import path
from . import views

# Системийн холбоосуудыг нэрлэх 'inventory' namespace
app_name = "inventory"

urlpatterns = [
    # 1. Улсын сүлжээний багаж хэрэгслийн график тайлан (Dashboard)
    path('dashboard/', views.national_dashboard, name='national_dashboard'),
    
    # 2. Инженерүүдийг олноор бүртгэж, и-мэйл илгээх (Bulk User Import)
    path('import-engineers/', views.import_engineers_from_csv, name='import_engineers_from_csv'),

    # 3. Багаж хэрэгслийг CSV-ээс импортлох (Bulk Device Import)
    path("device/import-csv/", views.device_import_csv, name="inventory_device_import_csv"),
    
    # 4. Тухайн аймгийн инженер зөвхөн өөрийн станцуудын Template-ийг татах
    path('download-template/', views.download_aimag_template, name='download_aimag_template'),

    # 5. Ашиглалтаас хасагдсан багажнуудын архивыг CSV-ээр татах
    path('download-retired-archive/', views.download_retired_archive, name='download_retired_archive'),

    # 6. Станцуудын байршил харуулах интерактив газрын зураг
    path("map/", views.location_map, name="location_map"),
]