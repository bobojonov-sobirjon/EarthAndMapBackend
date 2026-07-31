from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('lands.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/monitoring/', include('monitoring.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Бухара GIS — Панель управления'
admin.site.site_title = 'Бухара GIS'
admin.site.index_title = 'Электронная реестр и геоинформационный мониторинг земель общего пользования'
