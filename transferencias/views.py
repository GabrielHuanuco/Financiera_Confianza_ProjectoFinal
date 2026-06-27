from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core_bancario.decorators import role_required
from django.db import transaction
from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from core_bancario.models import Movimiento, Notificacion
from decimal import Decimal

@role_required(['CLIENTE'])
def index(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
    except Cliente.DoesNotExist:
        return redirect('dashboard:index')

    if request.method == 'POST':
        cuenta_origen_id = request.POST.get('cuenta_origen')
        cuenta_destino_numero = request.POST.get('cuenta_destino')
        monto_str = request.POST.get('monto')
        
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'

        try:
            monto = Decimal(monto_str)
            if monto <= Decimal('0'):
                raise ValueError("El monto debe ser mayor a 0.")

            with transaction.atomic():
                cuenta_origen = CuentaAhorro.objects.select_for_update().get(id=cuenta_origen_id, cliente=cliente, estado='ACTIVA')
                
                if cuenta_origen.saldo < monto:
                    raise ValueError("Saldo insuficiente.")

                # Descontar de cuenta origen
                cuenta_origen.saldo -= monto
                cuenta_origen.save()

                # Crear movimiento de salida
                Movimiento.objects.create(
                    cuenta=cuenta_origen,
                    tipo_operacion='TRANSFERENCIA_ENVIADA',
                    monto=monto,
                    saldo_resultante=cuenta_origen.saldo,
                    descripcion=f"Transferencia a {cuenta_destino_numero}"
                )

                # Verificar si la cuenta destino existe internamente
                cuenta_destino = CuentaAhorro.objects.filter(numero_cuenta=cuenta_destino_numero, estado='ACTIVA').first()
                if cuenta_destino:
                    cuenta_destino.saldo += monto
                    cuenta_destino.save()
                    
                    # Crear movimiento de entrada
                    Movimiento.objects.create(
                        cuenta=cuenta_destino,
                        tipo_operacion='TRANSFERENCIA_RECIBIDA',
                        monto=monto,
                        saldo_resultante=cuenta_destino.saldo,
                        descripcion=f"Transferencia recibida de {cuenta_origen.numero_cuenta}"
                    )
                    
                    # Notificar al receptor
                    Notificacion.objects.create(
                        cliente=cuenta_destino.cliente,
                        mensaje=f"Has recibido una transferencia de S/ {monto:.2f} de la cuenta {cuenta_origen.numero_cuenta}."
                    )

                # Notificar al remitente
                Notificacion.objects.create(
                    cliente=cliente,
                    mensaje=f"Transferencia exitosa de S/ {monto:.2f} a la cuenta {cuenta_destino_numero}."
                )

            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Transferencia realizada con éxito.'})
            messages.success(request, 'Transferencia realizada con éxito.')
            return redirect('transferencias:index')

        except CuentaAhorro.DoesNotExist:
            error_msg = "Cuenta de origen no válida o inactiva."
        except ValueError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Error al procesar la transferencia: {str(e)}"

        if is_ajax:
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
        messages.error(request, error_msg)

    # GET request
    cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')
    return render(request, 'transferencias/dashboard.html', {'cuentas': cuentas})
