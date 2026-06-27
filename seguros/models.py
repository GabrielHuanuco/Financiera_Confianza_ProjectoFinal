from django.db import models
from authentication.models import Cliente


class Seguro(models.Model):
    TIPOS = [
        ('VIDA', 'Seguro de Vida'),
        ('DESGRAVAMEN', 'Seguro de Desgravamen'),
        ('VEHICULAR', 'Seguro Vehicular'),
        ('HOGAR', 'Seguro de Hogar'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='seguros')
    tipo_seguro = models.CharField(max_length=50, choices=TIPOS)
    prima_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    cobertura = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.BooleanField(default=True)
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.tipo_seguro} — {self.cliente.usuario.username}"
