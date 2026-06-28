from django.db import models
from authentication.models import Cliente

class CuentaAhorro(models.Model):

    TIPOS_CUENTA = [
        ('Tradicional', 'Ahorro Tradicional (TREA ~3.50%)'),
        ('Plazo Fijo', 'Depósito a Plazo Fijo (TEA 3.13% - 6.38%)'),
        ('CTS', 'Cuenta CTS'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE
    )

    numero_cuenta = models.CharField(
        max_length=20,
        unique=True
    )

    tipo_cuenta = models.CharField(
        max_length=50,
        choices=TIPOS_CUENTA,
        default='Tradicional'
    )

    # Tasa Efectiva Anual (TEA/TREA)
    tasa_interes = models.DecimalField(
        max_digits=7, 
        decimal_places=4, 
        default=0.0350 # 3.50% por defecto (Ahorro tradicional)
    )

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