from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core_bancario.decorators import role_required

@role_required(['CLIENTE'])
def index(request):
    return render(request, 'seguros/dashboard.html')

@role_required(['CLIENTE'])
def poliza(request):
    return render(request, 'seguros/poliza.html')

@role_required(['CLIENTE'])
def siniestro(request):
    if request.method == 'POST':
        messages.success(request, 'Su reporte de siniestro ha sido enviado y será evaluado por nuestros asesores.')
        return redirect('seguros:siniestro')
    return render(request, 'seguros/siniestro.html')

@role_required(['CLIENTE'])
def beneficiarios(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        messages.success(request, f'El beneficiario {nombre} ha sido registrado correctamente.')
        return redirect('seguros:beneficiarios')
    return render(request, 'seguros/beneficiarios.html')
