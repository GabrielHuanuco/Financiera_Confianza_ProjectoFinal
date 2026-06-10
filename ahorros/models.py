from django.db import models
from authentication.models import Cliente

class CuentaAhorro(models.Model):

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE
    )

    numero_cuenta = models.CharField(
        max_length=20,
        unique=True
    )

    tipo_cuenta = models.CharField(max_length=50)

    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=20,
        default='ACTIVA'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.numero_cuenta