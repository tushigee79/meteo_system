from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Админ панел
    path('admin/', admin.site.urls),
    
    # 2. Inventory апп-ыг namespace-тэй холбох
    # Энэ нь 'inventory:location_map' гэх мэтээр дуудахад заавал хэрэгтэй
    path('inventory/', include('inventory.urls', namespace='inventory')), 
]

# Статик болон медиа файлуудын тохиргоо
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)