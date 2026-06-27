from django.urls import path
from . import views

app_name = 'seguros'

urlpatterns = [
    path('', views.index, name='index'),
    path('poliza/', views.poliza, name='poliza'),
    path('siniestro/', views.siniestro, name='siniestro'),
    path('beneficiarios/', views.beneficiarios, name='beneficiarios'),
]
