from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Cliente(models.Model):

    ROLES_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('ASESOR', 'Asesor'),
        ('RIESGOS', 'Riesgos'),
        ('COMITE', 'Comité'),
        ('GERENCIA', 'Gerencia'),
        ('ADMIN', 'Admin'),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    uid = models.UUIDField(
        unique=True
    )

    telefono = models.CharField(max_length=20)

    direccion = models.TextField()

    dni = models.CharField(
        max_length=20,
        unique=True
    )

    ingresos = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    score_crediticio = models.IntegerField(default=0)

    estado = models.BooleanField(default=True)

    rol = models.CharField(
        max_length=20, 
        choices=ROLES_CHOICES, 
        default='CLIENTE'
    )

    def __str__(self):
        return self.usuario.username

    @property
    def semaforo_crediticio(self):
        if self.score_crediticio >= 700:
            return 'VERDE'
        elif self.score_crediticio >= 500:
            return 'AMARILLO'
        else:
            return 'ROJO'

    @property
    def ingreso_diario(self):
        """Promedio diario de ingreso (asumiendo 30 días al mes)."""
        if not self.ingresos:
            return Decimal('0.00')
        return (self.ingresos / Decimal('30')).quantize(Decimal('0.01'))