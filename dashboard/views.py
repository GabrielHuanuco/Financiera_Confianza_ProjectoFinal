from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from core_bancario.models import Movimiento, Notificacion
from django.db.models import Sum

@login_required(login_url='/')
def dashboard(request):
    try:
        cliente = Cliente.objects.get(usuario=request.user)
        cuentas = CuentaAhorro.objects.filter(cliente=cliente, estado='ACTIVA')
        
        # Calculate total balance
        total_balance = cuentas.aggregate(total=Sum('saldo'))['total'] or 0.00
        
        # Get recent transactions for all accounts of this client
        cuentas_ids = cuentas.values_list('id', flat=True)
        recent_transactions_qs = Movimiento.objects.filter(cuenta_id__in=cuentas_ids).order_by('-fecha')[:5]
        
        # Unread notifications
        unread_notifications = Notificacion.objects.filter(cliente=cliente, leida=False).count()
        
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
                'type': tx_type
            })
            
    except Cliente.DoesNotExist:
        cliente = None
        cuentas = CuentaAhorro.objects.none()   # ← QuerySet vacío, no lista
        total_balance = 0.00
        recent_transactions = []
        unread_notifications = 0

    context = {
        'user_name': request.user.get_full_name() or request.user.username,
        'first_name': request.user.first_name or request.user.username,
        'account_number': cuentas.first().numero_cuenta if cuentas else 'Sin cuenta',
        'total_balance': f"{total_balance:,.2f}",
        'currency': 'S/',
        'cuentas': cuentas,
        'recent_transactions': recent_transactions,
        'unread_notifications': unread_notifications,
        'quick_actions': [
            {'icon': 'bi-send', 'label': 'Transferir', 'url': 'transferencias:index'},
            {'icon': 'bi-receipt', 'label': 'Pagar Servicios', 'url': 'servicios:pagar'},
            {'icon': 'bi-cash', 'label': 'Pedir Préstamo', 'url': 'creditos:solicitar'},
            {'icon': 'bi-shield-check', 'label': 'Seguros', 'url': 'seguros:index'}
        ]
    }
    return render(request, 'dashboard.html', context)
