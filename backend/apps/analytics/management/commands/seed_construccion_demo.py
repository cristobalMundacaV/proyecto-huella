from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import (
    Organizacion,
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
        organizacion, _ = Organizacion.objects.update_or_create(
            organizacion_id="ORGANIZACION_ANDINA",
            defaults={
                "nombre": "Organizacion Andina SpA",
                "rut": "76.123.456-7",
                "region": "Biobio",
                "comuna": "Concepcion",
                "direccion": "Av. Los Carrera 1200",
                "rubro": "Construccion",
                "email": "operaciones@organizacionandina.cl",
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
                    "organizacion": organizacion,
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
                "organizacion": organizacion,
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
            ("Retiro de escombros", "Residuos", "ton", "35.000000", "Base demo construccion", 2026),
            ("Transporte de aridos", "Transporte", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Transporte de hormigon", "Transporte", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Excavadora diesel", "Maquinaria", "litros diesel", "2.680000", "Base demo construccion", 2026),
            ("Retroexcavadora", "Maquinaria", "litros diesel", "2.680000", "Base demo construccion", 2026),
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

        registros_template = [
            ("Hormigon H30", "Materiales", etapas["Fundaciones"], Decimal("8.5"), "m3", Decimal("320.000000")),
            ("Cemento", "Materiales", etapas["Fundaciones"], Decimal("1.4"), "ton", Decimal("735.000000")),
            ("Aridos", "Materiales", etapas["Fundaciones"], Decimal("18"), "ton", Decimal("4.000000")),
            ("Transporte de aridos", "Transporte", etapas["Fundaciones"], Decimal("21"), "litros diesel", Decimal("2.680000")),
            ("Transporte de hormigon", "Transporte", etapas["Fundaciones"], Decimal("16"), "litros diesel", Decimal("2.680000")),
            ("Acero estructural", "Materiales", etapas["Obra gruesa"], Decimal("2.2"), "ton", Decimal("1850.000000")),
            ("Generador diesel", "Energia", etapas["Obra gruesa"], Decimal("58"), "litros diesel", Decimal("2.680000")),
            ("Excavadora diesel", "Maquinaria", etapas["Excavacion y movimiento de tierra"], Decimal("72"), "litros diesel", Decimal("2.680000")),
            ("Retroexcavadora", "Maquinaria", etapas["Excavacion y movimiento de tierra"], Decimal("38"), "litros diesel", Decimal("2.680000")),
            ("Electricidad de faena", "Energia", etapas["Instalaciones"], Decimal("260"), "kWh", Decimal("0.390000")),
            ("Yeso-carton", "Materiales", etapas["Terminaciones"], Decimal("110"), "m2", Decimal("2.500000")),
            ("Residuos mixtos", "Residuos", etapas["Retiro de residuos"], Decimal("1.2"), "ton", Decimal("120.000000")),
            ("Retiro de escombros", "Residuos", etapas["Retiro de residuos"], Decimal("2.6"), "ton", Decimal("35.000000")),
        ]

        RegistroEmision.objects.filter(obra=obra).delete()
        registros = {}
        start_date = timezone.localdate() - timedelta(days=179)

        for day_index in range(180):
            fuente, categoria, etapa, cantidad_base, unidad, factor = registros_template[day_index % len(registros_template)]
            current_date = start_date + timedelta(days=day_index)
            month_pressure = Decimal("1") + Decimal(str((current_date.month % 4) * 0.05))
            weekly_pressure = Decimal("0.92") + Decimal(str((day_index % 7) * 0.025))
            stage_pressure = Decimal("1.12") if etapa.nombre in {"Fundaciones", "Obra gruesa"} else Decimal("0.88")
            cantidad = (cantidad_base * month_pressure * weekly_pressure * stage_pressure).quantize(Decimal("0.001"))

            registro = RegistroEmision.objects.create(
                obra=obra,
                etapa=etapa,
                categoria=categoria,
                fuente_emision=fuente,
                cantidad=cantidad,
                unidad=unidad,
                factor_emision=factor,
                fecha=current_date,
                proveedor="Proveedor demo",
                observaciones="Registro demo generado para poblar 180 dias de evolucion mensual.",
            )
            registros.setdefault(fuente, registro)

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
            ("Factura hormigon H30", EvidenciaObra.TipoEvidencia.FACTURA_MATERIAL, "Hormigon H30"),
            ("Guia despacho aridos", EvidenciaObra.TipoEvidencia.GUIA_DESPACHO, "Aridos"),
            ("Factura combustible maquinaria", EvidenciaObra.TipoEvidencia.FACTURA_COMBUSTIBLE, "Excavadora diesel"),
            ("Boleta electrica faena", EvidenciaObra.TipoEvidencia.BOLETA_ELECTRICA, "Electricidad de faena"),
            ("Ticket pesaje residuos", EvidenciaObra.TipoEvidencia.TICKET_PESAJE, "Residuos mixtos"),
            ("Registro retiro de escombros", EvidenciaObra.TipoEvidencia.REGISTRO_RESIDUOS, "Retiro de escombros"),
            ("Certificado acero estructural", EvidenciaObra.TipoEvidencia.FACTURA_MATERIAL, "Acero estructural"),
            ("Control generador diesel", EvidenciaObra.TipoEvidencia.FACTURA_COMBUSTIBLE, "Generador diesel"),
            ("Respaldo transporte hormigon", EvidenciaObra.TipoEvidencia.GUIA_DESPACHO, "Transporte de hormigon"),
        ]
        for nombre, tipo, fuente in evidencias_data:
            registro = registros.get(fuente)
            if not registro:
                continue

            EvidenciaObra.objects.create(
                organizacion=organizacion,
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

        self.stdout.write(
            self.style.SUCCESS(
                "Datos demo de construccion creados correctamente con 180 dias de registros de emision."
            )
        )
