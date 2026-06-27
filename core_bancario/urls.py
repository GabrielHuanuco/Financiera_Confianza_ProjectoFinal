from django.urls import path
from django.shortcuts import redirect
from . import views
from . import views_recuperaciones

app_name = 'core_bancario'


def core_login_redirect(request):
    """Redirige al login de trabajadores (alias de conveniencia para /core/login/)."""
    return redirect('/auth/trabajadores/')


urlpatterns = [
    # ── Core Bancario Dashboard ──────────────────────────────────
    path('', views.core_dashboard, name='index'),
    path('login/', core_login_redirect, name='login'),

    # ── Recuperaciones y Mora ────────────────────────────────────
    path('recuperaciones/', views_recuperaciones.bandeja_mora, name='bandeja_mora'),
    path('recuperaciones/detalle/<int:credito_id>/', views_recuperaciones.detalle_mora, name='detalle_mora'),
    path('recuperaciones/gestion/<int:credito_id>/', views_recuperaciones.registrar_gestion, name='registrar_gestion'),
    path('recuperaciones/judicializar/<int:credito_id>/', views_recuperaciones.judicializar, name='judicializar'),
    path('recuperaciones/castigar/<int:credito_id>/', views_recuperaciones.castigar, name='castigar'),
]
