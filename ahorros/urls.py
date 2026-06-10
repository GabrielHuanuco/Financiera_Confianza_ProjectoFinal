from django.urls import path
from . import views

app_name = 'ahorros'

urlpatterns = [
    path('', views.index, name='index'),
]
