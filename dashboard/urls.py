from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('agregar-tarjeta/', views.agregar_tarjeta, name='agregar_tarjeta'),
    # Asesor
    path('asesor/clientes/', views.asesor_clientes, name='asesor_clientes'),
    path('asesor/derivar/<int:credito_id>/', views.asesor_derivar, name='asesor_derivar'),
    path('asesor/desembolsar/<int:credito_id>/', views.asesor_desembolsar, name='asesor_desembolsar'),
    # Riesgos
    path('riesgos/evaluar/<int:credito_id>/', views.riesgos_evaluar, name='riesgos_evaluar'),
    # Comite
    path('comite/resolver/<int:credito_id>/', views.comite_resolver, name='comite_resolver'),
    # Gerencia
    path('gerencia/resolver/<int:credito_id>/', views.gerencia_resolver, name='gerencia_resolver'),
    # Admin
    path('admin/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin/cambiar-rol/<int:cliente_id>/', views.admin_cambiar_rol, name='admin_cambiar_rol'),
]