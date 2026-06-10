from django.urls import path
from . import views

app_name = 'creditos'

urlpatterns = [
    path('',                      views.index,            name='index'),
    path('solicitar/',            views.solicitar_credito, name='solicitar'),
    path('pagar/<int:credito_id>/', views.pagar_cuota,    name='pagar_cuota'),
]
