from django.urls import path
from . import views

app_name = 'seguros'

urlpatterns = [
    path('', views.index, name='index'),
]
