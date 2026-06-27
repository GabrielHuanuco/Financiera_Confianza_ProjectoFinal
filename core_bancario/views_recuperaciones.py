"""
views_recuperaciones.py — Vistas del módulo de Recuperaciones y Mora.

Acceso:
  - bandeja_mora    → RIESGOS, GERENCIA, ADMIN
  - registrar_gestion → RIESGOS, GERENCIA, ADMIN
  - judicializar    → GERENCIA, ADMIN (≥ 121 días mora)
  - castigar        → GERENCIA, ADMIN (> 180 días mora)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse

from .decorators import role_required
from .recuperaciones import (
    get_cartera_morosa, get_kpis_mora,
    calcular_dias_mora, clasificar_mora, enriquecer_credito
)
from .models import GestionCobranza, EstadoMora
from creditos.models import Credito


# ──────────────────────────────────────────────────────────────
#  BANDEJA DE MORA — RIESGOS, GERENCIA, ADMIN
# ──────────────────────────────────────────────────────────────

@role_required(['RIESGOS', 'GERENCIA', 'ADMIN'])
def bandeja_mora(request):
    """
    Vista principal de recuperaciones: muestra KPIs y la tabla de
    créditos morosos con sus gestiones y opciones de acción.
    """
    cartera = get_cartera_morosa()
    kpis    = get_kpis_mora(cartera)

    # Filtro por banda (query param ?banda=PREVENTIVA)
    banda_filtro = request.GET.get('banda', 'TODAS')
    if banda_filtro != 'TODAS':
        cartera_filtrada = [d for d in cartera if d['banda'] == banda_filtro]
    else:
        cartera_filtrada = cartera

    try:
        rol_usuario = request.user.cliente.rol
    except Exception:
        rol_usuario = 'RIESGOS'

    context = {
        'cartera': cartera_filtrada,
        'cartera_completa': cartera,
        'kpis': kpis,
        'banda_filtro': banda_filtro,
        'rol': rol_usuario,
        'user_name': request.user.get_full_name() or request.user.username,
        'first_name': request.user.first_name or request.user.username,
        'bandas_disponibles': ['TODAS', 'PREVENTIVA', 'TEMPRANA', 'TARDIA', 'JUDICIAL', 'CASTIGO'],
    }
    return render(request, 'core/recuperaciones.html', context)


# ──────────────────────────────────────────────────────────────
#  DETALLE DE CRÉDITO — panel lateral con historial de gestiones
# ──────────────────────────────────────────────────────────────

@role_required(['RIESGOS', 'GERENCIA', 'ADMIN'])
def detalle_mora(request, credito_id):
    """Retorna JSON con el detalle de un crédito y sus gestiones (para modal)."""
    credito = get_object_or_404(Credito, id=credito_id, estado='DESEMBOLSADO')
    datos   = enriquecer_credito(credito)

    gestiones = []
    for g in credito.gestiones_cobranza.all()[:10]:
        gestiones.append({
            'fecha':    g.fecha.strftime('%d/%m/%Y %H:%M'),
            'usuario':  g.usuario.get_full_name() if g.usuario else '—',
            'rol':      g.rol,
            'resultado': g.get_resultado_display(),
            'comentario': g.comentario,
            'dias_mora': g.dias_mora_snapshot,
            'banda':    g.banda_mora_snapshot,
        })

    return JsonResponse({
        'credito_id': credito.id,
        'cliente': credito.cliente.usuario.get_full_name(),
        'dni': credito.cliente.dni,
        'tipo_credito': credito.tipo_credito,
        'monto': str(credito.monto),
        'cuota_mensual': str(credito.cuota_mensual),
        'saldo_pendiente': str(credito.saldo_pendiente),
        'cuotas_pagadas': credito.cuotas_pagadas,
        'cuotas_total': credito.cuotas,
        'dias_mora': datos['dias_mora'],
        'banda': datos['banda'],
        'banda_label': datos['banda_label'],
        'estado_judicial': datos['estado_judicial'],
        'puede_judicializar': datos['puede_judicializar'],
        'puede_castigar': datos['puede_castigar'],
        'gestiones': gestiones,
    })


# ──────────────────────────────────────────────────────────────
#  REGISTRAR GESTIÓN DE COBRANZA
# ──────────────────────────────────────────────────────────────

@role_required(['RIESGOS', 'GERENCIA', 'ADMIN'])
def registrar_gestion(request, credito_id):
    """Registra una nueva gestión de cobranza sobre un crédito moroso."""
    if request.method != 'POST':
        return redirect('core_bancario:bandeja_mora')

    credito   = get_object_or_404(Credito, id=credito_id)
    comentario = request.POST.get('comentario', '').strip()
    resultado  = request.POST.get('resultado', '')

    if not comentario or not resultado:
        messages.error(request, 'Debes ingresar un comentario y seleccionar el resultado.')
        return redirect('core_bancario:bandeja_mora')

    dias_mora = calcular_dias_mora(credito)
    info_mora = clasificar_mora(dias_mora)

    try:
        rol = request.user.cliente.rol
    except Exception:
        rol = 'RIESGOS'

    GestionCobranza.objects.create(
        credito=credito,
        usuario=request.user,
        rol=rol,
        comentario=comentario,
        resultado=resultado,
        dias_mora_snapshot=dias_mora,
        banda_mora_snapshot=info_mora['banda'],
    )

    messages.success(
        request,
        f'Gestión registrada exitosamente para el crédito #{credito.id} '
        f'— {dias_mora} días de mora ({info_mora["label"]}).'
    )
    return redirect('core_bancario:bandeja_mora')


# ──────────────────────────────────────────────────────────────
#  JUDICIALIZAR — solo GERENCIA y ADMIN, mínimo 121 días
# ──────────────────────────────────────────────────────────────

@role_required(['GERENCIA', 'ADMIN'])
def judicializar(request, credito_id):
    """Pasa un crédito al estado JUDICIAL. Requiere ≥ 121 días de mora."""
    if request.method != 'POST':
        return redirect('core_bancario:bandeja_mora')

    credito = get_object_or_404(Credito, id=credito_id, estado='DESEMBOLSADO')
    dias    = calcular_dias_mora(credito)

    if dias < 121:
        messages.error(
            request,
            f'No se puede judicializar: el crédito #{credito.id} solo tiene '
            f'{dias} días de mora. Se requieren mínimo 121 días.'
        )
        return redirect('core_bancario:bandeja_mora')

    observacion = request.POST.get('observacion', '').strip()

    estado_mora, _ = EstadoMora.objects.get_or_create(credito=credito)
    estado_mora.estado = 'JUDICIAL'
    estado_mora.usuario_cambio = request.user
    estado_mora.observacion = observacion or f'Judicializado con {dias} días de mora.'
    estado_mora.save()

    # Registrar gestión automática
    try:
        rol = request.user.cliente.rol
    except Exception:
        rol = 'GERENCIA'

    GestionCobranza.objects.create(
        credito=credito,
        usuario=request.user,
        rol=rol,
        comentario=observacion or f'Crédito judicializado con {dias} días de mora.',
        resultado='ACUERDO_PAGO',
        dias_mora_snapshot=dias,
        banda_mora_snapshot='JUDICIAL',
    )

    messages.success(
        request,
        f'Crédito #{credito.id} marcado como JUDICIAL ({dias} días de mora).'
    )
    return redirect('core_bancario:bandeja_mora')


# ──────────────────────────────────────────────────────────────
#  CASTIGAR — solo GERENCIA y ADMIN, mínimo 181 días
# ──────────────────────────────────────────────────────────────

@role_required(['GERENCIA', 'ADMIN'])
def castigar(request, credito_id):
    """Pasa un crédito al estado CASTIGO. Requiere > 180 días de mora."""
    if request.method != 'POST':
        return redirect('core_bancario:bandeja_mora')

    credito = get_object_or_404(Credito, id=credito_id, estado='DESEMBOLSADO')
    dias    = calcular_dias_mora(credito)

    if dias <= 180:
        messages.error(
            request,
            f'No se puede castigar: el crédito #{credito.id} tiene {dias} días '
            f'de mora. Se requieren más de 180 días.'
        )
        return redirect('core_bancario:bandeja_mora')

    observacion = request.POST.get('observacion', '').strip()

    estado_mora, _ = EstadoMora.objects.get_or_create(credito=credito)
    estado_mora.estado = 'CASTIGO'
    estado_mora.usuario_cambio = request.user
    estado_mora.observacion = observacion or f'Castigado con {dias} días de mora.'
    estado_mora.save()

    # Registrar gestión automática
    try:
        rol = request.user.cliente.rol
    except Exception:
        rol = 'GERENCIA'

    GestionCobranza.objects.create(
        credito=credito,
        usuario=request.user,
        rol=rol,
        comentario=observacion or f'Crédito castigado con {dias} días de mora.',
        resultado='SIN_CONTACTO',
        dias_mora_snapshot=dias,
        banda_mora_snapshot='CASTIGO',
    )

    messages.success(
        request,
        f'Crédito #{credito.id} marcado como CASTIGO ({dias} días de mora). '
        f'La deuda ha sido castigada contablemente.'
    )
    return redirect('core_bancario:bandeja_mora')
