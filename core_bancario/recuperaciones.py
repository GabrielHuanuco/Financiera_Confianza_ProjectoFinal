"""
recuperaciones.py — Utilidades de cálculo de mora para Financiera Confianza.

No contiene vistas ni lógica de Django views; solo funciones puras de cálculo
que pueden ser importadas desde cualquier vista o template tag.
"""
from datetime import date, timedelta
from decimal import Decimal


# ──────────────────────────────────────────────────────────────
#  DEFINICIÓN DE BANDAS
# ──────────────────────────────────────────────────────────────

BANDAS_MORA = [
    # (label,         min_dias, max_dias, color_css,    color_badge)
    ('AL_DIA',        None,  0,    '#10b981', 'badge-verde'),
    ('PREVENTIVA',    1,    30,    '#3b82f6', 'badge-azul'),
    ('TEMPRANA',     31,    60,    '#f59e0b', 'badge-amarillo'),
    ('TARDIA',       61,   120,    '#f97316', 'badge-naranja'),
    ('JUDICIAL',    121,   180,    '#ef4444', 'badge-rojo'),
    ('CASTIGO',     181,  None,    '#475569', 'badge-gris'),
]

BANDA_LABELS = {
    'AL_DIA':     'Al Día',
    'PREVENTIVA': 'Preventiva (1-30 días)',
    'TEMPRANA':   'Temprana (31-60 días)',
    'TARDIA':     'Tardía (61-120 días)',
    'JUDICIAL':   'Judicial (121-180 días)',
    'CASTIGO':    'Castigo (>180 días)',
}


def calcular_dias_mora(credito):
    """
    Calcula cuántos días lleva en mora un crédito DESEMBOLSADO.

    Lógica:
      - La cuota N vence 30 días después del desembolso × N
      - Si cuotas_pagadas = k, la cuota k+1 vence en fecha_solicitud + (k+1)*30 días
      - dias_mora = hoy - fecha_vencimiento_proxima_cuota
      - Si negativo → al día (0)

    Retorna int ≥ 0.
    """
    if credito.estado not in ('DESEMBOLSADO',):
        return 0

    cuotas_pagadas = credito.cuotas_pagadas
    # Si ya pagó todas las cuotas → 0 mora
    if cuotas_pagadas >= credito.cuotas:
        return 0

    # Fecha de vencimiento de la próxima cuota por pagar
    proxima_cuota_num = cuotas_pagadas + 1
    fecha_desembolso = credito.fecha_solicitud.date()
    fecha_vencimiento = fecha_desembolso + timedelta(days=30 * proxima_cuota_num)

    hoy = date.today()
    diferencia = (hoy - fecha_vencimiento).days
    return max(0, diferencia)


def clasificar_mora(dias_mora):
    """
    Dada una cantidad de días de mora, retorna un dict con:
    {
        'banda': 'PREVENTIVA',
        'label': 'Preventiva (1-30 días)',
        'color': '#3b82f6',
        'badge': 'badge-azul',
        'puede_judicializar': False,
        'puede_castigar': False,
    }
    """
    for banda, min_d, max_d, color, badge in BANDAS_MORA:
        en_rango = True
        if min_d is not None and dias_mora < min_d:
            en_rango = False
        if max_d is not None and dias_mora > max_d:
            en_rango = False
        if en_rango:
            return {
                'banda': banda,
                'label': BANDA_LABELS[banda],
                'color': color,
                'badge': badge,
                'puede_judicializar': dias_mora >= 121,
                'puede_castigar': dias_mora > 180,
            }
    # Fallback
    return {
        'banda': 'CASTIGO',
        'label': BANDA_LABELS['CASTIGO'],
        'color': '#475569',
        'badge': 'badge-gris',
        'puede_judicializar': True,
        'puede_castigar': True,
    }


def enriquecer_credito(credito):
    """
    Dado un objeto Credito, retorna un dict con todos los datos
    necesarios para la bandeja de mora.
    """
    dias = calcular_dias_mora(credito)
    info = clasificar_mora(dias)

    # Estado judicial/castigo
    try:
        estado_mora = credito.estado_mora
        estado_judicial = estado_mora.estado
    except Exception:
        estado_judicial = 'NORMAL'

    # Última gestión
    ultima_gestion = credito.gestiones_cobranza.first()

    return {
        'credito': credito,
        'cliente': credito.cliente,
        'dias_mora': dias,
        'banda': info['banda'],
        'banda_label': info['label'],
        'banda_color': info['color'],
        'banda_badge': info['badge'],
        'puede_judicializar': info['puede_judicializar'],
        'puede_castigar': info['puede_castigar'],
        'monto_vencido': credito.saldo_pendiente,
        'cuotas_pendientes': credito.cuotas - credito.cuotas_pagadas,
        'estado_judicial': estado_judicial,
        'ultima_gestion': ultima_gestion,
        'total_gestiones': credito.gestiones_cobranza.count(),
    }


def get_cartera_morosa():
    """
    Retorna lista de dicts (enriquecidos) para todos los créditos
    DESEMBOLSADO con mora > 0, ordenados por días de mora desc.
    """
    from creditos.models import Credito
    creditos = Credito.objects.filter(
        estado='DESEMBOLSADO'
    ).select_related(
        'cliente__usuario', 'estado_mora'
    ).prefetch_related('gestiones_cobranza', 'pagos')

    morosos = []
    for c in creditos:
        datos = enriquecer_credito(c)
        if datos['dias_mora'] > 0:
            morosos.append(datos)

    morosos.sort(key=lambda x: x['dias_mora'], reverse=True)
    return morosos


def get_kpis_mora(cartera=None):
    """
    Calcula los KPIs de mora a partir de la cartera morosa.
    Si no se pasa cartera, la calcula internamente.
    """
    if cartera is None:
        cartera = get_cartera_morosa()

    total_creditos = len(cartera)
    clientes_ids = {d['cliente'].id for d in cartera}
    total_clientes = len(clientes_ids)
    monto_vencido = sum(d['monto_vencido'] for d in cartera)

    conteo_bandas = {
        'PREVENTIVA': 0,
        'TEMPRANA': 0,
        'TARDIA': 0,
        'JUDICIAL': 0,
        'CASTIGO': 0,
    }
    for d in cartera:
        if d['banda'] in conteo_bandas:
            conteo_bandas[d['banda']] += 1

    return {
        'total_creditos': total_creditos,
        'total_clientes': total_clientes,
        'monto_vencido': monto_vencido,
        'conteo_bandas': conteo_bandas,
    }
