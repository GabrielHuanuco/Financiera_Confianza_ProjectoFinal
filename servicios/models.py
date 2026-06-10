from django.db import models
from authentication.models import Cliente

class PagoServicio(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo_servicio = models.CharField(max_length=50)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_pago = models.CharField(max_length=50)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_servicio} - {self.codigo_pago}"
