from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import PagoServicio
from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from decimal import Decimal
from core_bancario.models import Movimiento, Notificacion

@login_required(login_url='/')
def pagar_servicio(request):
    if request.method == 'POST':
        tipo_servicio = request.POST.get('tipo_servicio')
        codigo_pago = request.POST.get('codigo_pago')
        monto = request.POST.get('monto')
        cuenta_id = request.POST.get('cuenta_id')
        
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'
        
        try:
            monto_decimal = Decimal(monto)
            cliente = Cliente.objects.get(usuario=request.user)
            
            with transaction.atomic():
                if cuenta_id:
                    cuenta = CuentaAhorro.objects.select_for_update().get(id=cuenta_id, cliente=cliente)
                    if cuenta.saldo >= monto_decimal:
                        cuenta.saldo -= monto_decimal
                        cuenta.save()
                        
                        # Register movement
                        Movimiento.objects.create(
                            cuenta=cuenta,
                            tipo_operacion='PAGO_SERVICIO',
                            monto=monto_decimal,
                            saldo_resultante=cuenta.saldo,
                            descripcion=f"Pago de {tipo_servicio} - Código {codigo_pago}"
                        )
                        
                        # Register notification
                        Notificacion.objects.create(
                            cliente=cliente,
                            mensaje=f"Pago de servicio {tipo_servicio} por S/ {monto_decimal:.2f} realizado exitosamente."
                        )
                    else:
                        raise ValueError('Saldo insuficiente en la cuenta seleccionada.')

                PagoServicio.objects.create(
                    cliente=cliente,
                    tipo_servicio=tipo_servicio,
                    monto=monto_decimal,
                    codigo_pago=codigo_pago
                )
            
            if is_ajax:
                return JsonResponse({
                    'status': 'success', 
                    'message': f'El pago de {tipo_servicio} se ha realizado con éxito.',
                    'nuevo_saldo': str(cuenta.saldo) if cuenta_id else None,
                    'cuenta_id': cuenta_id
                })
                
            messages.success(request, f'El pago de {tipo_servicio} se ha realizado con éxito.')
            return redirect('dashboard:index')
            
        except Cliente.DoesNotExist:
            error_msg = 'Error: No se encontró el perfil de cliente asociado.'
        except CuentaAhorro.DoesNotExist:
            error_msg = 'Error: No se encontró la cuenta seleccionada.'
        except ValueError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f'Error al procesar el pago: {str(e)}'
            
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
        
        messages.error(request, error_msg)
            
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')
    except Cliente.DoesNotExist:
        cuentas = []
        
    return render(request, 'servicios/pagar_servicio.html', {'cuentas': cuentas})
