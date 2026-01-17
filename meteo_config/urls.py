from django.contrib import admin
from django.urls import path, include # 'include' нэмэв
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # inventory апп-ын замуудыг холбох
    path('inventory/', include('inventory.urls')), 
    path('', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)