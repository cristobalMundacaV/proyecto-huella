import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import (
    ConfiguracionConstructora,
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    LoteForestal,
    RegistroEmision,
    TransporteLoteForestal,
    TransporteObra,
)

ACTIVE_PREFIX = "CZP_"
LEGACY_PREFIX = "CZ_SEED"
YEAR = timezone.localdate().year


def source(categoria, fuente, unidad, factor, min_value, max_value, module, evidence, weight):
    return {
        "categoria": categoria,
        "fuente": fuente,
        "unidad": unidad,
        "factor": Decimal(factor),
        "min": Decimal(str(min_value)),
        "max": Decimal(str(max_value)),
        "module": module,
        "evidence": evidence,
        "weight": int(weight),
    }


PILOT_COMPANIES = {
    "constructora": {
        "id": "CZP_CONSTRUCTORA_BIOBIO",
        "name": "Constructora Bío Bío Infraestructura",
        "rubro": "Construcción",
        "preset": "construccion",
        "sector_label": "construccion",
        "region": "Biobío",
        "comuna": "Los Ángeles",
        "email": "ambiental@constructorabiobio.cl",
        "telefono": "+56 43 232 4100",
        "contacto": "Coordinación de obra",
        "observaciones": "Seguimiento ambiental en obras urbanas y viales.",
        "data_maturity": "Inicial",
        "quality": {"link": 0.48, "stage": 0.42, "source": 0.78, "factor": 0.70, "quantity": 0.86, "evidence": 0.18},
        "units": ["Edificio Norte Los Ángeles", "Conjunto Habitacional Paillihue", "Urbanización Avenida Oriente"],
        "stages": ["Movimiento de tierra", "Fundaciones", "Obra gruesa", "Terminaciones", "Retiro de residuos"],
        "unit_type": "Edificio habitacional",
        "mandante": "Inmobiliaria del Sur",
        "sources": [
            source("Materiales", "Hormigón H30", "m3", "310.000000", 5, 28, "materiales", "factura_material", 34),
            source("Materiales", "Acero de refuerzo", "ton", "1850.000000", 0.08, 0.62, "materiales", "factura_material", 20),
            source("Maquinaria", "Excavadora diesel", "litros diesel", "2.680000", 16, 92, "maquinaria", "registro_maquinaria", 18),
            source("Transporte", "Camión tolva obra", "litros diesel", "2.680000", 22, 150, "transporte", "factura_combustible", 19),
            source("Residuos", "Retiro de escombros", "kg", "0.080000", 220, 1800, "residuos", "registro_retiro_residuos", 9),
        ],
    },
    "industrial": {
        "id": "CZP_INDUSTRIAS_NAHUELBUTA",
        "name": "Industrias Nahuelbuta SpA",
        "rubro": "Industrial manufactura",
        "preset": "industrial",
        "sector_label": "industrial",
        "region": "Biobío",
        "comuna": "Concepción",
        "email": "medioambiente@industriasnahuelbuta.cl",
        "telefono": "+56 41 236 1180",
        "contacto": "Encargada de medio ambiente",
        "observaciones": "Control de consumos, caldera, residuos y despacho.",
        "data_maturity": "Intermedia",
        "quality": {"link": 0.72, "stage": 0.76, "source": 0.88, "factor": 0.82, "quantity": 0.92, "evidence": 0.46},
        "units": ["Línea Producción A", "Línea Producción B", "Caldera Principal", "Bodega Despacho"],
        "stages": ["Producción", "Energía", "Caldera", "Residuos industriales", "Transporte interno"],
        "unit_type": "Industrial",
        "mandante": "Operación interna",
        "sources": [
            source("Energia", "Electricidad planta", "kWh", "0.390000", 720, 4300, "energia", "boleta_electrica", 34),
            source("Energia", "Diésel caldera", "litros diesel", "2.680000", 55, 360, "caldera", "factura_combustible", 25),
            source("Residuos", "Residuo industrial no peligroso", "kg", "0.120000", 420, 2800, "residuos", "ticket_pesaje", 18),
            source("Agua", "Agua de proceso", "m3", "0.450000", 24, 170, "agua", "otro", 10),
            source("Transporte", "Grúa horquilla diésel", "litros diesel", "2.680000", 10, 82, "transporte_interno", "factura_combustible", 13),
        ],
    },
    "forestal": {
        "id": "CZP_FORESTAL_SANTA_LAURA",
        "name": "Forestal Santa Laura Ltda",
        "rubro": "Forestal",
        "preset": "aserradero",
        "sector_label": "forestal",
        "region": "Biobío",
        "comuna": "Mulchén",
        "email": "gestionambiental@forestalsantalaura.cl",
        "telefono": "+56 43 245 7700",
        "contacto": "Jefatura de patrimonio",
        "observaciones": "Trazabilidad de lotes, cosecha y transporte forestal.",
        "data_maturity": "Trazabilidad parcial",
        "quality": {"link": 0.82, "stage": 0.74, "source": 0.86, "factor": 0.78, "quantity": 0.94, "evidence": 0.58},
        "units": ["Predio Santa Laura", "Predio El Roble", "Patio Acopio Mulchén"],
        "stages": ["Cosecha", "Clasificación", "Acopio", "Transporte forestal", "Recepción destino"],
        "unit_type": "Infraestructura",
        "mandante": "Patrimonio forestal",
        "lotes": [
            ("SL-PINO-2401", "Pino radiata", "96.400", "Predio Santa Laura", "Patio Acopio Mulchén", "Troza aserrable", "420.000", "0.5000"),
            ("SL-PINO-2402", "Pino radiata", "78.800", "Predio El Roble", "Planta destino", "Madera pulpable", "420.000", "0.5000"),
            ("SL-EUCA-2403", "Eucalipto", "64.200", "Predio Los Aromos", "Patio Acopio Mulchén", "Troza industrial", "560.000", "0.4800"),
        ],
        "sources": [
            source("Maquinaria", "Harvester diésel", "litros diesel", "2.680000", 32, 150, "cosecha", "registro_maquinaria", 23),
            source("Maquinaria", "Forwarder diésel", "litros diesel", "2.680000", 24, 130, "cosecha", "registro_maquinaria", 18),
            source("Transporte", "Camión forestal", "litros diesel", "2.680000", 42, 210, "transporte_forestal", "factura_combustible", 28),
            source("Materiales", "Volumen cosechado", "m3", "18.000000", 8, 42, "lotes_forestales", "guia_despacho", 24),
            source("Residuos", "Residuos de faena", "kg", "0.030000", 120, 860, "residuos", "registro_retiro_residuos", 7),
        ],
    },
    "transporte": {
        "id": "CZP_TRANSPORTES_RUTA_SUR",
        "name": "Transportes Ruta Sur SpA",
        "rubro": "Transporte y logística",
        "preset": "transporte",
        "sector_label": "transporte",
        "region": "Metropolitana",
        "comuna": "Santiago",
        "email": "operaciones@rutasur.cl",
        "telefono": "+56 2 2840 3100",
        "contacto": "Control de flota",
        "observaciones": "Seguimiento de combustible, rutas y operación de flota.",
        "data_maturity": "Operacional",
        "quality": {"link": 0.86, "stage": 0.88, "source": 0.94, "factor": 0.90, "quantity": 0.96, "evidence": 0.66},
        "units": ["Camión RS-01", "Camión RS-02", "Camión RS-03", "Ruta Centro Sur"],
        "stages": ["Planificación de rutas", "Operación de flota", "Combustible", "Mantenciones", "Carga y distribución"],
        "unit_type": "Infraestructura",
        "mandante": "Clientes de distribución nacional",
        "sources": [
            source("Transporte", "Diésel camión ruta", "litros diesel", "2.680000", 48, 265, "combustible", "factura_combustible", 45),
            source("Transporte", "Kilómetros ruta larga", "km", "0.850000", 80, 560, "rutas", "documento_transporte", 28),
            source("Maquinaria", "Mantención flota", "unidad", "35.000000", 1, 4, "mantenciones", "otro", 10),
            source("Energia", "Electricidad centro logístico", "kWh", "0.390000", 90, 460, "centro_logistico", "boleta_electrica", 8),
            source("Residuos", "Neumáticos y residuos taller", "kg", "0.180000", 20, 180, "residuos", "ticket_pesaje", 9),
        ],
    },
    "aserradero": {
        "id": "CZP_ASERRADERO_LOS_RAULIES",
        "name": "Aserradero Los Raulíes Ltda",
        "rubro": "Aserradero",
        "preset": "aserradero",
        "sector_label": "aserradero",
        "region": "Biobío",
        "comuna": "Los Ángeles",
        "email": "controlambiental@losraulies.cl",
        "telefono": "+56 43 251 6800",
        "contacto": "Encargado de producción",
        "observaciones": "Control de recepción, aserrío, secado y despacho de madera.",
        "data_maturity": "Avanzada",
        "quality": {"link": 0.94, "stage": 0.93, "source": 0.97, "factor": 0.95, "quantity": 0.98, "evidence": 0.82},
        "units": ["Línea Aserrío 1", "Cámara Secado 2", "Patio Trozas", "Despacho Madera Seca"],
        "stages": ["Recepción de trozas", "Aserrío", "Secado", "Clasificación", "Despacho"],
        "unit_type": "Industrial",
        "mandante": "Clientes industriales y construcción",
        "lotes": [
            ("LR-PINO-2501", "Pino radiata", "88.500", "Predio Los Raulíes", "Planta Los Ángeles", "Madera estructural", "420.000", "0.5000"),
            ("LR-PINO-2502", "Pino radiata", "72.300", "Predio Las Palmas", "Planta Los Ángeles", "Madera seca", "420.000", "0.5000"),
            ("LR-ROBLE-2503", "Roble", "38.600", "Predio Cordillera", "Planta Los Ángeles", "Tabla dimensionada", "650.000", "0.5000"),
        ],
        "sources": [
            source("Materiales", "Recepción de trozas", "m3", "18.000000", 8, 44, "recepcion_trozas", "guia_despacho", 22),
            source("Procesos externos", "Proceso de aserrío", "m3", "22.000000", 7, 38, "produccion", "registro_produccion", 18),
            source("Energia", "Electricidad secado", "kWh", "0.390000", 360, 1900, "secado", "boleta_electrica", 28),
            source("Transporte", "Diésel despacho madera", "litros diesel", "2.680000", 34, 175, "transporte", "factura_combustible", 20),
            source("Residuos", "Subproductos de madera", "kg", "0.030000", 240, 1500, "subproductos", "registro_produccion", 12),
        ],
    },
    "mineria": {
        "id": "CZP_MINERA_CORDILLERA_SUR",
        "name": "Minera Cordillera Sur SpA",
        "rubro": "Minería",
        "preset": "industrial",
        "sector_label": "mineria",
        "region": "Antofagasta",
        "comuna": "Calama",
        "email": "sustentabilidad@cordillerasur.cl",
        "telefono": "+56 55 241 9000",
        "contacto": "Superintendencia ambiental",
        "observaciones": "Control ambiental de operación minera, energía, agua y flota interna.",
        "data_maturity": "Consolidada",
        "quality": {"link": 0.98, "stage": 0.98, "source": 0.99, "factor": 0.98, "quantity": 0.99, "evidence": 0.92},
        "units": ["Rajo Norte", "Planta Chancado", "Campamento Operación", "Botadero Controlado"],
        "stages": ["Extracción", "Chancado", "Transporte interno", "Energía y agua", "Residuos operacionales"],
        "unit_type": "Industrial",
        "mandante": "Operación minera",
        "sources": [
            source("Maquinaria", "Camión extracción diésel", "litros diesel", "2.680000", 140, 780, "flota_mina", "factura_combustible", 31),
            source("Energia", "Electricidad chancado", "kWh", "0.390000", 1800, 9200, "energia", "boleta_electrica", 26),
            source("Agua", "Agua proceso", "m3", "0.450000", 180, 960, "agua", "otro", 15),
            source("Transporte", "Transporte interno mineral", "litros diesel", "2.680000", 90, 420, "transporte_interno", "registro_maquinaria", 16),
            source("Residuos", "Residuo operacional controlado", "kg", "0.120000", 600, 4200, "residuos", "ticket_pesaje", 12),
        ],
    },
}


class Command(BaseCommand):
    help = "Crea empresas piloto realistas de Carbono Zero con registros ambientales históricos."

    def add_arguments(self, parser):
        parser.add_argument("--records", type=int, default=180, help="Cantidad de registros por empresa.")
        parser.add_argument("--days", type=int, default=180, help="Ventana histórica en días.")
        parser.add_argument("--reset", action="store_true", help="Elimina empresas piloto anteriores antes de crear datos.")
        parser.add_argument("--seed", type=int, default=20260621, help="Semilla determinística para reproducir los datos.")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        records_per_company = max(1, int(options["records"]))
        days = max(30, int(options["days"]))

        if options["reset"]:
            self.reset_pilots()

        totals = {"empresas": 0, "etapas": 0, "unidades": 0, "lotes": 0, "factores": 0, "registros": 0, "evidencias": 0}
        for key, cfg in PILOT_COMPANIES.items():
            result = self.seed_company(key, cfg, records_per_company, days, rng)
            for total_key, value in result.items():
                totals[total_key] += value

        self.stdout.write(self.style.SUCCESS("Empresas piloto Carbono Zero creadas correctamente."))
        self.stdout.write(self.style.SUCCESS(str(totals)))

    def reset_pilots(self):
        query = Q(constructora_id__startswith=ACTIVE_PREFIX) | Q(constructora_id__startswith=LEGACY_PREFIX)
        empresas = Constructora.objects.filter(query)
        TransporteObra.objects.filter(obra__constructora__in=empresas).delete()
        TransporteLoteForestal.objects.filter(lote_forestal__constructora__in=empresas).delete()
        EvidenciaObra.objects.filter(constructora__in=empresas).delete()
        RegistroEmision.objects.filter(constructora__in=empresas).delete()
        LoteForestal.objects.filter(constructora__in=empresas).delete()
        Obra.objects.filter(constructora__in=empresas).delete()
        EtapaObra.objects.filter(constructora__in=empresas).delete()
        ConfiguracionConstructora.objects.filter(constructora__in=empresas).delete()
        count = empresas.count()
        empresas.delete()
        self.stdout.write(self.style.WARNING(f"Empresas piloto eliminadas: {count}"))

    def seed_company(self, key, cfg, records_per_company, days, rng):
        empresa, created = Constructora.objects.update_or_create(
            constructora_id=cfg["id"],
            defaults={
                "nombre": cfg["name"],
                "rubro": cfg["rubro"],
                "preset": cfg["preset"],
                "region": cfg["region"],
                "comuna": cfg["comuna"],
                "direccion": f"{cfg['comuna']}, {cfg['region']}",
                "email": cfg["email"],
                "telefono": cfg["telefono"],
                "contacto": cfg["contacto"],
                "observaciones": cfg["observaciones"],
                "activa": True,
            },
        )
        self.configure_company(empresa, cfg)
        etapas = self.create_stages(empresa, cfg)
        unidades = self.create_units(empresa, etapas, cfg)
        lotes = self.create_lotes(empresa, cfg)
        factores = self.create_factors(cfg)
        registros = self.create_records(empresa, unidades, etapas, lotes, factores, cfg, records_per_company, days, rng)
        evidencias = self.create_evidences(empresa, registros, rng)
        return {"empresas": int(created), "etapas": len(etapas), "unidades": len(unidades), "lotes": len(lotes), "factores": len(factores), "registros": len(registros), "evidencias": evidencias}

    def configure_company(self, empresa, cfg):
        maturity = cfg["quality"]
        strict = maturity["link"] >= 0.85
        ConfiguracionConstructora.objects.update_or_create(
            constructora=empresa,
            defaults={
                "modo_importacion": "estricto" if strict else "flexible",
                "permitir_registros_sin_factor": not strict,
                "requerir_etapa_obra": strict,
                "requerir_obra_registro": strict,
                "permitir_evidencias_sin_vinculo": not strict,
                "evidencia_obligatoria": cfg["quality"]["evidence"] >= 0.80,
                "factor_electrico_default": "Factor eléctrico operativo vigente",
                "region_electrica_default": cfg["region"],
            },
        )

    def create_stages(self, empresa, cfg):
        etapas = []
        for index, name in enumerate(cfg["stages"], 1):
            etapa, _ = EtapaObra.objects.update_or_create(
                etapa_id=f"{empresa.constructora_id}_ETAPA_{index:02d}",
                defaults={
                    "constructora": empresa,
                    "nombre": name,
                    "tipo": self.stage_type(name),
                    "region": empresa.region,
                    "comuna": empresa.comuna,
                    "direccion": empresa.direccion,
                    "descripcion": f"Proceso operativo: {name}.",
                    "estado": "activa",
                    "activa": True,
                },
            )
            etapas.append(etapa)
        return etapas

    def create_units(self, empresa, etapas, cfg):
        unidades = []
        start = timezone.localdate() - timedelta(days=210)
        for index, name in enumerate(cfg["units"], 1):
            etapa = etapas[(index - 1) % len(etapas)]
            unidad, _ = Obra.objects.update_or_create(
                codigo_obra=f"{empresa.constructora_id}_UNIDAD_{index:02d}",
                defaults={
                    "constructora": empresa,
                    "etapa_principal": etapa,
                    "nombre": name,
                    "tipo_proyecto": cfg["unit_type"],
                    "fecha_inicio": start + timedelta(days=index * 11),
                    "fecha_termino_estimada": timezone.localdate() + timedelta(days=90 + index * 15),
                    "superficie_m2": Decimal(str(950 + index * 640)),
                    "ubicacion": f"{empresa.comuna}, {empresa.region}",
                    "region": empresa.region,
                    "comuna": empresa.comuna,
                    "mandante": cfg["mandante"],
                    "estado": "en_ejecucion",
                    "descripcion": "Unidad operacional incluida en el seguimiento ambiental.",
                },
            )
            unidades.append(unidad)
        return unidades

    def create_lotes(self, empresa, cfg):
        lotes = []
        start = timezone.localdate() - timedelta(days=175)
        for index, item in enumerate(cfg.get("lotes", []), 1):
            lote_id, especie, volumen, origen, destino, producto, densidad, carbono = item
            lote, _ = LoteForestal.objects.update_or_create(
                lote_id=f"{empresa.constructora_id}_{lote_id}",
                defaults={
                    "constructora": empresa,
                    "fecha": start + timedelta(days=index * 18),
                    "especie": especie,
                    "volumen_m3": Decimal(volumen),
                    "origen": origen,
                    "destino": destino,
                    "tipo_producto": producto,
                    "densidad_kg_m3": Decimal(densidad),
                    "porcentaje_carbono": Decimal(carbono),
                    "estado": "activo",
                    "observaciones": "Lote trazable para balance neto, transporte y evidencia operacional.",
                    "metadata": {"sector": cfg["sector_label"], "module": "lotes_forestales", "data_maturity": cfg["data_maturity"]},
                },
            )
            lotes.append(lote)
        return lotes

    def create_factors(self, cfg):
        factors = {}
        factor_source = f"Referencia operativa {cfg['sector_label']} {YEAR}"
        for item in cfg["sources"]:
            factor, _ = FactorEmision.objects.update_or_create(
                actividad=item["fuente"],
                unidad=item["unidad"],
                fuente=factor_source,
                anio=YEAR,
                defaults={
                    "preset": cfg["preset"],
                    "module": item["module"],
                    "categoria": item["categoria"] or "Otros",
                    "factor_emision": item["factor"],
                    "alcance": "Referencia operativa",
                    "descripcion": f"Factor aplicado a {item['fuente']}.",
                    "metadata": {"sector": cfg["sector_label"], "module": item["module"]},
                    "activo": True,
                },
            )
            factors[item["fuente"]] = factor
        return factors

    def create_records(self, empresa, unidades, etapas, lotes, factors, cfg, count, days, rng):
        registros = []
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)
        weighted_sources = []
        for item in cfg["sources"]:
            weighted_sources.extend([item] * max(1, int(item["weight"])))

        for index in range(count):
            item = rng.choice(weighted_sources)
            factor = factors[item["fuente"]]
            fecha = start + timedelta(days=index % days)
            obra = unidades[index % len(unidades)] if rng.random() <= cfg["quality"]["link"] else None
            etapa = obra.etapa_principal if obra else (etapas[index % len(etapas)] if rng.random() <= cfg["quality"]["stage"] else None)
            lote = rng.choice(lotes) if lotes and rng.random() <= cfg["quality"]["link"] else None
            has_source = rng.random() <= cfg["quality"]["source"]
            has_factor = rng.random() <= cfg["quality"]["factor"]
            valid_quantity = rng.random() <= cfg["quality"]["quantity"]
            amount = self.amount_for(item, fecha, rng) if valid_quantity else Decimal("0.000")
            factor_value = factor.factor_emision if has_factor else Decimal("0.000000")
            fuente = item["fuente"] if has_source else ""
            categoria = item["categoria"] if has_source else ""
            is_transport = item["categoria"] == "Transporte"
            metadata = {
                "sector": cfg["sector_label"],
                "preset": empresa.preset,
                "module": item["module"],
                "source_profile": item["fuente"],
                "data_maturity": cfg["data_maturity"],
                "evidence_expected": item["evidence"],
                "quality_flags": self.quality_flags(obra, etapa, fuente, categoria, factor_value, amount),
                "should_create_evidence": rng.random() <= cfg["quality"]["evidence"],
            }
            if lote:
                metadata["lote"] = lote.lote_id

            registro = RegistroEmision.objects.create(
                constructora=empresa,
                obra=obra,
                etapa=etapa,
                lote_forestal=lote,
                categoria=categoria or "Otros",
                fuente_emision=fuente,
                cantidad=amount,
                unidad=item["unidad"],
                factor_emision=factor_value,
                fecha=fecha,
                proveedor=self.provider(item["fuente"], cfg),
                origen_transporte=self.origin(empresa, lote) if is_transport else "",
                destino_transporte=self.destination(empresa, lote) if is_transport else "",
                distancia_km=Decimal(str(round(rng.uniform(8, 420), 3))) if is_transport else None,
                observaciones=self.record_observation(metadata),
                metadata=metadata,
            )
            if obra and rng.random() > cfg["quality"]["stage"]:
                RegistroEmision.objects.filter(pk=registro.pk).update(etapa=None)
                registro.etapa = None
            registros.append(registro)
        return registros

    def create_evidences(self, empresa, registros, rng):
        total = 0
        for registro in registros:
            if not registro.metadata.get("should_create_evidence"):
                continue
            evidence_type = registro.metadata.get("evidence_expected") or "otro"
            status = self.evidence_status(rng)
            content = (
                f"Respaldo ambiental\n"
                f"Empresa: {empresa.nombre}\n"
                f"Fuente: {registro.fuente_emision or registro.metadata.get('source_profile', 'Sin fuente')}\n"
                f"Cantidad: {registro.cantidad} {registro.unidad}\n"
                f"Fecha: {registro.fecha}\n"
                f"Emisiones: {registro.emisiones_kg_co2e} kg CO2e\n"
            )
            evidencia = EvidenciaObra(
                constructora=empresa,
                obra=registro.obra,
                etapa=registro.etapa,
                registro_emision=registro,
                lote_forestal=registro.lote_forestal,
                tipo_evidencia=evidence_type,
                estado_documental=status,
                fecha_documento=registro.fecha,
                nombre=f"Respaldo {registro.fecha} - {registro.fuente_emision or registro.metadata.get('source_profile', 'registro ambiental')}",
                observaciones="Documento operacional vinculado al registro ambiental.",
                texto_extraido=content,
                metadata_extraccion={
                    "sector": empresa.rubro,
                    "module": registro.metadata.get("module"),
                    "fuente_emision_sugerida": registro.fuente_emision or registro.metadata.get("source_profile"),
                    "categoria_sugerida": registro.categoria,
                    "cantidad_sugerida": str(registro.cantidad),
                    "unidad_sugerida": registro.unidad,
                    "confianza_extraccion": round(rng.uniform(0.74, 0.97), 2),
                },
            )
            filename = f"{empresa.constructora_id}_{registro.id}_{evidence_type}.txt"
            evidencia.archivo.save(filename, ContentFile(content), save=True)
            total += 1
        return total

    def amount_for(self, item, fecha, rng):
        min_value = float(item["min"])
        max_value = float(item["max"])
        base = rng.uniform(min_value, max_value)
        month_factor = 1 + (0.12 if fecha.month in {3, 4, 5, 10, 11} else 0) - (0.10 if fecha.month in {1, 2} else 0)
        weekday_factor = 0.82 if fecha.weekday() >= 5 else 1
        return Decimal(str(round(max(0, base * month_factor * weekday_factor), 3)))

    def quality_flags(self, obra, etapa, fuente, categoria, factor_value, amount):
        flags = []
        if not obra:
            flags.append("sin_vinculo_operacional")
        if not etapa:
            flags.append("sin_etapa")
        if not fuente or not categoria:
            flags.append("sin_fuente_o_categoria")
        if not factor_value:
            flags.append("sin_factor")
        if not amount:
            flags.append("cantidad_invalida")
        return flags or ["completo"]

    def record_observation(self, metadata):
        if metadata["quality_flags"] == ["completo"]:
            return "Registro consistente para análisis ambiental."
        return "Registro operativo pendiente de completar para fortalecer trazabilidad."

    def evidence_status(self, rng):
        value = rng.random()
        if value < 0.70:
            return EvidenciaObra.EstadoDocumental.VINCULADA
        if value < 0.88:
            return EvidenciaObra.EstadoDocumental.VALIDADA
        if value < 0.96:
            return EvidenciaObra.EstadoDocumental.PENDIENTE
        return EvidenciaObra.EstadoDocumental.OBSERVADA

    def stage_type(self, name):
        normalized = name.lower()
        if "fund" in normalized:
            return "Fundaciones"
        if "obra gruesa" in normalized:
            return "Obra gruesa"
        if "termin" in normalized:
            return "Terminaciones"
        if "resid" in normalized:
            return "Retiro de residuos"
        if "extrac" in normalized or "movimiento" in normalized:
            return "Excavacion"
        if "ruta" in normalized or "transporte" in normalized or "log" in normalized:
            return "Logistica"
        if "energ" in normalized or "caldera" in normalized:
            return "Instalaciones"
        return "Otro"

    def provider(self, fuente, cfg):
        normalized = fuente.lower()
        if "hormig" in normalized:
            return "Hormigones Bío Bío"
        if "acero" in normalized:
            return "Aceros del Sur"
        if "diesel" in normalized or "diésel" in normalized or "combustible" in normalized:
            return "Distribuidora Combustibles Sur"
        if "electricidad" in normalized:
            return "Empresa eléctrica regional"
        if "residuo" in normalized or "escombro" in normalized:
            return "Gestor ambiental autorizado"
        if cfg["sector_label"] in {"forestal", "aserradero"}:
            return "Operación forestal integrada"
        if cfg["sector_label"] == "mineria":
            return "Proveedor operacional minero"
        return "Proveedor operacional"

    def origin(self, empresa, lote=None):
        return lote.origen if lote else f"{empresa.comuna}, {empresa.region}"

    def destination(self, empresa, lote=None):
        if lote:
            return lote.destino
        if empresa.preset == "transporte":
            return "Centro de distribución cliente"
        if empresa.rubro == "Minería":
            return "Área operacional mina"
        return f"Unidad operacional {empresa.comuna}"
