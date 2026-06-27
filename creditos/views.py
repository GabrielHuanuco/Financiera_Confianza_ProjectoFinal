from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core_bancario.decorators import role_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ahorros.models import CuentaAhorro
from authentication.models import Cliente
from core_bancario.models import Movimiento, Notificacion

from .models import Credito, PagoCuota


# ──────────────────────────────────────────
# Reglas de negocio para aprobación
# ──────────────────────────────────────────
LIMITES_MONTO = {
    'Personal':    Decimal('30000'),
    'Vehicular':   Decimal('80000'),
    'Hipotecario': Decimal('300000'),
    'Negocio':     Decimal('50000'),
    'Microempresa': Decimal('100000'),
}

SCORE_MINIMO = 400          # score_crediticio mínimo
RATIO_CUOTA_INGRESO = Decimal('0.35')  # cuota ≤ 35% de ingresos mensuales


def _evaluar_solicitud(cliente, tipo_credito, monto, cuota_mensual):
    """
    Devuelve (aprobado: bool, motivo: str).
    Reglas:
      1. Score crediticio ≥ 400
      2. Monto ≤ límite del tipo
      3. Cuota mensual ≤ 35% de ingresos
      4. No tener otro crédito DESEMBOLSADO del mismo tipo
    """
    if cliente.score_crediticio < SCORE_MINIMO:
        return False, f"Score crediticio insuficiente ({cliente.score_crediticio}/400 mínimo)."

    limite = LIMITES_MONTO.get(tipo_credito, Decimal('30000'))
    if monto > limite:
        return False, f"El monto solicitado supera el límite permitido de S/ {limite:,.2f} para {tipo_credito}."

    if cliente.ingresos > 0:
        ratio = cuota_mensual / cliente.ingresos
        if ratio > RATIO_CUOTA_INGRESO:
            return False, (
                f"La cuota mensual (S/ {cuota_mensual:,.2f}) supera el 35% de tus ingresos "
                f"(S/ {cliente.ingresos:,.2f}). Reduce el monto o amplía el plazo."
            )

    ya_tiene = Credito.objects.filter(
        cliente=cliente,
        tipo_credito=tipo_credito,
        estado='DESEMBOLSADO'
    ).exists()
    if ya_tiene:
        return False, f"Ya tienes un crédito {tipo_credito} activo. Completa su pago antes de solicitar uno nuevo."

    return True, "Solicitud aprobada."


# ──────────────────────────────────────────
# Vistas
# ──────────────────────────────────────────

@role_required(['CLIENTE'])
def index(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
    except Cliente.DoesNotExist:
        return render(request, 'creditos/dashboard.html', {'creditos': [], 'historial': []})

    creditos_activos = Credito.objects.filter(
        cliente=cliente,
        estado='DESEMBOLSADO'
    ).order_by('-fecha_solicitud')

    historial = PagoCuota.objects.filter(
        credito__cliente=cliente
    ).select_related('credito').order_by('-fecha')[:10]

    context = {
        'creditos': creditos_activos,
        'historial': historial,
        'cliente': cliente,
    }
    return render(request, 'creditos/dashboard.html', context)


@role_required(['CLIENTE'])
def solicitar_credito(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
    except Cliente.DoesNotExist:
        messages.error(request, 'No se encontró el perfil de cliente.')
        return redirect('dashboard:index')

    cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')

    if request.method != 'POST':
        return render(request, 'creditos/solicitar_credito.html', {
            'cuentas': cuentas,
            'cliente': cliente,
        })

    tipo_credito = request.POST.get('tipo_credito', '').strip()
    monto_str    = request.POST.get('monto', '0')
    cuotas_str   = request.POST.get('cuotas', '12')
    cuenta_destino_id = request.POST.get('cuenta_destino_id', '')
    ingreso_mensual_str = request.POST.get('ingreso_mensual', '0')
    is_ajax      = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
    )

    try:
        monto  = Decimal(monto_str)
        cuotas = int(cuotas_str)
        ingreso = Decimal(ingreso_mensual_str)

        if monto <= 0 or cuotas <= 0 or ingreso <= 0:
            raise ValueError("El monto, cuotas e ingresos deben ser mayores a cero.")

        # Actualizar ingresos declarados del cliente
        cliente.ingresos = ingreso
        cliente.save()

        tasa    = Credito.TASAS.get(tipo_credito, Decimal('0.18'))

        # Calcular cuota (sistema francés con TEA)
        tea = float(tasa)
        if tea == 0:
            cuota_mensual = monto / cuotas
        else:
            tasa_mensual = (1 + tea) ** (1/12) - 1
            factor = (1 + tasa_mensual) ** cuotas
            cuota_float = float(monto) * (tasa_mensual * factor) / (factor - 1)
            cuota_mensual = Decimal(str(round(cuota_float, 2)))

        # Evaluar la solicitud
        aprobado, motivo = _evaluar_solicitud(cliente, tipo_credito, monto, cuota_mensual)

        if not aprobado:
            # Crear registro de crédito rechazado
            Credito.objects.create(
                cliente=cliente,
                tipo_credito=tipo_credito,
                monto=monto,
                cuotas=cuotas,
                tasa_interes=tasa,
                cuota_mensual=round(cuota_mensual, 2),
                saldo_pendiente=Decimal('0.00'),
                estado='RECHAZADO',
            )
            Notificacion.objects.create(
                cliente=cliente,
                mensaje=f"❌ Tu solicitud de crédito ha sido rechazada: {motivo}",
            )
            msg = f"Solicitud procesada. {motivo}"
            tipo_msg = 'error'
        else:
            with transaction.atomic():
                # Preparar observación con la cuenta destino
                obs = f"Ingreso mensual declarado: S/ {ingreso:,.2f}.\n"
                if cuenta_destino_id:
                    obs += f"Cuenta Destino Solicitada ID: {cuenta_destino_id}"
                else:
                    obs += "Cuenta Destino: AUTO_CREAR"

                # Crear crédito para EVALUACIÓN
                credito = Credito.objects.create(
                    cliente=cliente,
                    tipo_credito=tipo_credito,
                    monto=monto,
                    cuotas=cuotas,
                    tasa_interes=tasa,
                    cuota_mensual=round(cuota_mensual, 2),
                    saldo_pendiente=round(cuota_mensual * cuotas, 2),
                    estado='EN_EVALUACION',
                    observaciones=obs
                )

                Notificacion.objects.create(
                    cliente=cliente,
                    mensaje=(
                        f"📝 Tu solicitud de crédito {tipo_credito} por S/ {monto:,.2f} ha sido ingresada "
                        f"y está siendo evaluada por un asesor."
                    ),
                )
            msg = "Solicitud ingresada correctamente. Está en evaluación."
            tipo_msg = 'success'

        if is_ajax:
            return JsonResponse({'status': tipo_msg, 'message': msg})
        if aprobado:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('creditos:index')

    except (ValueError, Exception) as e:
        error = f'Error en los datos: {str(e)}'

    if is_ajax:
        return JsonResponse({'status': 'error', 'message': error}, status=400)
    messages.error(request, error)
    return render(request, 'creditos/solicitar_credito.html', {
        'cuentas': cuentas,
        'cliente': cliente,
    })


@role_required(['CLIENTE'])
def pagar_cuota(request, credito_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

    try:
        cliente = Cliente.objects.get(usuario=request.user)
        credito = get_object_or_404(Credito, id=credito_id, cliente=cliente, estado='DESEMBOLSADO')

        cuenta = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA').first()
        if not cuenta:
            return JsonResponse({'status': 'error', 'message': 'No tienes una cuenta activa para realizar el pago.'}, status=400)

        if cuenta.saldo < credito.cuota_mensual:
            return JsonResponse({
                'status': 'error',
                'message': f'Saldo insuficiente. Tu saldo es S/ {cuenta.saldo:,.2f} y la cuota es S/ {credito.cuota_mensual:,.2f}.'
            }, status=400)

        if credito.cuotas_pagadas >= credito.cuotas:
            return JsonResponse({'status': 'error', 'message': 'Este crédito ya está completamente pagado.'}, status=400)

        with transaction.atomic():
            # Descontar de la cuenta
            cuenta.saldo -= credito.cuota_mensual
            cuenta.save()

            # Actualizar crédito
            credito.saldo_pendiente -= credito.cuota_mensual
            credito.cuotas_pagadas  += 1

            numero_cuota = credito.cuotas_pagadas

            # Si era la última cuota, marcar como PAGADO
            if credito.cuotas_pagadas >= credito.cuotas:
                credito.saldo_pendiente = Decimal('0')
                credito.estado = 'PAGADO'

            credito.save()

            # Registrar pago en historial
            PagoCuota.objects.create(
                credito=credito,
                numero_cuota=numero_cuota,
                monto_pagado=credito.cuota_mensual,
                saldo_tras_pago=credito.saldo_pendiente,
            )

            # Movimiento bancario
            Movimiento.objects.create(
                cuenta=cuenta,
                tipo_operacion='RETIRO',
                monto=credito.cuota_mensual,
                saldo_resultante=cuenta.saldo,
                descripcion=f"Pago cuota #{numero_cuota}/{credito.cuotas} — {credito.tipo_credito}",
            )

            # Notificación
            if credito.estado == 'PAGADO':
                mensaje_noti = f"🎉 ¡Felicitaciones! Tu crédito {credito.tipo_credito} ha sido pagado completamente."
            else:
                restantes = credito.cuotas - credito.cuotas_pagadas
                mensaje_noti = (
                    f"✅ Pagaste la cuota #{numero_cuota} de tu crédito {credito.tipo_credito}. "
                    f"Saldo pendiente: S/ {credito.saldo_pendiente:,.2f}. Quedan {restantes} cuota(s)."
                )
            Notificacion.objects.create(cliente=cliente, mensaje=mensaje_noti)

        if credito.estado == 'PAGADO':
            return JsonResponse({
                'status': 'success',
                'message': f'¡Crédito {credito.tipo_credito} pagado completamente! 🎉',
                'credito_pagado': True,
                'nuevo_saldo': str(cuenta.saldo),
            })

        return JsonResponse({
            'status': 'success',
            'message': f'Cuota #{numero_cuota} pagada. Saldo pendiente: S/ {credito.saldo_pendiente:,.2f}.',
            'credito_pagado': False,
            'nuevo_saldo_credito': str(credito.saldo_pendiente),
            'cuotas_pagadas': credito.cuotas_pagadas,
            'progreso': credito.progreso_pago(),
            'nuevo_saldo': str(cuenta.saldo),
        })

    except Cliente.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Perfil de cliente no encontrado.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error al procesar el pago: {str(e)}'}, status=500)


@role_required(['CLIENTE'])
def ver_cronograma(request, credito_id):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        credito = get_object_or_404(Credito, id=credito_id, cliente=cliente)
        
        cronograma = credito.generar_cronograma()
        
        # Convertir a JSON serializable
        cronograma_json = []
        for cuota in cronograma:
            cronograma_json.append({
                'numero': cuota['numero'],
                'fecha_vencimiento': cuota['fecha_vencimiento'].strftime('%d/%m/%Y') if cuota.get('fecha_vencimiento') else 'N/A',
                'saldo_inicial': str(cuota['saldo_inicial']),
                'capital': str(cuota['capital']),
                'interes': str(cuota['interes']),
                'cuota': str(cuota['cuota']),
                'saldo_final': str(cuota['saldo_final']),
                'estado': cuota['estado']
            })
            
        return JsonResponse({'status': 'success', 'cronograma': cronograma_json})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
