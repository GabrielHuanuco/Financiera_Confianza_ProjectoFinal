from django.db import models
from decimal import Decimal
from authentication.models import Cliente
from django.contrib.auth.models import User


class Credito(models.Model):

    ESTADOS = [
        ('EN_EVALUACION', 'En Evaluación'),
        ('EN_RIESGOS',    'En Evaluación de Riesgos'),
        ('EN_COMITE',     'En Comité'),
        ('EN_GERENCIA',   'En Gerencia'),
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
        ('Microempresa', 'Crédito Microempresa'),
    ]

    # Tasas Efectivas Anuales (TEA) por tipo de crédito
    TASAS = {
        'Personal':      Decimal('0.18'),     # TEA 18%
        'Vehicular':     Decimal('0.14'),     # TEA 14%
        'Hipotecario':   Decimal('0.10'),     # TEA 10%
        'Negocio':       Decimal('0.20'),     # TEA 20%
        'Microempresa':  Decimal('0.4392'),   # TEA 43.92%
    }

    cliente        = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='creditos')
    tipo_credito   = models.CharField(max_length=100, choices=TIPOS)
    monto          = models.DecimalField(max_digits=12, decimal_places=2)
    cuotas         = models.IntegerField()
    tasa_interes   = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.18'))
    
    # Tasa Moratoria (Penalidad sobre saldo atrasado - 15% nominal anual BCRP)
    tasa_moratoria = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.15'))
    
    incluye_desgravamen = models.BooleanField(default=True)
    incluye_multiriesgo = models.BooleanField(default=True)

    
    cuota_mensual  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    saldo_pendiente= models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    cuotas_pagadas = models.IntegerField(default=0)
    estado         = models.CharField(max_length=30, choices=ESTADOS, default='EN_EVALUACION')
    fecha_solicitud= models.DateTimeField(auto_now_add=True)
    observaciones  = models.TextField(blank=True, default='')

    def calcular_cuota_mensual(self):
        """
        Sistema francés (cuota fija): M = P * [r(1+r)^n] / [(1+r)^n - 1]
        Convierte la TEA a Tasa Efectiva Mensual (TEM): r = (1 + TEA)^(1/12) - 1
        """
        tea = float(self.tasa_interes)
        n = self.cuotas
        if tea == 0:
            return self.monto / n
        # Conversión TEA -> TEM
        tasa_mensual = (1 + tea) ** (1/12) - 1
        factor = (1 + tasa_mensual) ** n
        cuota = float(self.monto) * (tasa_mensual * factor) / (factor - 1)
        
        # Seguros fijos mensuales (aprox)
        seguro_desgravamen = float(self.monto) * 0.000746 if self.incluye_desgravamen else 0
        seguro_multiriesgo = float(self.monto) * 0.000916 if self.incluye_multiriesgo else 0
        
        cuota_total = cuota + seguro_desgravamen + seguro_multiriesgo
        return Decimal(str(round(cuota_total, 2)))

    def progreso_pago(self):
        if self.cuotas == 0:
            return 0
        return int((self.cuotas_pagadas / self.cuotas) * 100)

    def generar_cronograma(self):
        """
        Genera el cronograma de pagos utilizando el sistema francés.
        Retorna una lista de diccionarios con el detalle de cada cuota.
        """
        cronograma = []
        saldo = float(self.monto)
        tea = float(self.tasa_interes)
        n = self.cuotas
        
        if tea == 0:
            cuota = saldo / n
            for i in range(1, n + 1):
                cronograma.append({
                    'numero': i,
                    'saldo_inicial': Decimal(str(round(saldo, 2))),
                    'capital': Decimal(str(round(cuota, 2))),
                    'interes': Decimal('0.00'),
                    'cuota': Decimal(str(round(cuota, 2))),
                    'saldo_final': Decimal(str(round(max(0, saldo - cuota), 2))),
                    'estado': 'PAGADO' if i <= self.cuotas_pagadas else 'PENDIENTE'
                })
                saldo -= cuota
            return cronograma

        tasa_mensual = (1 + tea) ** (1/12) - 1
        factor = (1 + tasa_mensual) ** n
        cuota_pura = saldo * (tasa_mensual * factor) / (factor - 1)
        
        seguro_desgravamen = float(self.monto) * 0.000746 if self.incluye_desgravamen else 0
        seguro_multiriesgo = float(self.monto) * 0.000916 if self.incluye_multiriesgo else 0
        
        cuota_total = cuota_pura + seguro_desgravamen + seguro_multiriesgo
        cuota_decimal = round(cuota_total, 2)

        from datetime import timedelta
        fecha_pago = self.fecha_solicitud.date() if self.fecha_solicitud else None

        for i in range(1, n + 1):
            interes = saldo * tasa_mensual
            capital = cuota_pura - interes
            
            # Ajuste en la última cuota para evitar centavos de diferencia
            if i == n:
                capital = saldo
                cuota_total = capital + interes + seguro_desgravamen + seguro_multiriesgo
                cuota_decimal = round(cuota_total, 2)
            
            saldo_final = saldo - capital
            if fecha_pago:
                fecha_pago += timedelta(days=30)
                
            cronograma.append({
                'numero': i,
                'fecha_vencimiento': fecha_pago,
                'saldo_inicial': Decimal(str(round(saldo, 2))),
                'capital': Decimal(str(round(capital, 2))),
                'interes': Decimal(str(round(interes, 2))),
                'seguro_desgravamen': Decimal(str(round(seguro_desgravamen, 2))),
                'seguro_multiriesgo': Decimal(str(round(seguro_multiriesgo, 2))),
                'cuota': Decimal(str(cuota_decimal)),
                'saldo_final': Decimal(str(round(max(0, saldo_final), 2))),
                'estado': 'PAGADO' if i <= self.cuotas_pagadas else 'PENDIENTE'
            })
            saldo = saldo_final
            
        return cronograma

    @property
    def cuotas_restantes(self):
        return self.cuotas - self.cuotas_pagadas

    @property
    def valor_rds(self):
        if self.cliente.ingresos == 0:
            return Decimal('100')
        return (self.cuota_mensual / self.cliente.ingresos) * Decimal('100')

    @property
    def semaforo_rds(self):
        rds = self.valor_rds
        if rds <= Decimal('30'):
            return 'VERDE'
        elif rds <= Decimal('50'):
            return 'AMARILLO'
        else:
            return 'ROJO'

    @property
    def elegibilidad(self):
        score_color = self.cliente.semaforo_crediticio
        rds_color = self.semaforo_rds

        if score_color == 'VERDE' and rds_color == 'VERDE':
            return 'APROBABLE'
        elif score_color == 'ROJO' or rds_color == 'ROJO':
            return 'NO APROBABLE'
        else:
            return 'OBSERVADO'

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


class HistorialAprobacion(models.Model):
    credito = models.ForeignKey(Credito, on_delete=models.CASCADE, related_name='historial_aprobaciones')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    rol = models.CharField(max_length=20)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField()
    estado_anterior = models.CharField(max_length=30)
    estado_nuevo = models.CharField(max_length=30)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.credito.id} - {self.estado_anterior} -> {self.estado_nuevo} ({self.rol})"
