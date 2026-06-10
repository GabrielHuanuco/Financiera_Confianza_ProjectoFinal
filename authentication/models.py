from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):

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

    def __str__(self):
        return self.usuario.username