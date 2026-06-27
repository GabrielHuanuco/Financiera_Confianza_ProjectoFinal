from django.contrib import admin
from .models import Movimiento, Notificacion, GestionCobranza, EstadoMora

admin.site.register(Movimiento)
admin.site.register(Notificacion)


@admin.register(GestionCobranza)
class GestionCobranzaAdmin(admin.ModelAdmin):
    list_display  = ['id', 'credito', 'usuario', 'rol', 'resultado', 'dias_mora_snapshot', 'banda_mora_snapshot', 'fecha']
    list_filter   = ['resultado', 'rol', 'banda_mora_snapshot']
    search_fields = ['credito__id', 'usuario__username', 'comentario']
    ordering      = ['-fecha']


@admin.register(EstadoMora)
class EstadoMoraAdmin(admin.ModelAdmin):
    list_display  = ['credito', 'estado', 'usuario_cambio', 'fecha_cambio']
    list_filter   = ['estado']
    search_fields = ['credito__id']
