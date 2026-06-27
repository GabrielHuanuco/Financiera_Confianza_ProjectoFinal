from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


# ──────────────────────────────────────────────────────────────
#  ROLES
# ──────────────────────────────────────────────────────────────

ROLES_TRABAJADOR = ['ASESOR', 'RIESGOS', 'COMITE', 'GERENCIA', 'ADMIN']
ROLES_CLIENTE    = ['CLIENTE']


# ──────────────────────────────────────────────────────────────
#  role_required — Decorador genérico (existente, sin cambios)
# ──────────────────────────────────────────────────────────────

def role_required(roles=None):
    """
    Decorador que restringe el acceso a una vista según el rol del usuario.
    Retorna 403 si el usuario no tiene el rol adecuado.
    """
    if roles is None:
        roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/auth/')

            try:
                cliente = request.user.cliente
                if cliente.rol in roles:
                    return view_func(request, *args, **kwargs)
                else:
                    return render(request, '403.html', {
                        'motivo': 'No tienes permisos para acceder a esta área.',
                        'es_trabajador': cliente.rol in ROLES_TRABAJADOR,
                    }, status=403)
            except Exception:
                return redirect('/auth/')

        return _wrapped_view
    return decorator


# ──────────────────────────────────────────────────────────────
#  trabajador_required — Solo para personal interno del banco
# ──────────────────────────────────────────────────────────────

def trabajador_required(view_func):
    """
    Decorador que permite el acceso únicamente a trabajadores internos:
    ASESOR, RIESGOS, COMITE, GERENCIA, ADMIN.

    - Si no está autenticado → redirige al login del Core Bancario (/core/login/)
    - Si es CLIENTE → retorna 403 con página personalizada
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/core/login/')

        try:
            cliente = request.user.cliente
            if cliente.rol in ROLES_TRABAJADOR:
                return view_func(request, *args, **kwargs)
            else:
                # Cliente intentando acceder al Core Bancario
                return render(request, '403.html', {
                    'motivo': 'Esta área es exclusiva para el personal interno de Financiera Confianza.',
                    'es_trabajador': False,
                    'area_correcta_url': '/dashboard/',
                    'area_correcta_label': 'Ir a mi Homebanking',
                }, status=403)
        except Exception:
            return redirect('/core/login/')

    return _wrapped_view


# ──────────────────────────────────────────────────────────────
#  cliente_required — Solo para clientes del Homebanking
# ──────────────────────────────────────────────────────────────

def cliente_required(view_func):
    """
    Decorador que permite el acceso únicamente a clientes (rol=CLIENTE).

    - Si no está autenticado → redirige al login del Homebanking (/auth/)
    - Si es trabajador → retorna 403 con página personalizada
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/auth/')

        try:
            cliente = request.user.cliente
            if cliente.rol in ROLES_CLIENTE:
                return view_func(request, *args, **kwargs)
            else:
                # Trabajador intentando acceder al Homebanking
                return render(request, '403.html', {
                    'motivo': 'Esta área es exclusiva para clientes. Como trabajador, debes acceder al Core Bancario.',
                    'es_trabajador': True,
                    'area_correcta_url': '/core/',
                    'area_correcta_label': 'Ir al Core Bancario',
                }, status=403)
        except Exception:
            return redirect('/auth/')

    return _wrapped_view
