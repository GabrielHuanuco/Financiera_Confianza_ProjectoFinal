from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.conf import settings
from django.conf.urls.static import static
from authentication.models import Cliente


def home(request):
    """Página pública del Homebanking. Si el usuario ya está logueado, redirige al área correcta."""
    if request.user.is_authenticated:
        try:
            rol = request.user.cliente.rol
            if rol in ['ASESOR', 'RIESGOS', 'COMITE', 'GERENCIA', 'ADMIN']:
                return redirect('/core/')
            else:
                return redirect('/dashboard/')
        except Exception:
            pass
    return render(request, 'home.html')


urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación (clientes y trabajadores)
    path('auth/', include('authentication.urls')),

    # Página principal pública — Homebanking
    path('', home, name='home'),

    # Homebanking — módulos del cliente
    path('dashboard/', include('dashboard.urls')),
    path('creditos/', include('creditos.urls')),
    path('ahorros/', include('ahorros.urls')),
    path('seguros/', include('seguros.urls')),
    path('servicios/', include('servicios.urls')),
    path('transferencias/', include('transferencias.urls')),

    # Core Bancario — acceso exclusivo para trabajadores internos
    path('core/', include('core_bancario.urls')),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)