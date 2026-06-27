from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('',       views.login_view,  name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',views.logout_view, name='logout'),
    path('trabajadores/', views.login_trabajador_view, name='login_trabajador'),
]
