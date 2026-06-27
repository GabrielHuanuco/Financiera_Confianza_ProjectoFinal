from django.db import models
from ahorros.models import CuentaAhorro
from authentication.models import Cliente
from django.contrib.auth.models import User

class Movimiento(models.Model):
    TIPO_CHOICES = [
        ('DEPOSITO', 'Depósito'),
        ('RETIRO', 'Retiro'),
        ('TRANSFERENCIA_ENVIADA', 'Transferencia Enviada'),
        ('TRANSFERENCIA_RECIBIDA', 'Transferencia Recibida'),
        ('PAGO_SERVICIO', 'Pago de Servicio'),
    ]

    cuenta = models.ForeignKey(CuentaAhorro, on_delete=models.CASCADE, related_name='movimientos')
    tipo_operacion = models.CharField(max_length=50, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_resultante = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.tipo_operacion} - {self.monto} - {self.cuenta.numero_cuenta}"

class Notificacion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación para {self.cliente.usuario.username} - {'Leída' if self.leida else 'No leída'}"


# ──────────────────────────────────────────────────────────────
#  MÓDULO RECUPERACIONES Y MORA
# ──────────────────────────────────────────────────────────────

class GestionCobranza(models.Model):
    """Registro de cada acción de cobranza realizada sobre un crédito moroso."""

    RESULTADO_CHOICES = [
        ('LLAMADA',        'Llamada realizada'),
        ('PROMESA_PAGO',   'Cliente promete pago'),
        ('CORREO',         'Correo enviado'),
        ('VISITA',         'Visita realizada'),
        ('SIN_CONTACTO',   'Sin contacto'),
        ('PAGO_PARCIAL',   'Pago parcial recibido'),
        ('ACUERDO_PAGO',   'Acuerdo de pago suscrito'),
    ]

    credito            = models.ForeignKey(
        'creditos.Credito',
        on_delete=models.CASCADE,
        related_name='gestiones_cobranza'
    )
    usuario            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    rol                = models.CharField(max_length=20)
    fecha              = models.DateTimeField(auto_now_add=True)
    comentario         = models.TextField()
    resultado          = models.CharField(max_length=30, choices=RESULTADO_CHOICES)
    dias_mora_snapshot = models.IntegerField(default=0)
    banda_mora_snapshot = models.CharField(max_length=20, default='PREVENTIVA')

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"Gestión #{self.id} — Crédito {self.credito_id} — {self.resultado}"


class EstadoMora(models.Model):
    """Estado de escalamiento judicial o castigo de un crédito."""

    ESTADO_CHOICES = [
        ('NORMAL',   'Normal'),
        ('JUDICIAL', 'Judicial'),
        ('CASTIGO',  'Castigo / Cartera Castigada'),
    ]

    credito        = models.OneToOneField(
        'creditos.Credito',
        on_delete=models.CASCADE,
        related_name='estado_mora'
    )
    estado         = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='NORMAL')
    fecha_cambio   = models.DateTimeField(auto_now=True)
    usuario_cambio = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    observacion    = models.TextField(blank=True, default='')

    def __str__(self):
        return f"EstadoMora — Crédito {self.credito_id} — {self.estado}"

