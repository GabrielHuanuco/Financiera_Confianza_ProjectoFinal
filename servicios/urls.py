from django.urls import path
from . import views

app_name = 'servicios'

urlpatterns = [
    path('pagar/', views.pagar_servicio, name='pagar'),
]
