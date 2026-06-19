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
    LoteForestal,
    Obra,
    RegistroEmision,
    TransporteLoteForestal,
    TransporteObra,
)

SEED_PREFIX = "CZ_SEED"
YEAR = timezone.localdate().year

PRESETS = {
    "construccion": {
        "id": "CZ_SEED_CONSTRUCCION",
        "name": "Constructora Demo Carbono Zero",
        "rubro": "Construccion",
        "region": "Biobio",
        "comuna": "Los Angeles",
        "units": ["Edificio Habitacional Norte", "Condominio Sustentable Sur", "Centro Comercial Piloto"],
        "stages": ["Excavacion", "Fundaciones", "Obra gruesa", "Terminaciones", "Retiro de residuos"],
        "sources": [
            ("Materiales", "Hormigon H30", "m3", "310.000000", 4, 18, "materiales", "factura_material", 42),
            ("Materiales", "Acero de refuerzo", "ton", "1850.000000", 0.05, 0.42, "materiales", "factura_material", 28),
            ("Maquinaria", "Excavadora diesel", "litros diesel", "2.680000", 18, 96, "maquinaria", "registro_maquinaria", 17),
            ("Transporte", "Diesel camion obra", "litros diesel", "2.680000", 25, 145, "transporte", "factura_combustible", 22),
            ("Residuos", "Retiro de escombros", "kg", "0.080000", 260, 1600, "residuos", "registro_retiro_residuos", 11),
        ],
    },
    "aserradero": {
        "id": "CZ_SEED_ASERRADERO",
        "name": "Aserradero Demo Carbono Zero",
        "rubro": "Forestal / Aserradero",
        "region": "Biobio",
        "comuna": "Los Angeles",
        "units": ["Lote Pino Radiata A", "Lote Pino Radiata B", "Lote Eucalipto C"],
        "stages": ["Recepcion de trozas", "Produccion", "Secado", "Energia", "Transporte forestal", "Residuos y subproductos"],
        "lotes": [
            ("LOTE-PINO-A", "Pino radiata", "84.500", "Predio Santa Clara", "Planta Los Angeles", "Troza aserrable", "420.000", "0.5000"),
            ("LOTE-PINO-B", "Pino radiata", "66.200", "Predio El Roble", "Planta Los Angeles", "Madera estructural", "420.000", "0.5000"),
            ("LOTE-EUCA-C", "Eucalipto", "52.700", "Predio Las Vertientes", "Planta Los Angeles", "Madera seca", "560.000", "0.4800"),
        ],
        "sources": [
            ("Materiales", "Recepcion de trozas", "m3", "18.000000", 8, 38, "recepcion_trozas", "guia_despacho", 22),
            ("Procesos externos", "Proceso de aserrio", "m3", "22.000000", 7, 34, "produccion", "registro_produccion", 18),
            ("Energia", "Electricidad secado", "kWh", "0.390000", 320, 1800, "secado", "boleta_electrica", 34),
            ("Transporte", "Diesel transporte forestal", "litros diesel", "2.680000", 35, 170, "transporte_forestal", "factura_combustible", 25),
            ("Residuos", "Subproductos de madera", "kg", "0.030000", 220, 1400, "residuos_subproductos", "registro_retiro_residuos", 10),
        ],
    },
    "transporte": {
        "id": "CZ_SEED_TRANSPORTE",
        "name": "Transporte Demo Carbono Zero",
        "rubro": "Transporte y logistica",
        "region": "Metropolitana",
        "comuna": "Santiago",
        "units": ["Camion FL-01", "Camion FL-02", "Camion FL-03", "Ruta Centro Sur"],
        "stages": ["Planificacion de rutas", "Operacion de flota", "Combustible", "Mantenciones", "Carga y distribucion"],
        "sources": [
            ("Transporte", "Diesel camion ruta", "litros diesel", "2.680000", 45, 250, "combustible", "factura_combustible", 50),
            ("Transporte", "Ruta larga distancia", "km", "0.850000", 60, 520, "rutas", "documento_transporte", 31),
            ("Maquinaria", "Mantencion flota", "unidad", "35.000000", 1, 4, "mantenciones", "otro", 9),
            ("Energia", "Electricidad oficina logistica", "kWh", "0.390000", 90, 420, "flota", "boleta_electrica", 7),
        ],
    },
    "industrial": {
        "id": "CZ_SEED_INDUSTRIAL",
        "name": "Industria Demo Carbono Zero",
        "rubro": "Industrial",
        "region": "Biobio",
        "comuna": "Concepcion",
        "units": ["Linea Produccion A", "Linea Produccion B", "Caldera Principal", "Bodega Despacho"],
        "stages": ["Produccion", "Energia", "Caldera", "Residuos industriales", "Transporte interno"],
        "sources": [
            ("Energia", "Electricidad planta", "kWh", "0.390000", 700, 4200, "energia", "boleta_electrica", 43),
            ("Energia", "Diesel caldera", "litros diesel", "2.680000", 55, 340, "produccion", "factura_combustible", 34),
            ("Residuos", "Residuo industrial no peligroso", "kg", "0.120000", 400, 2600, "residuos", "ticket_pesaje", 17),
            ("Agua", "Consumo agua proceso", "m3", "0.450000", 20, 160, "agua", "otro", 11),
            ("Transporte", "Diesel grua interna", "litros diesel", "2.680000", 12, 75, "transporte", "factura_combustible", 9),
        ],
    },
}


class Command(BaseCommand):
    help = "Crea un demo limpio de Carbono Zero con registros validos por preset."

    def add_arguments(self, parser):
        parser.add_argument("--records", type=int, default=180)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--seed", type=int, default=20260619)

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        total_records = max(1, int(options["records"]))
        if options["reset"]:
            self.reset_demo()
        distribution = self.distribution(total_records)
        totals = {"empresas": 0, "etapas": 0, "unidades": 0, "lotes": 0, "factores": 0, "registros": 0, "evidencias": 0}
        for preset, count in distribution.items():
            result = self.seed_preset(preset, PRESETS[preset], count, rng)
            for key, value in result.items():
                totals[key] += value
        self.stdout.write(self.style.SUCCESS("Demo Carbono Zero creado correctamente."))
        self.stdout.write(self.style.SUCCESS(str(totals)))

    def distribution(self, total):
        keys = list(PRESETS.keys())
        base = total // len(keys)
        rem = total % len(keys)
        return {key: base + (1 if index < rem else 0) for index, key in enumerate(keys)}

    def reset_demo(self):
        empresas = Constructora.objects.filter(constructora_id__startswith=SEED_PREFIX)
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
        self.stdout.write(self.style.WARNING(f"Empresas demo eliminadas: {count}"))

    def seed_preset(self, preset, cfg, count, rng):
        empresa, created = Constructora.objects.update_or_create(
            constructora_id=cfg["id"],
            defaults={
                "nombre": cfg["name"],
                "rubro": cfg["rubro"],
                "preset": preset,
                "region": cfg["region"],
                "comuna": cfg["comuna"],
                "direccion": f"{cfg['comuna']}, {cfg['region']}",
                "email": f"{preset}@carbonozero.cl",
                "telefono": "+56 9 4321 0000",
                "contacto": "Equipo ambiental",
                "observaciones": "Empresa de demostracion para validar gestion ambiental por preset.",
                "activa": True,
            },
        )
        ConfiguracionConstructora.objects.get_or_create(constructora=empresa)
        etapas = self.create_stages(empresa, cfg)
        unidades = self.create_units(empresa, etapas, cfg, preset)
        lotes = self.create_lotes(empresa, cfg) if preset == "aserradero" else []
        factores = self.create_factors(preset, cfg)
        registros = self.create_records(empresa, unidades, lotes, factores, cfg, count, rng)
        evidencias = self.create_evidences(empresa, registros)
        return {"empresas": int(created), "etapas": len(etapas), "unidades": len(unidades), "lotes": len(lotes), "factores": len(factores), "registros": len(registros), "evidencias": evidencias}

    def create_stages(self, empresa, cfg):
        etapas = []
        for index, name in enumerate(cfg["stages"], 1):
            etapa, _ = EtapaObra.objects.update_or_create(
                etapa_id=f"{empresa.constructora_id}_ETAPA_{index:02d}",
                defaults={"constructora": empresa, "nombre": name, "tipo": self.stage_type(name), "region": empresa.region, "comuna": empresa.comuna, "direccion": empresa.direccion, "descripcion": f"Proceso operativo: {name}.", "estado": "activa", "activa": True},
            )
            etapas.append(etapa)
        return etapas

    def create_units(self, empresa, etapas, cfg, preset):
        unidades = []
        start = timezone.localdate() - timedelta(days=120)
        for index, name in enumerate(cfg["units"], 1):
            etapa = etapas[(index - 1) % len(etapas)]
            unidad, _ = Obra.objects.update_or_create(
                codigo_obra=f"{empresa.constructora_id}_UNIDAD_{index:02d}",
                defaults={"constructora": empresa, "etapa_principal": etapa, "nombre": name, "tipo_proyecto": self.unit_type(preset), "fecha_inicio": start + timedelta(days=index * 8), "fecha_termino_estimada": timezone.localdate() + timedelta(days=90), "superficie_m2": Decimal(str(1200 + index * 740)), "ubicacion": f"{empresa.comuna}, {empresa.region}", "region": empresa.region, "comuna": empresa.comuna, "mandante": "Mandante de referencia", "estado": "en_ejecucion", "descripcion": f"Unidad operativa para medicion ambiental del preset {preset}."},
            )
            unidades.append(unidad)
        return unidades

    def create_lotes(self, empresa, cfg):
        lotes = []
        start = timezone.localdate() - timedelta(days=90)
        for index, item in enumerate(cfg.get("lotes", []), 1):
            lote_id, especie, volumen, origen, destino, producto, densidad, carbono = item
            lote, _ = LoteForestal.objects.update_or_create(
                lote_id=f"{empresa.constructora_id}_{lote_id}",
                defaults={"constructora": empresa, "fecha": start + timedelta(days=index * 14), "especie": especie, "volumen_m3": Decimal(volumen), "origen": origen, "destino": destino, "tipo_producto": producto, "densidad_kg_m3": Decimal(densidad), "porcentaje_carbono": Decimal(carbono), "estado": "activo", "observaciones": "Lote trazable para balance neto, transporte y evidencias.", "metadata": {"preset": "aserradero", "module": "lotes_forestales", "quality_status": "validado"}},
            )
            lotes.append(lote)
        return lotes

    def create_factors(self, preset, cfg):
        factors = {}
        for source in cfg["sources"]:
            categoria, fuente, unidad, factor_value, _, _, module, _, _ = source
            factor, _ = FactorEmision.objects.update_or_create(
                actividad=fuente,
                unidad=unidad,
                fuente=f"Factor de referencia Carbono Zero {YEAR}",
                anio=YEAR,
                defaults={"preset": preset, "module": module, "categoria": categoria, "factor_emision": Decimal(factor_value), "alcance": "Referencia operativa", "descripcion": f"Factor usado para calcular emisiones de {fuente}.", "metadata": {"preset": preset, "module": module, "quality_status": "validado"}, "activo": True},
            )
            factors[fuente] = factor
        return factors

    def create_records(self, empresa, unidades, lotes, factors, cfg, count, rng):
        registros = []
        today = timezone.localdate()
        weighted = []
        for source in cfg["sources"]:
            weighted.extend([source] * max(1, int(source[8])))
        for index in range(count):
            categoria, fuente, unidad, _, min_v, max_v, module, evidence, _ = rng.choice(weighted)
            factor = factors[fuente]
            obra = unidades[index % len(unidades)]
            lote = rng.choice(lotes) if lotes else None
            cantidad = Decimal(str(round(rng.uniform(float(min_v), float(max_v)), 3)))
            is_transport = categoria == "Transporte"
            metadata = {"preset": empresa.preset, "module": module, "source_profile": fuente, "quality_status": "validado", "evidence_expected": evidence}
            if lote:
                metadata["lote"] = lote.lote_id
            registro = RegistroEmision.objects.create(
                constructora=empresa,
                obra=obra,
                etapa=obra.etapa_principal,
                lote_forestal=lote,
                categoria=categoria,
                fuente_emision=fuente,
                cantidad=cantidad,
                unidad=unidad,
                factor_emision=factor.factor_emision,
                fecha=today - timedelta(days=(count - index) * 2),
                proveedor=self.provider(fuente, empresa.preset),
                origen_transporte=self.origin(empresa, lote) if is_transport else "",
                destino_transporte=self.destination(empresa, lote) if is_transport else "",
                distancia_km=Decimal(str(round(rng.uniform(8, 280), 3))) if is_transport else None,
                observaciones="Registro validado para seguimiento ambiental y analisis de puntos criticos.",
                metadata=metadata,
            )
            registros.append(registro)
        return registros

    def create_evidences(self, empresa, registros):
        total = 0
        for index, registro in enumerate(registros):
            if index % 3 != 0:
                continue
            evidence = registro.metadata.get("evidence_expected") or "otro"
            content = f"Evidencia Carbono Zero\nEmpresa: {empresa.nombre}\nFuente: {registro.fuente_emision}\nCantidad: {registro.cantidad} {registro.unidad}\nFecha: {registro.fecha}\nEmisiones: {registro.emisiones_kg_co2e} kg CO2e\n"
            evidencia = EvidenciaObra(constructora=empresa, obra=registro.obra, etapa=registro.etapa, registro_emision=registro, lote_forestal=registro.lote_forestal, tipo_evidencia=evidence, estado_documental=EvidenciaObra.EstadoDocumental.VINCULADA, fecha_documento=registro.fecha, nombre=f"Respaldo - {registro.fuente_emision}", observaciones="Documento vinculado al registro ambiental para trazabilidad.", texto_extraido=content, metadata_extraccion={"preset": empresa.preset, "module": registro.metadata.get("module"), "fuente_emision_sugerida": registro.fuente_emision, "categoria_sugerida": registro.categoria, "cantidad_sugerida": str(registro.cantidad), "unidad_sugerida": registro.unidad, "confianza_extraccion": 0.92, "quality_status": "validado"})
            evidencia.archivo.save(f"{empresa.constructora_id}_{registro.id}_{evidence}.txt", ContentFile(content), save=True)
            total += 1
        return total

    def stage_type(self, name):
        name = name.lower()
        if "fund" in name:
            return "Fundaciones"
        if "obra gruesa" in name:
            return "Obra gruesa"
        if "termin" in name:
            return "Terminaciones"
        if "resid" in name:
            return "Retiro de residuos"
        if "excav" in name:
            return "Excavacion"
        if "ruta" in name or "transporte" in name:
            return "Logistica"
        return "Otro"

    def unit_type(self, preset):
        return {"construccion": "Edificio habitacional", "industrial": "Industrial", "transporte": "Infraestructura"}.get(preset, "Otro")

    def provider(self, source, preset):
        source = source.lower()
        if "hormigon" in source:
            return "Hormigones Biobio"
        if "acero" in source:
            return "Aceros del Sur"
        if "diesel" in source or "combustible" in source:
            return "Distribuidora Combustibles Sur"
        if "electricidad" in source:
            return "Distribuidora Electrica Regional"
        if "residuo" in source or "escombro" in source:
            return "Gestor Ambiental Certificado"
        if preset == "aserradero":
            return "Operacion Forestal Integrada"
        return "Proveedor operacional"

    def origin(self, empresa, lote=None):
        return lote.origen if lote else f"{empresa.comuna}, {empresa.region}"

    def destination(self, empresa, lote=None):
        if lote:
            return lote.destino
        if empresa.preset == "transporte":
            return "Centro de distribucion cliente"
        return f"Faena {empresa.comuna}"
