# Migración manual — agrega campos financieros a Credito y crea PagoCuota

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('creditos', '0001_initial'),
    ]

    operations = [
        # Nuevos campos en Credito
        migrations.AddField(
            model_name='credito',
            name='tasa_interes',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.18'), max_digits=5),
        ),
        migrations.AddField(
            model_name='credito',
            name='cuota_mensual',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AddField(
            model_name='credito',
            name='saldo_pendiente',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12),
        ),
        migrations.AddField(
            model_name='credito',
            name='cuotas_pagadas',
            field=models.IntegerField(default=0),
        ),
        # Actualizar choices de estado para incluir PAGADO
        migrations.AlterField(
            model_name='credito',
            name='estado',
            field=models.CharField(
                choices=[
                    ('EN_EVALUACION', 'En Evaluación'),
                    ('APROBADO',      'Aprobado'),
                    ('DESEMBOLSADO',  'Desembolsado'),
                    ('PAGADO',        'Pagado'),
                    ('RECHAZADO',     'Rechazado'),
                ],
                default='EN_EVALUACION',
                max_length=30,
            ),
        ),
        # Nuevo modelo PagoCuota
        migrations.CreateModel(
            name='PagoCuota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_cuota', models.IntegerField()),
                ('monto_pagado', models.DecimalField(decimal_places=2, max_digits=12)),
                ('saldo_tras_pago', models.DecimalField(decimal_places=2, max_digits=12)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('credito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos', to='creditos.credito')),
            ],
        ),
    ]
