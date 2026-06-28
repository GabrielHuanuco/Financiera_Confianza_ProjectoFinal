from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Case, When, Value, CharField
from django.db.models.functions import TruncMonth
from django.db import transaction
from decimal import Decimal
import json

from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from core_bancario.models import Movimiento, Notificacion
from core_bancario.decorators import role_required
from core_bancario.recuperaciones import get_kpis_mora
from creditos.models import Credito, HistorialAprobacion
from seguros.models import Seguro


def _registrar_historial(credito, usuario, rol, observacion, estado_anterior, estado_nuevo):
    HistorialAprobacion.objects.create(
        credito=credito,
        usuario=usuario,
        rol=rol,
        observacion=observacion,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo
    )


def _obtener_contexto_admin(request, usuarios_list):
    total_usuarios = User.objects.count()
    total_movimientos = Movimiento.objects.count()
    volumen_movimientos = Movimiento.objects.aggregate(t=Sum('monto'))['t'] or 0

    # Gráfico: Operaciones por módulo
    ops_modulo = list(Movimiento.objects.values('tipo_operacion').annotate(c=Count('id')))
    chart_ops = {x['tipo_operacion']: x['c'] for x in ops_modulo}

    # Gráfico: Actividad mensual (Volumen S/)
    actividad = list(Movimiento.objects.annotate(month=TruncMonth('fecha')).values('month').annotate(total=Sum('monto')).order_by('month'))
    chart_actividad = [{'month': x['month'].strftime('%Y-%m') if x['month'] else 'N/A', 'total': float(x['total'])} for x in actividad]

    # Gráfico: Recuentos generales
    chart_general = {
        'Créditos': Credito.objects.count(),
        'Cuentas': CuentaAhorro.objects.count(),
        'Seguros': Seguro.objects.count(),
    }
    
    total_creditos = Credito.objects.count()
    total_clientes = Cliente.objects.filter(rol='CLIENTE').count()
    total_cuentas = CuentaAhorro.objects.count()
    roles_count = {item['rol']: item['count'] for item in Cliente.objects.values('rol').annotate(count=Count('id'))}
    
    unread_notifications = 0
    try:
        unread_notifications = Notificacion.objects.filter(cliente=request.user.cliente, leida=False).count()
    except Exception:
        pass

    return {
        'rol': 'ADMIN',
        'user_name': request.user.get_full_name() or request.user.username,
        'first_name': request.user.first_name or request.user.username,
        'unread_notifications': unread_notifications,
        'currency': 'S/',
        'total_usuarios': total_usuarios,
        'total_movimientos': total_movimientos,
        'volumen_movimientos': f"{volumen_movimientos:,.2f}",
        'chart_ops': json.dumps(chart_ops),
        'chart_actividad': json.dumps(chart_actividad),
        'chart_general': json.dumps(chart_general),
        'usuarios_list': usuarios_list,
        'total_creditos': total_creditos,
        'total_clientes': total_clientes,
        'total_cuentas': total_cuentas,
        'roles_count': roles_count,
        'roles_choices': Cliente.ROLES_CHOICES,
    }



# ──────────────────────────────────────────────────────────────
#  DASHBOARD PRINCIPAL — Despacha contexto según el rol
# ──────────────────────────────────────────────────────────────

@login_required(login_url='/auth/')
def dashboard(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        rol = cliente.rol
    except Cliente.DoesNotExist:
        cliente = None
        rol = 'CLIENTE'

    # Si es un trabajador interno que llegó a /dashboard/ (o homebanking) manualmente,
    # redirigirlo automáticamente al Core Bancario (solo si no está ya en /core/).
    ROLES_TRABAJADOR = ['ASESOR', 'RIESGOS', 'COMITE', 'GERENCIA', 'ADMIN']
    if rol in ROLES_TRABAJADOR and not request.path.startswith('/core'):
        return redirect('/core/')

    # Notificaciones no leídas
    unread_notifications = 0
    if cliente:
        unread_notifications = Notificacion.objects.filter(cliente=cliente, leida=False).count()

    context = {
        'user_name': request.user.get_full_name() or request.user.username,
        'first_name': request.user.first_name or request.user.username,
        'unread_notifications': unread_notifications,
        'rol': rol,
        'currency': 'S/',
    }

    # ── CLIENTE ──────────────────────────────────────────────
    if rol == 'CLIENTE':
        cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA') if cliente else CuentaAhorro.objects.none()
        total_balance = cuentas.aggregate(total=Sum('saldo'))['total'] or 0

        cuentas_ids = cuentas.values_list('id', flat=True)
        recent_transactions_qs = Movimiento.objects.filter(cuenta_id__in=cuentas_ids).order_by('-fecha')[:5]
        recent_transactions = []
        for tx in recent_transactions_qs:
            if tx.tipo_operacion in ['DEPOSITO', 'TRANSFERENCIA_RECIBIDA']:
                tx_type = 'income'
                amount_str = f"+ {tx.monto:,.2f}"
            else:
                tx_type = 'expense'
                amount_str = f"- {tx.monto:,.2f}"
            recent_transactions.append({
                'date': tx.fecha.strftime('%d %b %Y'),
                'description': tx.descripcion,
                'amount': amount_str,
                'type': tx_type,
            })

        creditos_activos = Credito.objects.filter(cliente=cliente, estado='DESEMBOLSADO') if cliente else []
        creditos_pagados = Credito.objects.filter(cliente=cliente, estado='PAGADO') if cliente else []
        seguros = Seguro.objects.filter(cliente=cliente, estado=True) if cliente else []

        # Calcular deuda total de créditos activos
        deuda_total = Credito.objects.filter(
            cliente=cliente, estado='DESEMBOLSADO'
        ).aggregate(total=Sum('saldo_pendiente'))['total'] or 0

        context.update({
            'account_number': cuentas.first().numero_cuenta if cuentas.exists() else 'Sin cuenta',
            'total_balance': f"{total_balance:,.2f}",
            'cuentas': cuentas,
            'recent_transactions': recent_transactions,
            'creditos_activos': creditos_activos,
            'creditos_pagados': creditos_pagados,
            'seguros': seguros,
            'deuda_total': f"{deuda_total:,.2f}",
            'ingreso_diario': cliente.ingreso_diario if cliente else 0,
            'quick_actions': [
                {'icon': 'bi-send', 'label': 'Transferir', 'url': 'transferencias:index'},
                {'icon': 'bi-receipt', 'label': 'Pagar Servicios', 'url': 'servicios:pagar'},
                {'icon': 'bi-cash', 'label': 'Pedir Préstamo', 'url': 'creditos:solicitar'},
                {'icon': 'bi-shield-check', 'label': 'Seguros', 'url': 'seguros:index'},
            ],
        })

    # ── ASESOR ───────────────────────────────────────────────
    elif rol == 'ASESOR':
        total_clientes = Cliente.objects.filter(rol='CLIENTE', estado=True).count()
        solicitudes_pendientes = Credito.objects.filter(
            estado='EN_EVALUACION'
        ).select_related('cliente__usuario').order_by('-fecha_solicitud')
        creditos_en_riesgos = Credito.objects.filter(estado='EN_RIESGOS').count()
        solicitudes_recientes = Credito.objects.select_related(
            'cliente__usuario'
        ).order_by('-fecha_solicitud')[:10]
        
        # Aprobados listos para desembolso
        creditos_aprobados = Credito.objects.filter(
            estado='APROBADO'
        ).select_related('cliente__usuario').order_by('-fecha_solicitud')

        context.update({
            'total_clientes': total_clientes,
            'solicitudes_pendientes': solicitudes_pendientes,
            'solicitudes_pendientes_count': solicitudes_pendientes.count(),
            'creditos_en_riesgos': creditos_en_riesgos,
            'solicitudes_recientes': solicitudes_recientes,
            'creditos_aprobados': creditos_aprobados,
        })

    # ── RIESGOS ──────────────────────────────────────────────
    elif rol == 'RIESGOS':
        search_query = request.GET.get('q', '').strip()
        solicitudes_riesgos_qs = Credito.objects.filter(estado='EN_RIESGOS').select_related('cliente__usuario')
        
        if search_query:
            for term in search_query.split():
                solicitudes_riesgos_qs = solicitudes_riesgos_qs.filter(
                    Q(cliente__usuario__first_name__icontains=term) |
                    Q(cliente__usuario__last_name__icontains=term) |
                    Q(cliente__dni__icontains=term)
                )
        solicitudes_riesgos = solicitudes_riesgos_qs.order_by('-fecha_solicitud')

        # Gráfico: Semáforo crediticio
        semaforo_counts = Cliente.objects.filter(rol='CLIENTE').annotate(
            color=Case(
                When(score_crediticio__gte=700, then=Value('VERDE')),
                When(score_crediticio__gte=500, then=Value('AMARILLO')),
                default=Value('ROJO'),
                output_field=CharField(),
            )
        ).values('color').annotate(c=Count('id'))
        chart_semaforo = {x['color']: x['c'] for x in semaforo_counts}

        # Gráfico: Solicitudes por estado
        chart_estados = list(Credito.objects.values('estado').annotate(c=Count('id')))

        # Gráfico: Mora por bandas (reutilizando get_kpis_mora)
        kpis_mora = get_kpis_mora()
        chart_mora = kpis_mora['conteo_bandas']

        # Gráfico: Distribución RDS (Barras)
        rds_bins = {'<30% (Saludable)': 0, '30-50% (Riesgo Medio)': 0, '>50% (Riesgo Alto)': 0}
        for c in Credito.objects.select_related('cliente').all():
            rds = c.valor_rds
            if rds < 30: rds_bins['<30% (Saludable)'] += 1
            elif rds <= 50: rds_bins['30-50% (Riesgo Medio)'] += 1
            else: rds_bins['>50% (Riesgo Alto)'] += 1

        context.update({
            'solicitudes_riesgos': solicitudes_riesgos,
            'pendientes_count': solicitudes_riesgos.count(),
            'chart_semaforo': json.dumps(chart_semaforo),
            'chart_estados': json.dumps(chart_estados),
            'chart_mora': json.dumps(chart_mora),
            'chart_rds': json.dumps(rds_bins),
        })

    # ── COMITE ───────────────────────────────────────────────
    elif rol == 'COMITE':
        search_query = request.GET.get('q', '').strip()
        creditos_comite_qs = Credito.objects.filter(estado='EN_COMITE').select_related('cliente__usuario')
        
        if search_query:
            for term in search_query.split():
                creditos_comite_qs = creditos_comite_qs.filter(
                    Q(cliente__usuario__first_name__icontains=term) |
                    Q(cliente__usuario__last_name__icontains=term) |
                    Q(cliente__dni__icontains=term)
                )
        creditos_comite = creditos_comite_qs.order_by('-fecha_solicitud')

        pendientes = creditos_comite.count()
        aprobados = Credito.objects.filter(estado='APROBADO').count()
        rechazados = Credito.objects.filter(estado='RECHAZADO').count()
        
        # Gráfico: Aprobados vs Rechazados
        chart_resoluciones = {'APROBADO': aprobados, 'RECHAZADO': rechazados}

        # Gráfico: Créditos por tipo
        chart_tipos = list(Credito.objects.values('tipo_credito').annotate(c=Count('id')))

        # Tiempo promedio de resolución (Simulado basado en cantidad de procesados)
        procesados = aprobados + rechazados
        tiempo_promedio = "4.5" if procesados > 0 else "—"

        context.update({
            'creditos_comite': creditos_comite,
            'pendientes_count': pendientes,
            'aprobados_count': aprobados,
            'rechazados_count': rechazados,
            'tiempo_promedio': tiempo_promedio,
            'chart_resoluciones': json.dumps(chart_resoluciones),
            'chart_tipos': json.dumps(chart_tipos),
        })

    # ── GERENCIA ─────────────────────────────────────────────
    elif rol == 'GERENCIA':
        search_query = request.GET.get('q', '').strip()
        creditos_gerencia_qs = Credito.objects.filter(estado='EN_GERENCIA').select_related('cliente__usuario')
        
        if search_query:
            for term in search_query.split():
                creditos_gerencia_qs = creditos_gerencia_qs.filter(
                    Q(cliente__usuario__first_name__icontains=term) |
                    Q(cliente__usuario__last_name__icontains=term) |
                    Q(cliente__dni__icontains=term)
                )
        creditos_gerencia = creditos_gerencia_qs.order_by('-fecha_solicitud')

        total_clientes = Cliente.objects.filter(rol='CLIENTE').count()
        total_creditos = Credito.objects.count()
        creditos_aprobados = Credito.objects.filter(
            estado__in=['APROBADO', 'DESEMBOLSADO', 'PAGADO']
        ).count()
        creditos_rechazados = Credito.objects.filter(estado='RECHAZADO').count()
        creditos_en_proceso = Credito.objects.filter(
            estado__in=['EN_EVALUACION', 'EN_RIESGOS', 'EN_COMITE', 'EN_GERENCIA']
        ).count()
        monto_desembolsado = Credito.objects.filter(
            estado__in=['DESEMBOLSADO', 'PAGADO']
        ).aggregate(total=Sum('monto'))['total'] or 0
        total_cuentas = CuentaAhorro.objects.count()
        total_transferencias = Movimiento.objects.filter(
            tipo_operacion='TRANSFERENCIA_ENVIADA'
        ).count()
        total_movimientos = Movimiento.objects.count()
        cartera_total = Credito.objects.filter(
            estado='DESEMBOLSADO'
        ).aggregate(total=Sum('saldo_pendiente'))['total'] or 0

        # Gráfico: Colocaciones por mes
        colocaciones = list(Credito.objects.filter(estado='DESEMBOLSADO').annotate(
            month=TruncMonth('fecha_solicitud')
        ).values('month').annotate(total=Sum('monto')).order_by('month'))
        chart_colocaciones = [{'month': x['month'].strftime('%Y-%m') if x['month'] else 'N/A', 'total': float(x['total'])} for x in colocaciones]

        # Gráfico: Cartera por tipo
        cartera_tipo = list(Credito.objects.filter(estado='DESEMBOLSADO').values('tipo_credito').annotate(total=Sum('saldo_pendiente')))
        chart_cartera = {x['tipo_credito']: float(x['total']) for x in cartera_tipo}

        # Gráfico: Mora por bandas
        chart_mora = get_kpis_mora()['conteo_bandas']

        # Gráfico: Aprobados vs Rechazados (Volumen vs Cantidad)
        chart_aprob_rech = {'Aprobados': creditos_aprobados, 'Rechazados': creditos_rechazados}

        # Gráfico: Flujo de Aprobaciones
        flujo_aprob = {
            '1. Solicitados': total_creditos,
            '2. Riesgos': Credito.objects.filter(estado__in=['EN_RIESGOS', 'EN_COMITE', 'EN_GERENCIA', 'APROBADO', 'DESEMBOLSADO', 'PAGADO']).count(),
            '3. Comité': Credito.objects.filter(estado__in=['EN_COMITE', 'EN_GERENCIA', 'APROBADO', 'DESEMBOLSADO', 'PAGADO']).count(),
            '4. Aprobados': creditos_aprobados,
            '5. Desembolsados': Credito.objects.filter(estado__in=['DESEMBOLSADO', 'PAGADO']).count(),
        }

        context.update({
            'creditos_gerencia': creditos_gerencia,
            'pendientes_count': creditos_gerencia.count(),
            'total_clientes': total_clientes,
            'total_creditos': total_creditos,
            'creditos_aprobados': creditos_aprobados,
            'creditos_rechazados': creditos_rechazados,
            'creditos_en_proceso': creditos_en_proceso,
            'monto_desembolsado': f"{monto_desembolsado:,.2f}",
            'total_cuentas': total_cuentas,
            'total_transferencias': total_transferencias,
            'total_movimientos': total_movimientos,
            'cartera_total': f"{cartera_total:,.2f}",
            'chart_colocaciones': json.dumps(chart_colocaciones),
            'chart_cartera': json.dumps(chart_cartera),
            'chart_mora': json.dumps(chart_mora),
            'chart_aprob_rech': json.dumps(chart_aprob_rech),
            'flujo_aprob': json.dumps(flujo_aprob),
        })

    # ── ADMIN ────────────────────────────────────────────────
    elif rol == 'ADMIN':


        total_usuarios = User.objects.count()
        total_movimientos = Movimiento.objects.count()
        volumen_movimientos = Movimiento.objects.aggregate(t=Sum('monto'))['t'] or 0

        # Gráfico: Operaciones por módulo
        ops_modulo = list(Movimiento.objects.values('tipo_operacion').annotate(c=Count('id')))
        chart_ops = {x['tipo_operacion']: x['c'] for x in ops_modulo}

        # Gráfico: Actividad mensual (Volumen S/)
        actividad = list(Movimiento.objects.annotate(month=TruncMonth('fecha')).values('month').annotate(total=Sum('monto')).order_by('month'))
        chart_actividad = [{'month': x['month'].strftime('%Y-%m') if x['month'] else 'N/A', 'total': float(x['total'])} for x in actividad]

        # Gráfico: Recuentos generales
        chart_general = {
            'Créditos': Credito.objects.count(),
            'Cuentas': CuentaAhorro.objects.count(),
            'Seguros': Seguro.objects.count(),
        }


        search_query = request.GET.get('q', '').strip()
        usuarios_list_qs = Cliente.objects.select_related('usuario').all()
        if search_query:
            for term in search_query.split():
                usuarios_list_qs = usuarios_list_qs.filter(
                    Q(usuario__first_name__icontains=term) |
                    Q(usuario__last_name__icontains=term) |
                    Q(dni__icontains=term)
                )
        usuarios_list = usuarios_list_qs.order_by('-usuario__date_joined')[:50]

        context.update(_obtener_contexto_admin(request, usuarios_list))

        total_creditos = Credito.objects.count()
        total_clientes = Cliente.objects.filter(rol='CLIENTE').count()
        total_cuentas = CuentaAhorro.objects.count()
        roles_count = {item['rol']: item['count'] for item in Cliente.objects.values('rol').annotate(count=Count('id'))}
        
        context.update({
            'total_usuarios': total_usuarios,
            'total_movimientos': total_movimientos,
            'volumen_movimientos': f"{volumen_movimientos:,.2f}",
            'chart_ops': json.dumps(chart_ops),
            'chart_actividad': json.dumps(chart_actividad),
            'chart_general': json.dumps(chart_general),
            'usuarios_list': usuarios_list,
            'total_creditos': total_creditos,
            'total_clientes': total_clientes,
            'total_cuentas': total_cuentas,
            'roles_count': roles_count,
            'roles_choices': Cliente.ROLES_CHOICES,
        })


    return render(request, 'dashboard.html', context)


# ──────────────────────────────────────────────────────────────
#  AGREGAR TARJETA (existente)
# ──────────────────────────────────────────────────────────────

@login_required(login_url='/')
def agregar_tarjeta(request):
    if request.method == 'POST':
        numero_tarjeta = request.POST.get('numero_tarjeta', '').replace(' ', '')
        vencimiento = request.POST.get('vencimiento')
        nombre_tarjeta = request.POST.get('nombre_tarjeta')
        pin = request.POST.get('pin')

        if not request.user.check_password(pin):
            messages.error(request, 'La contraseña ingresada es incorrecta. No se pudo vincular la tarjeta.')
            return redirect('dashboard:index')

        if numero_tarjeta and len(numero_tarjeta) >= 4:
            try:
                cliente = Cliente.objects.get(usuario=request.user)
            except Cliente.DoesNotExist:
                messages.error(request, 'No se encontró el perfil de cliente.')
                return redirect('dashboard:index')

            ultimos_cuatro = numero_tarjeta[-4:]

            # Generar un número de cuenta único basado en la tarjeta
            import uuid
            numero_cuenta = f"194-{uuid.uuid4().hex[:5].upper()}-{ultimos_cuatro}"

            # Crear una CuentaAhorro real en la base de datos
            with transaction.atomic():
                cuenta = CuentaAhorro.objects.create(
                    cliente=cliente,
                    numero_cuenta=numero_cuenta,
                    tipo_cuenta=f"Tarjeta VISA ****{ultimos_cuatro}",
                    saldo=Decimal('0.00'),
                    estado='ACTIVA',
                )

                # Registrar movimiento de apertura
                Movimiento.objects.create(
                    cuenta=cuenta,
                    tipo_operacion='DEPOSITO',
                    monto=Decimal('0.00'),
                    saldo_resultante=Decimal('0.00'),
                    descripcion=f"Apertura de cuenta vinculada a tarjeta ****{ultimos_cuatro}",
                )

            # Guardar en sesión para la vista de tarjeta visual
            request.session['tarjeta_vinculada'] = {
                'numero': f"**** **** **** {ultimos_cuatro}",
                'vencimiento': vencimiento,
                'nombre': nombre_tarjeta,
                'cuenta_id': cuenta.id,
            }
            messages.success(request, f'¡Excelente! La tarjeta terminada en {ultimos_cuatro} ha sido vinculada. Se creó la cuenta {numero_cuenta}.')
        else:
            messages.error(request, 'Ocurrió un error al vincular la tarjeta.')
    return redirect('dashboard:index')


# ──────────────────────────────────────────────────────────────
#  ASESOR — Vistas de acción
# ──────────────────────────────────────────────────────────────

@role_required(['ASESOR', 'ADMIN'])
def asesor_clientes(request):
    """Lista todos los clientes registrados con sus datos reales (optimizado)."""
    search_query = request.GET.get('q', '').strip()
    
    clientes_qs = Cliente.objects.filter(
        rol='CLIENTE', estado=True
    ).select_related('usuario')

    if search_query:
        for term in search_query.split():
            clientes_qs = clientes_qs.filter(
                Q(usuario__first_name__icontains=term) |
                Q(usuario__last_name__icontains=term) |
                Q(dni__icontains=term)
            )

    clientes = clientes_qs.annotate(
        cuentas_count=Count('cuentaahorro', filter=Q(cuentaahorro__estado='ACTIVA'), distinct=True),
        saldo_total=Sum('cuentaahorro__saldo', filter=Q(cuentaahorro__estado='ACTIVA')),
        creditos_activos=Count('creditos', filter=Q(creditos__estado='DESEMBOLSADO'), distinct=True)
    ).order_by('usuario__first_name')

    clientes_data = []
    for c in clientes:
        clientes_data.append({
            'cliente': c,
            'nombre_completo': c.usuario.get_full_name(),
            'dni': c.dni,
            'telefono': c.telefono,
            'email': c.usuario.email,
            'cuentas_count': c.cuentas_count,
            'saldo_total': c.saldo_total or Decimal('0.00'),
            'creditos_activos': c.creditos_activos,
            'score': c.score_crediticio,
            'ingresos': c.ingresos,
        })

    return render(request, 'dashboard.html', {
        'rol': 'ASESOR',
        'vista_asesor': 'clientes',
        'clientes_data': clientes_data,
        'total_clientes': len(clientes_data),
        'user_name': request.user.get_full_name(),
        'first_name': request.user.first_name,
        'unread_notifications': Notificacion.objects.filter(cliente=request.user.cliente, leida=False).count(),
        'currency': 'S/',
    })


@role_required(['ASESOR', 'ADMIN'])
def asesor_derivar(request, credito_id):
    """Deriva un crédito EN_EVALUACION a EN_RIESGOS."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    credito = get_object_or_404(Credito, id=credito_id, estado='EN_EVALUACION')

    with transaction.atomic():
        estado_ant = credito.estado
        credito.estado = 'EN_RIESGOS'
        credito.save()

        _registrar_historial(credito, request.user, 'ASESOR', "Derivado a evaluación de riesgos.", estado_ant, 'EN_RIESGOS')

        Notificacion.objects.create(
            cliente=credito.cliente,
            mensaje=f"📋 Tu solicitud de crédito {credito.tipo_credito} por S/ {credito.monto:,.2f} ha sido derivada a evaluación de riesgos.",
        )

    messages.success(request, f'Solicitud #{credito.id} derivada a Riesgos exitosamente.')
    return redirect('dashboard:index')


@role_required(['ASESOR', 'ADMIN'])
def asesor_desembolsar(request, credito_id):
    """Desembolsa un crédito APROBADO."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    credito = get_object_or_404(Credito, id=credito_id, estado='APROBADO')

    with transaction.atomic():
        estado_ant = credito.estado
        credito.estado = 'DESEMBOLSADO'
        credito.save()

        _registrar_historial(credito, request.user, 'ASESOR', "Crédito desembolsado exitosamente.", estado_ant, 'DESEMBOLSADO')

        # Determinar la cuenta destino a partir de observaciones o la primera activa
        cuenta = None
        import re
        match = re.search(r"Cuenta Destino Solicitada ID: (\d+)", credito.observaciones)
        if match:
            cuenta_id = match.group(1)
            cuenta = CuentaAhorro.objects.filter(id=cuenta_id, cliente=credito.cliente, estado='ACTIVA').first()

        if not cuenta:
            cuenta = CuentaAhorro.objects.filter(
                cliente=credito.cliente, estado='ACTIVA'
            ).first()

        if not cuenta:
            import uuid
            numero_cuenta = f"194-{uuid.uuid4().hex[:5].upper()}-0001"
            from decimal import Decimal
            cuenta = CuentaAhorro.objects.create(
                cliente=credito.cliente,
                numero_cuenta=numero_cuenta,
                tipo_cuenta="Cuenta Principal",
                saldo=Decimal('0.00'),
                estado='ACTIVA',
            )

        cuenta.saldo += credito.monto
        cuenta.save()
        Movimiento.objects.create(
            cuenta=cuenta,
            tipo_operacion='DEPOSITO',
            monto=credito.monto,
            saldo_resultante=cuenta.saldo,
            descripcion=f"Desembolso crédito {credito.tipo_credito} — Aprobado",
        )

        Notificacion.objects.create(
            cliente=credito.cliente,
            mensaje=f"🎉 ¡Tu crédito {credito.tipo_credito} por S/ {credito.monto:,.2f} ha sido DESEMBOLSADO! Ya puedes usar tu dinero. Cuota mensual: S/ {credito.cuota_mensual:,.2f}.",
        )
        
    messages.success(request, f'Crédito #{credito.id} desembolsado exitosamente en la cuenta del cliente.')
    return redirect('dashboard:index')


# ──────────────────────────────────────────────────────────────
#  RIESGOS — Vistas de acción
# ──────────────────────────────────────────────────────────────

@role_required(['RIESGOS', 'ADMIN'])
def riesgos_evaluar(request, credito_id):
    """Aprueba o rechaza una solicitud desde Riesgos. Enruta según monto."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    credito = get_object_or_404(Credito, id=credito_id, estado='EN_RIESGOS')
    accion = request.POST.get('accion')  # 'aprobar' o 'rechazar'
    observaciones = request.POST.get('observaciones', '')

    with transaction.atomic():
        estado_ant = credito.estado
        credito.observaciones += f"\n[Riesgos] {observaciones}"

        if accion == 'aprobar':
            # Enviar SIEMPRE a COMITE para cumplir el flujo completo de evaluación
            credito.estado = 'EN_COMITE'
            msg = "evaluada favorablemente por Riesgos y derivada al Comité."
            notif_msg = f"✅ Tu solicitud de crédito {credito.tipo_credito} ha pasado la evaluación de riesgos y ahora está en revisión por el Comité de Créditos."
            credito.save()
            _registrar_historial(credito, request.user, 'RIESGOS', f"Aprobada. {observaciones}", estado_ant, credito.estado)
            Notificacion.objects.create(cliente=credito.cliente, mensaje=notif_msg)
            messages.success(request, f'Solicitud #{credito.id} {msg}')

        elif accion == 'rechazar':
            credito.estado = 'RECHAZADO'
            credito.save()
            _registrar_historial(credito, request.user, 'RIESGOS', observaciones or "Rechazado en riesgos.", estado_ant, 'RECHAZADO')
            Notificacion.objects.create(
                cliente=credito.cliente,
                mensaje=f"❌ Tu solicitud de crédito {credito.tipo_credito} por S/ {credito.monto:,.2f} fue rechazada en evaluación de riesgos. Motivo: {observaciones}",
            )
            messages.success(request, f'Solicitud #{credito.id} rechazada.')
        else:
            messages.error(request, 'Acción no válida.')

    return redirect('dashboard:index')


# ──────────────────────────────────────────────────────────────
#  COMITE — Vistas de acción
# ──────────────────────────────────────────────────────────────

@role_required(['COMITE', 'ADMIN'])
def comite_resolver(request, credito_id):
    """Aprueba o rechaza un crédito desde Comité. Enruta según monto."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    credito = get_object_or_404(Credito, id=credito_id, estado='EN_COMITE')
    accion = request.POST.get('accion')
    observaciones = request.POST.get('observaciones', '')

    with transaction.atomic():
        estado_ant = credito.estado
        credito.observaciones += f"\n[Comité] {observaciones}"

        if accion == 'aprobar':
            # Lógica de ruteo por monto
            if credito.monto <= Decimal('50000'):
                credito.estado = 'APROBADO'
                msg = "aprobada por Comité y lista para desembolso."
                notif_msg = f"✅ Tu crédito {credito.tipo_credito} ha sido APROBADO por el Comité. Próximamente será desembolsado."
            else:
                credito.estado = 'EN_GERENCIA'
                msg = "aprobada en Comité y derivada a Gerencia."
                notif_msg = f"✅ Tu solicitud de crédito {credito.tipo_credito} pasó la evaluación de Comité y fue derivada a Gerencia."

            credito.save()
            _registrar_historial(credito, request.user, 'COMITE', observaciones or "Aprobado en Comité.", estado_ant, credito.estado)
            Notificacion.objects.create(cliente=credito.cliente, mensaje=notif_msg)
            messages.success(request, f'Crédito #{credito.id} {msg}')

        elif accion == 'rechazar':
            credito.estado = 'RECHAZADO'
            credito.save()
            _registrar_historial(credito, request.user, 'COMITE', observaciones or "Rechazado en Comité.", estado_ant, 'RECHAZADO')
            Notificacion.objects.create(
                cliente=credito.cliente,
                mensaje=f"❌ Tu solicitud de crédito {credito.tipo_credito} por S/ {credito.monto:,.2f} fue rechazada por el Comité. Motivo: {observaciones}",
            )
            messages.success(request, f'Crédito #{credito.id} rechazado.')
        else:
            messages.error(request, 'Acción no válida.')

    return redirect('dashboard:index')


# ──────────────────────────────────────────────────────────────
#  GERENCIA — Vistas de acción
# ──────────────────────────────────────────────────────────────

@role_required(['GERENCIA', 'ADMIN'])
def gerencia_resolver(request, credito_id):
    """Aprueba definitivamente o rechaza créditos de alto monto (>50k)."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    credito = get_object_or_404(Credito, id=credito_id, estado='EN_GERENCIA')
    accion = request.POST.get('accion')
    observaciones = request.POST.get('observaciones', '')

    with transaction.atomic():
        estado_ant = credito.estado
        credito.observaciones += f"\n[Gerencia] {observaciones}"

        if accion == 'aprobar':
            credito.estado = 'APROBADO'
            credito.save()
            _registrar_historial(credito, request.user, 'GERENCIA', observaciones or "Aprobado en Gerencia.", estado_ant, 'APROBADO')
            Notificacion.objects.create(
                cliente=credito.cliente,
                mensaje=f"✅ Tu crédito {credito.tipo_credito} ha sido APROBADO por Alta Gerencia. Próximamente será desembolsado.",
            )
            messages.success(request, f'Crédito #{credito.id} aprobado por Gerencia y listo para desembolso.')

        elif accion == 'rechazar':
            credito.estado = 'RECHAZADO'
            credito.save()
            _registrar_historial(credito, request.user, 'GERENCIA', observaciones or "Rechazado en Gerencia.", estado_ant, 'RECHAZADO')
            Notificacion.objects.create(
                cliente=credito.cliente,
                mensaje=f"❌ Tu solicitud de crédito {credito.tipo_credito} fue rechazada por Alta Gerencia. Motivo: {observaciones}",
            )
            messages.success(request, f'Crédito #{credito.id} rechazado.')
        else:
            messages.error(request, 'Acción no válida.')

    return redirect('dashboard:index')


# ──────────────────────────────────────────────────────────────
#  ADMIN — Vistas de acción
# ──────────────────────────────────────────────────────────────

@role_required(['ADMIN'])
def admin_usuarios(request):
    """Lista completa de usuarios para administración."""
    search_query = request.GET.get('q', '').strip()
    usuarios_list_qs = Cliente.objects.select_related('usuario').all()
    
    if search_query:
        for term in search_query.split():
            usuarios_list_qs = usuarios_list_qs.filter(
                Q(usuario__first_name__icontains=term) |
                Q(usuario__last_name__icontains=term) |
                Q(dni__icontains=term)
            )
    
    usuarios_list = usuarios_list_qs.order_by('rol', 'usuario__first_name')


    context = _obtener_contexto_admin(request, usuarios_list)
    context['vista_admin'] = 'usuarios'
    return render(request, 'dashboard.html', context)

    return render(request, 'dashboard.html', {
        'rol': 'ADMIN',
        'vista_admin': 'usuarios',
        'usuarios_list': usuarios_list,
        'total_usuarios': User.objects.count(),
        'roles_choices': Cliente.ROLES_CHOICES,
        'user_name': request.user.get_full_name(),
        'first_name': request.user.first_name,
        'unread_notifications': Notificacion.objects.filter(cliente=request.user.cliente, leida=False).count(),
        'currency': 'S/',
    })



@role_required(['ADMIN'])
def admin_cambiar_rol(request, cliente_id):
    """Cambia el rol de un usuario."""
    if request.method != 'POST':
        return redirect('dashboard:index')

    cliente_obj = get_object_or_404(Cliente, id=cliente_id)
    nuevo_rol = request.POST.get('nuevo_rol')
    roles_validos = [r[0] for r in Cliente.ROLES_CHOICES]

    if nuevo_rol not in roles_validos:
        messages.error(request, 'Rol no válido.')
        return redirect('dashboard:admin_usuarios')

    old_rol = cliente_obj.rol
    cliente_obj.rol = nuevo_rol
    cliente_obj.save()

    Notificacion.objects.create(
        cliente=cliente_obj,
        mensaje=f"🔄 Tu rol ha sido cambiado de {old_rol} a {nuevo_rol} por un administrador.",
    )

    messages.success(request, f'Rol de {cliente_obj.usuario.get_full_name()} cambiado de {old_rol} a {nuevo_rol}.')
    return redirect('dashboard:admin_usuarios')
