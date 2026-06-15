import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import (
    ConfiguracionConstructora,
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    Obra,
    RegistroEmision,
)

YEAR = timezone.localdate().year
SEED_PREFIX = "CZ_SEED"


PRESET_BLUEPRINTS = {
    "construccion": {
        "constructora_id": "CZ_SEED_CONSTRUCCION",
        "nombre": "Constructora Demo Carbono Zero",
        "rubro": "Construcción",
        "region": "Biobío",
        "comuna": "Los Ángeles",
        "stages": [
            "Excavación y movimiento de tierra",
            "Fundaciones",
            "Obra gruesa",
            "Terminaciones",
            "Retiro de residuos",
        ],
        "units": [
            "Edificio Habitacional Norte",
            "Condominio Sustentable Sur",
            "Centro Comercial Piloto",
        ],
        "sources": [
            {
                "categoria": "Materiales",
                "fuente": "Hormigon H30",
                "unidad": "m3",
                "factor": "310.000000",
                "min": 4,
                "max": 18,
                "weight": 4.5,
                "evidence_type": "factura_material",
                "module": "materiales",
            },
            {
                "categoria": "Materiales",
                "fuente": "Acero de refuerzo",
                "unidad": "ton",
                "factor": "1850.000000",
                "min": 0.05,
                "max": 0.45,
                "weight": 2.5,
                "evidence_type": "factura_material",
                "module": "materiales",
            },
            {
                "categoria": "Transporte",
                "fuente": "Diesel camion obra",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 25,
                "max": 140,
                "weight": 2.2,
                "evidence_type": "factura_combustible",
                "module": "transporte",
            },
            {
                "categoria": "Maquinaria",
                "fuente": "Excavadora diesel",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 18,
                "max": 95,
                "weight": 1.8,
                "evidence_type": "registro_maquinaria",
                "module": "maquinaria",
            },
            {
                "categoria": "Residuos",
                "fuente": "Retiro escombros",
                "unidad": "kg",
                "factor": "0.080000",
                "min": 300,
                "max": 1800,
                "weight": 1.2,
                "evidence_type": "registro_retiro_residuos",
                "module": "residuos",
            },
        ],
    },
    "aserradero": {
        "constructora_id": "CZ_SEED_ASERRADERO",
        "nombre": "Aserradero Demo Carbono Zero",
        "rubro": "Forestal / Aserradero",
        "region": "Biobío",
        "comuna": "Los Ángeles",
        "stages": [
            "Recepción de trozas",
            "Producción",
            "Secado",
            "Energía",
            "Transporte forestal",
            "Residuos y subproductos",
        ],
        "units": [
            "Lote Pino Radiata A",
            "Lote Pino Radiata B",
            "Lote Eucalipto C",
        ],
        "sources": [
            {
                "categoria": "Materiales",
                "fuente": "Recepcion de trozas",
                "unidad": "m3",
                "factor": "18.000000",
                "min": 12,
                "max": 75,
                "weight": 2.8,
                "evidence_type": "guia_despacho",
                "module": "recepcion_trozas",
            },
            {
                "categoria": "Energia",
                "fuente": "Electricidad secado kWh",
                "unidad": "kWh",
                "factor": "0.390000",
                "min": 350,
                "max": 2100,
                "weight": 3.8,
                "evidence_type": "boleta_electrica",
                "module": "secado",
            },
            {
                "categoria": "Transporte",
                "fuente": "Diesel transporte forestal",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 35,
                "max": 180,
                "weight": 2.7,
                "evidence_type": "factura_combustible",
                "module": "transporte_forestal",
            },
            {
                "categoria": "Procesos externos",
                "fuente": "Proceso de aserrio",
                "unidad": "m3",
                "factor": "22.000000",
                "min": 8,
                "max": 48,
                "weight": 1.8,
                "evidence_type": "otro",
                "module": "produccion",
            },
            {
                "categoria": "Residuos",
                "fuente": "Residuos y subproductos de madera",
                "unidad": "kg",
                "factor": "0.030000",
                "min": 250,
                "max": 1600,
                "weight": 1.1,
                "evidence_type": "registro_retiro_residuos",
                "module": "residuos_subproductos",
            },
        ],
    },
    "transporte": {
        "constructora_id": "CZ_SEED_TRANSPORTE",
        "nombre": "Transporte Demo Carbono Zero",
        "rubro": "Transporte y logística",
        "region": "Metropolitana",
        "comuna": "Santiago",
        "stages": [
            "Planificación de rutas",
            "Operación de flota",
            "Combustible",
            "Mantenciones",
            "Carga y distribución",
        ],
        "units": [
            "Camión FL-01",
            "Camión FL-02",
            "Camión FL-03",
            "Ruta Centro Sur",
        ],
        "sources": [
            {
                "categoria": "Transporte",
                "fuente": "Diesel camion ruta",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 40,
                "max": 260,
                "weight": 5.0,
                "evidence_type": "factura_combustible",
                "module": "combustible",
            },
            {
                "categoria": "Transporte",
                "fuente": "Ruta larga distancia",
                "unidad": "km",
                "factor": "0.850000",
                "min": 60,
                "max": 520,
                "weight": 3.2,
                "evidence_type": "documento_transporte",
                "module": "rutas",
            },
            {
                "categoria": "Maquinaria",
                "fuente": "Mantencion flota",
                "unidad": "unidad",
                "factor": "35.000000",
                "min": 1,
                "max": 4,
                "weight": 1.0,
                "evidence_type": "otro",
                "module": "mantenciones",
            },
            {
                "categoria": "Energia",
                "fuente": "Electricidad oficina logistica",
                "unidad": "kWh",
                "factor": "0.390000",
                "min": 90,
                "max": 420,
                "weight": 0.8,
                "evidence_type": "boleta_electrica",
                "module": "flota",
            },
        ],
    },
    "industrial": {
        "constructora_id": "CZ_SEED_INDUSTRIAL",
        "nombre": "Industria Demo Carbono Zero",
        "rubro": "Industrial",
        "region": "Biobío",
        "comuna": "Concepción",
        "stages": [
            "Producción",
            "Energía",
            "Caldera",
            "Residuos industriales",
            "Transporte interno",
        ],
        "units": [
            "Línea Producción A",
            "Línea Producción B",
            "Caldera Principal",
            "Bodega Despacho",
        ],
        "sources": [
            {
                "categoria": "Energia",
                "fuente": "Electricidad planta kWh",
                "unidad": "kWh",
                "factor": "0.390000",
                "min": 700,
                "max": 4200,
                "weight": 4.3,
                "evidence_type": "boleta_electrica",
                "module": "energia",
            },
            {
                "categoria": "Energia",
                "fuente": "Diesel caldera",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 55,
                "max": 340,
                "weight": 3.4,
                "evidence_type": "factura_combustible",
                "module": "produccion",
            },
            {
                "categoria": "Residuos",
                "fuente": "Residuo industrial no peligroso",
                "unidad": "kg",
                "factor": "0.120000",
                "min": 400,
                "max": 2600,
                "weight": 1.7,
                "evidence_type": "ticket_pesaje",
                "module": "residuos",
            },
            {
                "categoria": "Agua",
                "fuente": "Consumo agua proceso",
                "unidad": "m3",
                "factor": "0.450000",
                "min": 20,
                "max": 160,
                "weight": 1.2,
                "evidence_type": "otro",
                "module": "agua",
            },
            {
                "categoria": "Transporte",
                "fuente": "Diesel grua interna",
                "unidad": "litros diesel",
                "factor": "2.680000",
                "min": 12,
                "max": 75,
                "weight": 1.0,
                "evidence_type": "factura_combustible",
                "module": "transporte",
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Crea datos QA de 180 días para validar vistas, presets, dashboard, evidencias e inteligencia ambiental."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=180)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--seed", type=int, default=20260615)

    @transaction.atomic
    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        rng = random.Random(options["seed"])

        if options["reset"]:
            self.reset_seed_data()

        totals = {
            "empresas": 0,
            "etapas": 0,
            "unidades": 0,
            "factores": 0,
            "registros": 0,
            "evidencias": 0,
        }

        for preset, blueprint in PRESET_BLUEPRINTS.items():
            result = self.seed_preset(preset, blueprint, days, rng)

            for key, value in result.items():
                totals[key] += value

        self.stdout.write(self.style.SUCCESS("Seed QA Carbono Zero completado."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Empresas: {totals['empresas']} | Etapas: {totals['etapas']} | "
                f"Unidades: {totals['unidades']} | Factores: {totals['factores']} | "
                f"Registros: {totals['registros']} | Evidencias: {totals['evidencias']}"
            )
        )

    def reset_seed_data(self):
        empresas = Constructora.objects.filter(constructora_id__startswith=SEED_PREFIX)

        EvidenciaObra.objects.filter(constructora__in=empresas).delete()
        RegistroEmision.objects.filter(constructora__in=empresas).delete()
        Obra.objects.filter(constructora__in=empresas).delete()
        EtapaObra.objects.filter(constructora__in=empresas).delete()
        ConfiguracionConstructora.objects.filter(constructora__in=empresas).delete()
        deleted_count = empresas.count()
        empresas.delete()

        self.stdout.write(
            self.style.WARNING(f"Datos seed eliminados: {deleted_count} empresas.")
        )

    def seed_preset(self, preset, blueprint, days, rng):
        empresa, empresa_created = Constructora.objects.update_or_create(
            constructora_id=blueprint["constructora_id"],
            defaults={
                "nombre": blueprint["nombre"],
                "rubro": blueprint["rubro"],
                "preset": preset,
                "region": blueprint["region"],
                "comuna": blueprint["comuna"],
                "direccion": "Dirección demo Carbono Zero",
                "email": f"{preset}@carbonozero.demo",
                "telefono": "+56 9 0000 0000",
                "contacto": "Equipo QA Carbono Zero",
                "observaciones": "Empresa creada automáticamente para validar 180 días de operación por preset.",
                "activa": True,
            },
        )
        ConfiguracionConstructora.objects.get_or_create(constructora=empresa)

        etapas = self.create_stages(empresa, blueprint)
        unidades = self.create_units(empresa, etapas, blueprint, preset, days)
        factores = self.create_factors(preset, blueprint)
        registros = self.create_records(
            empresa, etapas, unidades, factores, blueprint, days, rng
        )
        evidencias = self.create_evidences(empresa, registros, preset, rng)

        return {
            "empresas": int(empresa_created),
            "etapas": len(etapas),
            "unidades": len(unidades),
            "factores": len(factores),
            "registros": len(registros),
            "evidencias": evidencias,
        }

    def create_stages(self, empresa, blueprint):
        etapas = []

        for index, name in enumerate(blueprint["stages"], start=1):
            etapa, _ = EtapaObra.objects.update_or_create(
                etapa_id=f"{empresa.constructora_id}_ETAPA_{index:02d}",
                defaults={
                    "constructora": empresa,
                    "nombre": name,
                    "tipo": self.resolve_stage_type(name),
                    "region": empresa.region,
                    "comuna": empresa.comuna,
                    "direccion": empresa.direccion,
                    "descripcion": f"Etapa QA para preset {empresa.preset}: {name}.",
                    "estado": "activa",
                    "activa": True,
                },
            )
            etapas.append(etapa)

        return etapas

    def create_units(self, empresa, etapas, blueprint, preset, days):
        unidades = []
        start_date = timezone.localdate() - timedelta(days=days)

        for index, name in enumerate(blueprint["units"], start=1):
            etapa = etapas[(index - 1) % len(etapas)]
            unidad, _ = Obra.objects.update_or_create(
                codigo_obra=f"{empresa.constructora_id}_UNIDAD_{index:02d}",
                defaults={
                    "constructora": empresa,
                    "etapa_principal": etapa,
                    "nombre": name,
                    "tipo_proyecto": self.resolve_unit_type(preset),
                    "fecha_inicio": start_date,
                    "fecha_termino_estimada": timezone.localdate() + timedelta(days=90),
                    "superficie_m2": Decimal(str(1200 + index * 850)),
                    "ubicacion": f"{empresa.comuna}, {empresa.region}",
                    "region": empresa.region,
                    "comuna": empresa.comuna,
                    "mandante": "Demo QA Carbono Zero",
                    "estado": "en_ejecucion",
                    "descripcion": f"Unidad operativa QA para validar vistas del preset {preset}.",
                },
            )
            unidades.append(unidad)

        return unidades

    def create_factors(self, preset, blueprint):
        factors = {}

        for source in blueprint["sources"]:
            factor, _ = FactorEmision.objects.update_or_create(
                actividad=source["fuente"],
                unidad=source["unidad"],
                fuente=f"Seed QA Carbono Zero {preset}",
                anio=YEAR,
                defaults={
                    "preset": preset,
                    "module": source["module"],
                    "categoria": source["categoria"],
                    "factor_emision": Decimal(source["factor"]),
                    "alcance": "Referencial QA",
                    "descripcion": f"Factor QA para {source['fuente']} en preset {preset}.",
                    "metadata": {
                        "seed": True,
                        "preset": preset,
                        "module": source["module"],
                    },
                    "activo": True,
                },
            )
            factors[source["fuente"]] = factor

        return factors

    def create_records(self, empresa, etapas, unidades, factores, blueprint, days, rng):
        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)
        registros = []

        weighted_sources = []
        for source in blueprint["sources"]:
            weighted_sources.extend([source] * max(1, int(source["weight"] * 10)))

        for day_index in range(days):
            current_date = start_date + timedelta(days=day_index)

            daily_records = rng.randint(3, 6)

            for record_index in range(daily_records):
                source = rng.choice(weighted_sources)
                factor = factores[source["fuente"]]
                unidad_operativa = rng.choice(unidades)
                etapa = unidad_operativa.etapa_principal or rng.choice(etapas)
                cantidad = self.random_decimal(rng, source["min"], source["max"])

                registro = RegistroEmision.objects.create(
                    constructora=empresa,
                    obra=unidad_operativa,
                    etapa=etapa,
                    categoria=source["categoria"],
                    fuente_emision=source["fuente"],
                    cantidad=cantidad,
                    unidad=source["unidad"],
                    factor_emision=factor.factor_emision,
                    fecha=current_date,
                    proveedor=self.resolve_provider(source["fuente"], empresa.preset),
                    origen_transporte=self.resolve_origin(source, empresa),
                    destino_transporte=self.resolve_destination(source, empresa),
                    distancia_km=self.resolve_distance(source, rng),
                    observaciones=f"Registro QA {empresa.preset} día {day_index + 1}.",
                    metadata={
                        "seed": True,
                        "preset": empresa.preset,
                        "module": source["module"],
                        "source_profile": source["fuente"],
                        "simulated_day_index": day_index + 1,
                        "simulated_record_index": record_index + 1,
                        "evidence_expected": source["evidence_type"],
                    },
                )
                registros.append(registro)

        return registros

    def create_evidences(self, empresa, registros, preset, rng):
        evidencias_creadas = 0

        selected_records = [
            registro
            for index, registro in enumerate(registros)
            if index % 14 == 0
            or registro.fuente_emision.lower().find("diesel") >= 0
            and index % 21 == 0
        ]

        for registro in selected_records:
            evidence_type = registro.metadata.get(
                "evidence_expected"
            ) or self.resolve_evidence_type(registro)
            filename = f"{empresa.constructora_id}_{registro.id}_{evidence_type}.txt"
            content = (
                f"Evidencia QA Carbono Zero\n"
                f"Empresa: {empresa.nombre}\n"
                f"Preset: {preset}\n"
                f"Fuente: {registro.fuente_emision}\n"
                f"Cantidad: {registro.cantidad} {registro.unidad}\n"
                f"Fecha: {registro.fecha}\n"
                f"Emisiones: {registro.emisiones_kg_co2e} kg CO2e\n"
            )

            evidencia = EvidenciaObra(
                constructora=empresa,
                obra=registro.obra,
                etapa=registro.etapa,
                registro_emision=registro,
                tipo_evidencia=evidence_type,
                estado_documental=rng.choice(
                    ["validada", "vinculada", "pendiente", "observada"]
                ),
                fecha_documento=registro.fecha,
                nombre=f"Respaldo QA - {registro.fuente_emision}",
                observaciones="Evidencia generada automáticamente para pruebas de flujo documental.",
                texto_extraido=content,
                metadata_extraccion={
                    "seed": True,
                    "preset": preset,
                    "module": registro.metadata.get("module"),
                    "fuente_emision_sugerida": registro.fuente_emision,
                    "categoria_sugerida": registro.categoria,
                    "cantidad_sugerida": str(registro.cantidad),
                    "unidad_sugerida": registro.unidad,
                    "confianza_extraccion": 0.88,
                    "extraction_engine": "seed_qa",
                },
            )
            evidencia.archivo.save(filename, ContentFile(content), save=True)
            evidencias_creadas += 1

        return evidencias_creadas

    def random_decimal(self, rng, min_value, max_value):
        value = rng.uniform(float(min_value), float(max_value))
        return Decimal(str(round(value, 3)))

    def resolve_stage_type(self, name):
        normalized = name.lower()

        if "fundacion" in normalized:
            return "Fundaciones"
        if "obra gruesa" in normalized:
            return "Obra gruesa"
        if "terminacion" in normalized:
            return "Terminaciones"
        if "residuo" in normalized:
            return "Retiro de residuos"
        if "excav" in normalized:
            return "Excavacion"
        if (
            "logistica" in normalized
            or "ruta" in normalized
            or "transporte" in normalized
        ):
            return "Logistica"

        return "Otro"

    def resolve_unit_type(self, preset):
        if preset == "construccion":
            return "Edificio habitacional"
        if preset == "industrial":
            return "Industrial"
        if preset == "transporte":
            return "Infraestructura"
        return "Otro"

    def resolve_provider(self, source, preset):
        source_lower = source.lower()

        if "hormigon" in source_lower:
            return "Proveedor Hormigones QA"
        if "acero" in source_lower:
            return "Proveedor Aceros QA"
        if "diesel" in source_lower or "combustible" in source_lower:
            return "Proveedor Combustible QA"
        if "electricidad" in source_lower:
            return "Distribuidora Eléctrica QA"
        if "residuo" in source_lower:
            return "Gestor Residuos QA"

        return f"Proveedor QA {preset}"

    def resolve_origin(self, source, empresa):
        if source["categoria"] == "Transporte":
            return f"{empresa.comuna}, {empresa.region}"

        return ""

    def resolve_destination(self, source, empresa):
        if source["categoria"] == "Transporte":
            return "Destino operativo QA"

        return ""

    def resolve_distance(self, source, rng):
        if source["categoria"] != "Transporte":
            return None

        return Decimal(str(round(rng.uniform(8, 280), 3)))

    def resolve_evidence_type(self, registro):
        source = registro.fuente_emision.lower()

        if "diesel" in source or "combustible" in source:
            return "factura_combustible"
        if "hormigon" in source or "acero" in source or "material" in source:
            return "factura_material"
        if "electricidad" in source or "kwh" in source:
            return "boleta_electrica"
        if "residuo" in source:
            return "registro_retiro_residuos"
        if "ruta" in source or "transporte" in source:
            return "documento_transporte"

        return "otro"
