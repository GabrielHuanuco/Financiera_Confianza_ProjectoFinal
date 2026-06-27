from django.shortcuts import redirect
from .decorators import trabajador_required


@trabajador_required
def core_dashboard(request):
    """
    Punto de entrada del Core Bancario.
    Reutiliza completamente la vista y template del dashboard existente.
    El acceso está restringido a: ASESOR, RIESGOS, COMITE, GERENCIA, ADMIN.
    """
    # Importamos aquí para evitar importación circular
    from dashboard.views import dashboard
    return dashboard(request)
