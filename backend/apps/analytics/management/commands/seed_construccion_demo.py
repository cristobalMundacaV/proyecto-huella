from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.analytics.models import (
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    MaterialConstruccion,
    Obra,
    RegistroEmision,
    TransporteObra,
)


class Command(BaseCommand):
    help = "Crea datos demo de construccion para Carbono Zero."

    def handle(self, *args, **options):
        constructora, _ = Constructora.objects.update_or_create(
            constructora_id="CONSTRUCTORA_ANDINA",
            defaults={
                "nombre": "Constructora Andina SpA",
                "rut": "76.123.456-7",
                "region": "Biobio",
                "comuna": "Concepcion",
                "direccion": "Av. Los Carrera 1200",
                "rubro": "Construccion",
                "email": "operaciones@constructoraandina.cl",
                "telefono": "+56 41 222 0000",
                "contacto": "Equipo de sostenibilidad",
            },
        )

        etapas_data = [
            ("ETAPA_EXCAVACION", "Excavacion y movimiento de tierra", EtapaObra.Tipo.EXCAVACION),
            ("ETAPA_FUNDACIONES", "Fundaciones", EtapaObra.Tipo.FUNDACIONES),
            ("ETAPA_OBRA_GRUESA", "Obra gruesa", EtapaObra.Tipo.OBRA_GRUESA),
            ("ETAPA_INSTALACIONES", "Instalaciones", EtapaObra.Tipo.INSTALACIONES),
            ("ETAPA_TERMINACIONES", "Terminaciones", EtapaObra.Tipo.TERMINACIONES),
            ("ETAPA_RETIRO_RESIDUOS", "Retiro de residuos", EtapaObra.Tipo.RETIRO_RESIDUOS),
        ]
        etapas = {}
        for etapa_id, nombre, tipo in etapas_data:
            etapa, _ = EtapaObra.objects.update_or_create(
                etapa_id=etapa_id,
                defaults={
                    "constructora": constructora,
                    "nombre": nombre,
                    "tipo": tipo,
                    "region": "Biobio",
                    "comuna": "Concepcion",
                    "estado": EtapaObra.Estado.ACTIVA,
                    "activa": True,
                },
            )
            etapas[nombre] = etapa

        obra, _ = Obra.objects.update_or_create(
            codigo_obra="OBRA_LOS_ROBLES",
            defaults={
                "constructora": constructora,
                "etapa_principal": etapas["Obra gruesa"],
                "nombre": "Edificio Habitacional Los Robles",
                "tipo_proyecto": Obra.TipoProyecto.EDIFICIO,
                "fecha_inicio": "2026-01-15",
                "fecha_termino_estimada": "2027-03-30",
                "superficie_m2": Decimal("4800"),
                "ubicacion": "Concepcion, Biobio",
                "region": "Biobio",
                "comuna": "Concepcion",
                "mandante": "Inmobiliaria Los Robles",
                "estado": Obra.Estado.EN_EJECUCION,
                "descripcion": "Proyecto demo para medicion de huella de carbono en obra.",
            },
        )

        factores_data = [
            ("Hormigon H30", "Materiales", "m3", "320.000000", "Base demo construccion", 2026),
            ("Cemento", "Materiales", "ton", "735.000000", "Base demo construccion", 2026),
            ("Acero estructural", "Materiales", "ton", "1850.000000", "Base demo construccion", 2026),
            ("Aridos", "Materiales", "ton", "4.000000", "Base demo construccion", 2026),
            ("Diesel maquinaria", "Maquinaria", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Electricidad de faena", "Energia", "kWh", "0.390000", "Base demo construccion", 2026),
            ("Generador diesel", "Energia", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Residuos mixtos", "Residuos", "ton", "120.000000", "Base demo construccion", 2026),
            ("Yeso-carton", "Materiales", "m2", "2.500000", "Base demo construccion", 2026),
            ("Transporte camion", "Transporte", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Escombros", "Residuos", "ton", "35.000000", "Base demo construccion", 2026),
        ]
        for actividad, categoria, unidad, factor, fuente, anio in factores_data:
            FactorEmision.objects.update_or_create(
                actividad=actividad,
                unidad=unidad,
                fuente=fuente,
                anio=anio,
                defaults={
                    "categoria": categoria,
                    "factor_emision": Decimal(factor),
                    "alcance": "Construccion",
                    "descripcion": "Factor demo inicial para registros de obra.",
                },
            )
            MaterialConstruccion.objects.update_or_create(
                nombre=actividad,
                defaults={
                    "categoria": categoria,
                    "unidad_default": unidad,
                    "factor_emision_default": Decimal(factor),
                    "fuente": fuente,
                    "anio": anio,
                },
            )

        registros_data = [
            ("Hormigon H30", "Materiales", etapas["Fundaciones"], Decimal("120"), "m3", Decimal("320.000000"), "2026-02-10"),
            ("Acero estructural", "Materiales", etapas["Obra gruesa"], Decimal("28"), "ton", Decimal("1850.000000"), "2026-02-18"),
            ("Aridos", "Materiales", etapas["Fundaciones"], Decimal("240"), "ton", Decimal("4.000000"), "2026-02-12"),
            ("Cemento", "Materiales", etapas["Fundaciones"], Decimal("18"), "ton", Decimal("735.000000"), "2026-02-11"),
            ("Transporte de aridos", "Transporte", etapas["Fundaciones"], Decimal("180"), "litros diesel", Decimal("2.680000"), "2026-02-12"),
            ("Transporte de hormigon", "Transporte", etapas["Fundaciones"], Decimal("95"), "litros diesel", Decimal("2.680000"), "2026-02-13"),
            ("Excavadora diesel", "Maquinaria", etapas["Excavacion y movimiento de tierra"], Decimal("420"), "litros diesel", Decimal("2.680000"), "2026-02-05"),
            ("Retroexcavadora", "Maquinaria", etapas["Excavacion y movimiento de tierra"], Decimal("140"), "litros diesel", Decimal("2.680000"), "2026-02-07"),
            ("Electricidad de faena", "Energia", etapas["Instalaciones"], Decimal("1600"), "kWh", Decimal("0.390000"), "2026-03-01"),
            ("Generador diesel", "Energia", etapas["Obra gruesa"], Decimal("260"), "litros diesel", Decimal("2.680000"), "2026-03-05"),
            ("Residuos mixtos", "Residuos", etapas["Retiro de residuos"], Decimal("8"), "ton", Decimal("120.000000"), "2026-03-12"),
            ("Yeso-carton", "Materiales", etapas["Terminaciones"], Decimal("900"), "m2", Decimal("2.500000"), "2026-03-20"),
            ("Retiro de escombros", "Residuos", etapas["Retiro de residuos"], Decimal("18"), "ton", Decimal("35.000000"), "2026-03-22"),
        ]
        RegistroEmision.objects.filter(obra=obra).delete()
        registros = {}
        for fuente, categoria, etapa, cantidad, unidad, factor, fecha in registros_data:
            registros[fuente] = RegistroEmision.objects.create(
                obra=obra,
                etapa=etapa,
                categoria=categoria,
                fuente_emision=fuente,
                cantidad=cantidad,
                unidad=unidad,
                factor_emision=factor,
                fecha=fecha,
                proveedor="Proveedor demo",
            )

        TransporteObra.objects.filter(obra=obra).delete()
        TransporteObra.objects.create(
            obra=obra,
            etapa=etapas["Fundaciones"],
            vehiculo="Camion mixer",
            patente="ABCD12",
            origen="Planta hormigon Bio Bio",
            destino="Edificio Habitacional Los Robles",
            distancia_km=Decimal("28"),
            consumo_estimado_litro_km=Decimal("0.3800"),
            fecha_hora="2026-02-13T08:30:00Z",
        )

        EvidenciaObra.objects.filter(obra=obra).delete()
        evidencias_data = [
            ("Factura hormigon H30", EvidenciaObra.TipoEvidencia.FACTURA_MATERIAL, registros["Hormigon H30"]),
            ("Guia despacho aridos", EvidenciaObra.TipoEvidencia.GUIA_DESPACHO, registros["Aridos"]),
            ("Factura combustible maquinaria", EvidenciaObra.TipoEvidencia.FACTURA_COMBUSTIBLE, registros["Excavadora diesel"]),
            ("Boleta electrica faena", EvidenciaObra.TipoEvidencia.BOLETA_ELECTRICA, registros["Electricidad de faena"]),
            ("Ticket pesaje residuos", EvidenciaObra.TipoEvidencia.TICKET_PESAJE, registros["Residuos mixtos"]),
            ("Registro retiro de escombros", EvidenciaObra.TipoEvidencia.REGISTRO_RESIDUOS, registros["Retiro de escombros"]),
        ]
        for nombre, tipo, registro in evidencias_data:
            EvidenciaObra.objects.create(
                constructora=constructora,
                obra=obra,
                etapa=registro.etapa,
                registro_emision=registro,
                tipo_evidencia=tipo,
                estado_documental=EvidenciaObra.EstadoDocumental.VALIDADA,
                fecha_documento=registro.fecha,
                archivo="evidencias/demo/documento_demo.pdf",
                nombre=nombre,
                observaciones="Evidencia demo de construccion.",
            )

        self.stdout.write(self.style.SUCCESS("Datos demo de construccion creados correctamente."))
