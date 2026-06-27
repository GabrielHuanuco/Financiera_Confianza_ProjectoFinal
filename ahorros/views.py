from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from decimal import Decimal
from core_bancario.decorators import role_required
from django.shortcuts import render

@role_required(['CLIENTE'])
def index(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')
    except Cliente.DoesNotExist:
        cuentas = []

    return render(request, 'ahorros/dashboard.html', {'cuentas': cuentas})

@role_required(['CLIENTE'])
def transferir(request):
    if request.method == 'POST':
        cuenta_id = request.POST.get('cuenta_id')
        monto = request.POST.get('monto')
        
        try:
            monto_decimal = Decimal(monto)
            if monto_decimal <= 0:
                messages.error(request, 'El monto debe ser mayor a cero.')
                return redirect('ahorros:index')
                
            cliente = Cliente.objects.get(usuario=request.user)
            
            if cuenta_id and cuenta_id != "0":
                cuenta = CuentaAhorro.objects.get(id=cuenta_id, cliente=cliente)
                cuenta.saldo += monto_decimal
                cuenta.save()
                messages.success(request, f'Transferencia exitosa: S/ {monto_decimal} a tu cuenta {cuenta.tipo_cuenta}.')
            else:
                # If static fallback was used, just show a fake success message
                messages.success(request, f'Transferencia simulada exitosa: S/ {monto_decimal} a tu Cuenta Sueldo.')
                
        except (ValueError, TypeError):
            messages.error(request, 'Monto inválido.')
        except Cliente.DoesNotExist:
            messages.error(request, 'Cliente no encontrado.')
        except CuentaAhorro.DoesNotExist:
            messages.error(request, 'Cuenta no encontrada o no pertenece al usuario.')
            
    return redirect('ahorros:index')

@role_required(['ASESOR', 'ADMIN'])
def registrar_cliente(request):
    # Lógica para registrar cliente
    if request.method == 'POST':
        # Procesar formulario y guardar cliente
        pass
    return render(request, 'ahorros/registrar_cliente.html')


@role_required(['CLIENTE'])
def retirar(request):
    """Permite al cliente retirar dinero de una de sus cuentas de ahorro."""
    if request.method == 'POST':
        cuenta_id = request.POST.get('cuenta_id')
        monto = request.POST.get('monto')

        try:
            monto_decimal = Decimal(monto)
            if monto_decimal <= 0:
                messages.error(request, 'El monto debe ser mayor a cero.')
                return redirect('ahorros:index')

            cliente = Cliente.objects.get(usuario=request.user)
            cuenta = CuentaAhorro.objects.get(id=cuenta_id, cliente=cliente, estado='ACTIVA')

            if cuenta.saldo < monto_decimal:
                messages.error(request, f'Saldo insuficiente. Tu saldo es S/ {cuenta.saldo:,.2f}.')
                return redirect('ahorros:index')

            from django.db import transaction
            from core_bancario.models import Movimiento, Notificacion

            with transaction.atomic():
                cuenta.saldo -= monto_decimal
                cuenta.save()

                Movimiento.objects.create(
                    cuenta=cuenta,
                    tipo_operacion='RETIRO',
                    monto=monto_decimal,
                    saldo_resultante=cuenta.saldo,
                    descripcion=f"Retiro de efectivo — Cuenta {cuenta.numero_cuenta}",
                )

                Notificacion.objects.create(
                    cliente=cliente,
                    mensaje=f"💰 Has retirado S/ {monto_decimal:,.2f} de tu cuenta {cuenta.numero_cuenta}. Saldo restante: S/ {cuenta.saldo:,.2f}.",
                )

            messages.success(request, f'Retiro exitoso: S/ {monto_decimal:,.2f} de tu cuenta {cuenta.tipo_cuenta}. Saldo restante: S/ {cuenta.saldo:,.2f}.')

        except (ValueError, TypeError):
            messages.error(request, 'Monto inválido.')
        except Cliente.DoesNotExist:
            messages.error(request, 'Cliente no encontrado.')
        except CuentaAhorro.DoesNotExist:
            messages.error(request, 'Cuenta no encontrada o no pertenece al usuario.')

    return redirect('ahorros:index')
