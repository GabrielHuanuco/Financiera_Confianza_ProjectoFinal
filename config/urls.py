from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

def home(request):
    return HttpResponse("Servidor Django funcionando correctamente 🚀")

urlpatterns = [
    path('admin/', admin.site.urls),

    # 👇 autenticación
    path('auth/', include('authentication.urls')),

    # 👇 página principal
    path('', home),
    
    # 👇 módulos
    path('dashboard/', include('dashboard.urls')),
    path('creditos/', include('creditos.urls')),
    path('ahorros/', include('ahorros.urls')),
    path('seguros/', include('seguros.urls')),
    path('servicios/', include('servicios.urls')),
    path('transferencias/', include('transferencias.urls')),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)