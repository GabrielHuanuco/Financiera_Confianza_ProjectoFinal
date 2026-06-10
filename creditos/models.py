from django.db import models
from decimal import Decimal
from authentication.models import Cliente


class Credito(models.Model):

    ESTADOS = [
        ('EN_EVALUACION', 'En Evaluación'),
        ('APROBADO',      'Aprobado'),
        ('DESEMBOLSADO',  'Desembolsado'),
        ('PAGADO',        'Pagado'),
        ('RECHAZADO',     'Rechazado'),
    ]

    TIPOS = [
        ('Personal',     'Préstamo Personal'),
        ('Vehicular',    'Préstamo Vehicular'),
        ('Hipotecario',  'Crédito Hipotecario'),
        ('Negocio',      'Crédito para Negocio'),
    ]

    # Tasas anuales por tipo de crédito
    TASAS = {
        'Personal':    Decimal('0.18'),   # 18% anual
        'Vehicular':   Decimal('0.14'),   # 14% anual
        'Hipotecario': Decimal('0.10'),   # 10% anual
        'Negocio':     Decimal('0.20'),   # 20% anual
    }

    cliente        = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='creditos')
    tipo_credito   = models.CharField(max_length=100, choices=TIPOS)
    monto          = models.DecimalField(max_digits=12, decimal_places=2)
    cuotas         = models.IntegerField()
    tasa_interes   = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.18'))
    cuota_mensual  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    saldo_pendiente= models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    cuotas_pagadas = models.IntegerField(default=0)
    estado         = models.CharField(max_length=30, choices=ESTADOS, default='EN_EVALUACION')
    fecha_solicitud= models.DateTimeField(auto_now_add=True)

    def calcular_cuota_mensual(self):
        """Sistema francés (cuota fija): M = P * [r(1+r)^n] / [(1+r)^n - 1]"""
        tasa_mensual = self.tasa_interes / 12
        n = self.cuotas
        if tasa_mensual == 0:
            return self.monto / n
        factor = (1 + tasa_mensual) ** n
        return self.monto * (tasa_mensual * factor) / (factor - 1)

    def progreso_pago(self):
        if self.cuotas == 0:
            return 0
        return int((self.cuotas_pagadas / self.cuotas) * 100)

    @property
    def cuotas_restantes(self):
        return self.cuotas - self.cuotas_pagadas

    def __str__(self):
        return f"{self.tipo_credito} — {self.cliente.usuario.username} — {self.estado}"


class PagoCuota(models.Model):
    credito    = models.ForeignKey(Credito, on_delete=models.CASCADE, related_name='pagos')
    numero_cuota = models.IntegerField()
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_tras_pago = models.DecimalField(max_digits=12, decimal_places=2)
    fecha      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cuota #{self.numero_cuota} — {self.credito}"
