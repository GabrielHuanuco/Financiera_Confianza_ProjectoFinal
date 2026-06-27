from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from authentication.models import Cliente
from ahorros.models import CuentaAhorro
from creditos.models import Credito, PagoCuota
from core_bancario.models import EstadoMora, GestionCobranza, Movimiento
from decimal import Decimal
from django.db import transaction
import uuid, random
from datetime import timedelta
from django.utils import timezone

NOMBRES = [
    ("Carlos","Quispe Mamani"),("Maria","Lopez Flores"),("Juan","Garcia Torres"),
    ("Ana","Rodriguez Silva"),("Luis","Martinez Vega"),("Rosa","Huanca Condori"),
    ("Pedro","Ccopa Ticona"),("Elena","Vargas Paredes"),("Jorge","Mendoza Cruz"),
    ("Sofia","Paucar Ramos"),("Ricardo","Chavez Lima"),("Lucia","Apaza Mamani"),
    ("Miguel","Quispe Cardenas"),("Patricia","Torres Huanca"),("Fernando","Salinas Diaz"),
    ("Carmen","Benitez Rojas"),("Raul","Flores Pacheco"),("Veronica","Soto Alvarado"),
    ("David","Inca Pillco"),("Margarita","Ccorimanya Huallpa"),("Roberto","Puma Quispe"),
    ("Isabel","Lazo Condori"),("Cesar","Huanca Yupanqui"),("Sandra","Mamani Ticona"),
    ("Arturo","Ccoa Apaza"),("Natalia","Ramos Velarde"),("Gustavo","Pinas Choque"),
    ("Diana","Maquera Luque"),("Hector","Quispe Cutipa"),("Claudia","Ayala Calsina"),
    ("Andres","Vilca Condori"),("Paola","Zevallos Mamani"),("Sergio","Huayta Quispe"),
    ("Viviana","Ccallo Torres"),("Eduardo","Limachi Paucara"),("Gabriela","Turpo Cruz"),
    ("Alfredo","Sucasaca Mamani"),("Monica","Aguilar Pari"),("Ernesto","Carpio Flores"),
    ("Karina","Quispe Huanca"),("Oswaldo","Cano Ccoa"),("Milagros","Villanueva Apaza"),
    ("Benjamin","Sanca Puma"),("Vanessa","Coyla Ticona"),("Oscar","Medina Cutipa"),
    ("Silvia","Butron Mamani"),("Felix","Ayala Luque"),("Jaqueline","Cari Quispe"),
    ("Gonzalo","Lara Valdivia"),("Adriana","Mamani Condori"),("Julio","Herrera Alca"),
    ("Roxana","Ccorimanya Cari"),("Manuel","Paucar Ticona"),("Fabiola","Quispe Ramos"),
    ("Enrique","Chura Ccoa"),("Liliana","Huanca Pillco"),("Antonio","Mamani Puma"),
    ("Yessica","Zeballos Luque"),("Hugo","Ticona Ccallo"),("Lorena","Apaza Cruz"),
    ("Ramon","Flores Huanca"),("Esther","Cano Condori"),("Victor","Quispe Maquera"),
    ("Norma","Turpo Mamani"),("Elias","Pari Ayala"),("Irene","Carpio Quispe"),
    ("Dario","Ccoa Villanueva"),("Consuelo","Mamani Sanca"),("Renato","Lima Zevallos"),
    ("Beatriz","Coyla Medina"),("Ivan","Butron Silva"),("Esperanza","Quispe Felix"),
    ("Gilberto","Cari Gonzalo"),("Roxanne","Lara Adriana"),("Javier","Herrera Julio"),
    ("Amelia","Ccori Mamani"),("Tomas","Huanca Paucar"),("Grecia","Ramos Enrique"),
    ("Marco","Chura Vilca"),("Pilar","Mamani Zevallos"),("Nicolas","Zeballos Hugo"),
    ("Alejandra","Ticona Lorena"),("Ignacio","Apaza Ramon"),("Susana","Flores Esther"),
    ("Adolfo","Cano Victor"),("Rebeca","Quispe Norma"),("Cristian","Turpo Elias"),
    ("Marlene","Pari Irene"),("Teodoro","Carpio Dario"),("Celeste","Ccoa Consuelo"),
    ("Wilmer","Mamani Renato"),("Nadia","Lima Beatriz"),("Humberto","Coyla Ivan"),
    ("Jacinta","Butron Esperanza"),("Rolando","Quispe Gilberto"),("Zoila","Cari Roxanne"),
    ("OswaldoB","Herrera Marco"),("Wendy","Mamani Tomas"),("Fredy","Chura Alejandra"),
]

DIRECCIONES = [
    "Av El Sol 234 Cusco","Jr Puno 456 Arequipa","Calle Lima 789 Trujillo",
    "Av Grau 321 Piura","Jr Ayacucho 654 Ica","Av Tacna 987 Tacna",
    "Calle Moquegua 111","Jr Loreto 222 Iquitos","Av Cajamarca 333",
    "Jr Huancayo 444","Calle Ancash 555 Huaraz","Av Junin 666 Pasco",
    "Jr Madre de Dios 777","Av Ucayali 888 Pucallpa","Calle San Martin 999",
    "Av Amazonas 100","Jr Lambayeque 200 Chiclayo","Calle La Libertad 300",
    "Av Tumbes 400","Jr Apurimac 500 Abancay",
]

TIPOS_CUENTA = ["Ahorro Clasico","Ahorro Plus","Ahorro Joven","Ahorro Empresarial"]
TIPOS_CREDITO = ["Personal","Vehicular","Hipotecario","Negocio","Microempresa"]

TASAS = {
    "Personal":Decimal("0.18"),"Vehicular":Decimal("0.14"),
    "Hipotecario":Decimal("0.10"),"Negocio":Decimal("0.20"),
    "Microempresa":Decimal("0.4392"),
}
MONTOS = {
    "Personal":(3000,30000),"Vehicular":(15000,80000),
    "Hipotecario":(80000,300000),"Negocio":(5000,50000),"Microempresa":(1000,15000),
}
CUOTAS = {
    "Personal":[12,18,24,36],"Vehicular":[24,36,48,60],
    "Hipotecario":[60,84,120,180],"Negocio":[12,18,24,36],"Microempresa":[6,9,12,18],
}
COMENTARIOS = [
    "Cliente informa tramite de liquidacion laboral.",
    "No contesta. Se dejo mensaje de voz.",
    "Cliente comprometido a pagar la proxima semana.",
    "Visita domiciliaria realizada, cliente ausente.",
    "Cliente solicita reprogramacion de deuda.",
    "Acuerdo parcial, pagara 500 soles semanales.",
    "Cliente informa perdida temporal de empleo.",
    "Se envio correo de recordatorio de pago.",
    "Cliente prometio pago para el dia 15.",
    "Numero de telefono no disponible.",
    "Cliente realizo pago parcial de 300 soles.",
    "Notificado por carta notarial.",
    "Vecino informo que cliente viajo al interior.",
    "Cliente en proceso de venta de inmueble.",
    "Sin contacto por segunda vez consecutiva.",
]


class Command(BaseCommand):
    help = "Puebla la BD con 100 clientes y creditos variados con moras relacionadas."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Eliminar datos seed previos")

    def handle(self, *args, **options):
        self.stdout.write("Iniciando poblamiento de datos...")
        random.seed(42)
        creados = 0
        saltados = 0
        errores = 0

        if options.get("reset"):
            deleted = User.objects.filter(username__startswith="cliente_").delete()
            self.stdout.write("Reset: {} registros eliminados.".format(deleted[0]))

        for i, (nombre, apellidos) in enumerate(NOMBRES, start=1):
            username = "cliente_{:03d}".format(i)
            dni = "4{:07d}".format(i)

            try:
                with transaction.atomic():
                    rnd = random.random()
                    if rnd < 0.30:
                        score = random.randint(700, 850)
                    elif rnd < 0.70:
                        score = random.randint(500, 699)
                    else:
                        score = random.randint(280, 499)

                    ingresos = Decimal(str(random.randint(1200, 12000)))

                    user, u_created = User.objects.get_or_create(
                        username=username,
                        defaults=dict(
                            email=username + "_test@financiera.pe",
                            first_name=nombre,
                            last_name=apellidos,
                        )
                    )
                    if u_created:
                        user.set_password("testpassword123")
                        user.save()

                    if hasattr(user, 'cliente'):
                        saltados += 1
                        continue

                    cliente = Cliente.objects.create(
                        usuario=user,
                        uid=uuid.uuid4(),
                        telefono="9" + str(random.randint(10000000, 99999999)),
                        dni=dni,
                        direccion=random.choice(DIRECCIONES),
                        ingresos=ingresos,
                        score_crediticio=score,
                        estado=True,
                        rol="CLIENTE",
                    )

                    saldo_inicial = Decimal(str(random.randint(200, 20000)))
                    cuenta = CuentaAhorro.objects.create(
                        cliente=cliente,
                        numero_cuenta="194-{:05d}-{}".format(i, random.randint(10, 99)),
                        tipo_cuenta=random.choice(TIPOS_CUENTA),
                        saldo=saldo_inicial,
                        estado="ACTIVA",
                    )

                    for _ in range(random.randint(2, 5)):
                        tipo_mov = random.choice(["DEPOSITO", "RETIRO"])
                        monto_mov = Decimal(str(random.randint(100, 2000)))
                        if tipo_mov == 'RETIRO' and monto_mov > cuenta.saldo:
                            monto_mov = max(Decimal('1'), cuenta.saldo // 2)
                        if tipo_mov == 'DEPOSITO':
                            cuenta.saldo += monto_mov
                        else:
                            cuenta.saldo -= monto_mov
                        cuenta.save()
                        Movimiento.objects.create(
                            cuenta=cuenta,
                            tipo_operacion=tipo_mov,
                            monto=monto_mov,
                            saldo_resultante=cuenta.saldo,
                            descripcion='Deposito en ventanilla' if tipo_mov == 'DEPOSITO' else 'Retiro en ventanilla',
                        )

                    rnd2 = random.random()
                    if rnd2 < 0.20:
                        num_creditos = 0
                    elif rnd2 < 0.70:
                        num_creditos = 1
                    else:
                        num_creditos = 2

                    for j in range(num_creditos):
                        tipo = random.choice(TIPOS_CREDITO)
                        tasa = TASAS[tipo]
                        mmin, mmax = MONTOS[tipo]
                        monto = Decimal(str(random.randrange(mmin, mmax, 500)))
                        cuotas = random.choice(CUOTAS[tipo])
                        tea = float(tasa)
                        tm = (1 + tea) ** (1 / 12) - 1
                        factor = (1 + tm) ** cuotas
                        cuota_mensual = Decimal(str(round(float(monto) * (tm * factor) / (factor - 1), 2)))

                        estados_pool = (
                            ["DESEMBOLSADO"] * 45 + ["PAGADO"] * 20 + ["EN_EVALUACION"] * 10 +
                            ["EN_RIESGOS"] * 8 + ["EN_COMITE"] * 7 + ["APROBADO"] * 5 + ["RECHAZADO"] * 5
                        )
                        estado_credito = random.choice(estados_pool)

                        if estado_credito == "PAGADO":
                            cuotas_pagadas = cuotas
                            saldo_pendiente = Decimal("0.00")
                        elif estado_credito == "DESEMBOLSADO":
                            cuotas_pagadas = random.randint(0, cuotas - 1)
                            saldo_pendiente = cuota_mensual * (cuotas - cuotas_pagadas)
                        else:
                            cuotas_pagadas = 0
                            saldo_pendiente = cuota_mensual * cuotas

                        credito = Credito.objects.create(
                            cliente=cliente, tipo_credito=tipo, monto=monto,
                            cuotas=cuotas, tasa_interes=tasa, cuota_mensual=cuota_mensual,
                            saldo_pendiente=saldo_pendiente, cuotas_pagadas=cuotas_pagadas,
                            estado=estado_credito,
                        )

                        if cuotas_pagadas > 0 and estado_credito in ("DESEMBOLSADO", "PAGADO"):
                            saldo_tmp = cuota_mensual * cuotas
                            for k in range(1, cuotas_pagadas + 1):
                                saldo_tmp -= cuota_mensual
                                PagoCuota.objects.create(
                                    credito=credito, numero_cuota=k,
                                    monto_pagado=cuota_mensual,
                                    saldo_tras_pago=max(Decimal("0"), saldo_tmp),
                                )

                        if estado_credito == "DESEMBOLSADO":
                            cuotas_sin_pagar = cuotas - cuotas_pagadas
                            prob_mora = 0.0
                            if score < 400:
                                prob_mora = 0.70
                            elif score < 500:
                                prob_mora = 0.50
                            elif score < 600:
                                prob_mora = 0.25
                            elif score < 700:
                                prob_mora = 0.10
                            else:
                                prob_mora = 0.03
                            if cuotas_sin_pagar > cuotas * 0.5:
                                prob_mora += 0.15

                            en_mora = random.random() < prob_mora
                            if en_mora:
                                br = random.random()
                                if br < 0.35:
                                    dias_mora = random.randint(1, 8)
                                    banda = "PREVENTIVA"
                                elif br < 0.60:
                                    dias_mora = random.randint(9, 30)
                                    banda = "TEMPRANA"
                                elif br < 0.78:
                                    dias_mora = random.randint(31, 60)
                                    banda = "INTERMEDIA"
                                elif br < 0.90:
                                    dias_mora = random.randint(61, 90)
                                    banda = "TARDIA"
                                elif br < 0.96:
                                    dias_mora = random.randint(91, 180)
                                    banda = "JUDICIAL"
                                else:
                                    dias_mora = random.randint(181, 365)
                                    banda = "CASTIGO"

                                credito.fecha_solicitud = timezone.now() - timedelta(days=dias_mora + cuotas_pagadas * 30)
                                credito.save()

                                if banda == "JUDICIAL":
                                    try:
                                        EstadoMora.objects.create(
                                            credito=credito,
                                            estado="JUDICIAL",
                                            observacion="Derivado a legal tras {} dias de mora.".format(dias_mora),
                                        )
                                    except Exception:
                                        pass
                                elif banda == "CASTIGO":
                                    try:
                                        EstadoMora.objects.create(
                                            credito=credito,
                                            estado="CASTIGO",
                                            observacion="Cartera castigada tras {} dias.".format(dias_mora),
                                        )
                                    except Exception:
                                        pass

                                num_gest = min(4, max(1, dias_mora // 15))
                                resultados = ["LLAMADA","PROMESA_PAGO","CORREO","VISITA",
                                              "SIN_CONTACTO","PAGO_PARCIAL","ACUERDO_PAGO"]
                                for _ in range(num_gest):
                                    GestionCobranza.objects.create(
                                        credito=credito,
                                        usuario=None,
                                        rol="RECUPERACIONES",
                                        comentario=random.choice(COMENTARIOS),
                                        resultado=random.choice(resultados),
                                        dias_mora_snapshot=dias_mora,
                                        banda_mora_snapshot=banda,
                                    )

                    creados += 1

            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR("  ERROR {}: {}".format(username, str(e)[:100])))

        self.stdout.write(self.style.SUCCESS(
            "Datos poblados correctamente. Creados={} Saltados={} Errores={}".format(creados, saltados, errores)
        ))
