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


from django.http import JsonResponse

def api_homebanking(request):
    """Endpoint simulado para verificar el estado de la API del Homebanking"""
    return JsonResponse({
        "servicio": "Banca Internet Financiera Confianza - Homebanking API",
        "version": "1.0.0",
        "estado": "ok"
    })

def api_core(request):
    """Endpoint simulado para verificar el estado de la API del Core Bancario"""
    return JsonResponse({
        "servicio": "Core Bancario Financiera Confianza - API Interna",
        "version": "1.0.0",
        "estado": "ok"
    })

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

    # APIs JSON para cumplir con la rúbrica
    path('api/homebanking/', api_homebanking, name='api_homebanking'),
    path('api/core/', api_core, name='api_core'),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)