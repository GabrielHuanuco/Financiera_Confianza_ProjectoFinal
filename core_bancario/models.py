from django.db import models
from ahorros.models import CuentaAhorro
from authentication.models import Cliente

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
