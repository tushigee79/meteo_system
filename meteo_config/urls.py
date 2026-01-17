from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static # Энэ мөр дутуу байсан тул нэмэв

urlpatterns = [
    path('admin/', admin.site.urls), #
    path('', admin.site.urls),
]

# Хөгжүүлэлтийн үед статик болон медиа файлуудыг харуулах
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)