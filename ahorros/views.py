from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from authentication.models import Cliente
from ahorros.models import CuentaAhorro

@login_required(login_url='/')
def index(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')
    except Cliente.DoesNotExist:
        cuentas = []

    return render(request, 'ahorros/dashboard.html', {'cuentas': cuentas})
