from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Энд 'namespace' нь 'inventory' байх нь 'admin' доторх URL дуудалтад чухал
    path('inventory/', include('inventory.urls', namespace='inventory')),
]