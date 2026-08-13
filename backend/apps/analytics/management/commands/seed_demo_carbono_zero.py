import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import (
    AlertaCumplimientoAmbiental,
    ConfiguracionOrganizacion,
    Organizacion,
    DocumentoAmbiental,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    LimiteNormativoAmbiental,
    LoteForestal,
    Obra,
    RegistroEmision,
    TransporteLoteForestal,
    TransporteObra,
    VariableAmbientalExtraida,
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
    "construccion": {
        "id": "CZP_ORGANIZACION_BIOBIO",
        "name": "Organizacion Bio Bio Infraestructura",
        "rubro": "Construccion",
        "preset": "construccion",
        "region": "Biobio",
        "comuna": "Los Angeles",
        "units": ["Edificio Norte", "Condominio Sur", "Centro Comercial"],
        "stages": ["Excavacion", "Fundaciones", "Obra gruesa", "Terminaciones", "Retiro de residuos"],
        "sources": [
            source("Materiales", "Hormigon H30", "m3", "310.000000", 4, 18, "materiales", "factura_material", 42),
            source("Materiales", "Acero de refuerzo", "ton", "1850.000000", 0.05, 0.42, "materiales", "factura_material", 28),
            source("Maquinaria", "Excavadora diesel", "litros diesel", "2.680000", 18, 96, "maquinaria", "registro_maquinaria", 17),
            source("Transporte", "Diesel camion obra", "litros diesel", "2.680000", 25, 145, "transporte", "factura_combustible", 22),
            source("Residuos", "Retiro de escombros", "kg", "0.080000", 260, 1600, "residuos", "registro_retiro_residuos", 11),
        ],
        "environmental": [
            ("registro_rcd", "Registro mensual RCD", "rcd_ton", "RCD generados", "Residuos", "ton", "12.5", "10.0", "<=", "SINADER"),
            ("medicion_ruido", "Medicion de ruido obra", "noise_db", "Ruido diurno", "Ruido", "dB", "61.0", "60.0", "<=", "DS38"),
            ("factura_combustible", "Factura combustible maquinaria", "diesel_l", "Diesel maquinaria", "Combustible", "L", "820.0", "900.0", "<=", "RETC"),
        ],
    },
    "aserradero": {
        "id": "CZP_ASERRADERO_LAJA",
        "name": "Aserradero Laja",
        "rubro": "Forestal / Aserradero",
        "preset": "aserradero",
        "region": "Biobio",
        "comuna": "Laja",
        "units": ["Planta Aserrio", "Secado Norte", "Patio Trozas"],
        "stages": ["Recepcion de trozas", "Produccion", "Secado", "Energia", "Transporte forestal", "Residuos"],
        "lotes": [
            ("LOTE-PINO-A", "Pino radiata", "84.500", "Predio Santa Clara", "Planta Laja", "Troza aserrable", "420.000", "0.5000"),
            ("LOTE-PINO-B", "Pino radiata", "66.200", "Predio El Roble", "Planta Laja", "Madera estructural", "420.000", "0.5000"),
        ],
        "sources": [
            source("Materiales", "Recepcion de trozas", "m3", "18.000000", 8, 38, "recepcion_trozas", "guia_despacho", 22),
            source("Energia", "Electricidad secado", "kWh", "0.390000", 320, 1800, "secado", "boleta_electrica", 34),
            source("Transporte", "Diesel transporte forestal", "litros diesel", "2.680000", 35, 170, "transporte_forestal", "factura_combustible", 25),
            source("Residuos", "Subproductos de madera", "kg", "0.030000", 220, 1400, "residuos", "registro_retiro_residuos", 10),
        ],
        "environmental": [
            ("registro_subproductos", "Registro de aserrin", "sawdust_ton", "Aserrin generado", "Residuos", "ton", "8.2", "9.0", "<=", "SINADER"),
            ("bitacora_caldera", "Bitacora caldera biomasa", "biomass_boiler_ton", "Biomasa caldera", "Energia", "ton", "18.5", "17.0", "<=", "RCA"),
            ("medicion_ruido", "Medicion ruido planta", "noise_db", "Ruido perimetral", "Ruido", "dB", "58.0", "60.0", "<=", "DS38"),
            ("guia_trozas", "Volumen madera recepcionada", "wood_volume_m3", "Volumen madera", "Produccion", "m3", "84.5", "70.0", ">=", "RCA"),
        ],
    },
    "transporte": {
        "id": "CZP_TRANSPORTE_ANDES",
        "name": "Transporte Andes",
        "rubro": "Transporte y logistica",
        "preset": "transporte",
        "region": "Metropolitana",
        "comuna": "Santiago",
        "units": ["Camion FL-01", "Camion FL-02", "Ruta Centro Sur"],
        "stages": ["Planificacion de rutas", "Operacion de flota", "Combustible", "Mantenciones"],
        "sources": [
            source("Transporte", "Diesel camion ruta", "litros diesel", "2.680000", 45, 250, "combustible", "factura_combustible", 50),
            source("Transporte", "Ruta larga distancia", "km", "0.850000", 60, 520, "rutas", "documento_transporte", 31),
            source("Energia", "Electricidad oficina logistica", "kWh", "0.390000", 90, 420, "flota", "boleta_electrica", 7),
        ],
        "environmental": [
            ("factura_combustible", "Factura diesel flota", "diesel_l", "Diesel flota", "Combustible", "L", "2450.0", "2200.0", "<=", "RETC"),
            ("documento_ruta", "Resumen kilometros ruta", "km_traveled", "Kilometros recorridos", "Rutas", "km", "12800.0", "14000.0", "<=", "RETC"),
            ("registro_residuos", "Registro residuos neumaticos", "tire_waste_kg", "Neumaticos fuera de uso", "Residuos REP", "kg", "460.0", "420.0", "<=", "REP"),
        ],
    },
    "industrial": {
        "id": "CZP_INDUSTRIAS_NAHUELBUTA",
        "name": "Industrias Nahuelbuta",
        "rubro": "Industrial agroindustria",
        "preset": "industrial",
        "region": "Biobio",
        "comuna": "Concepcion",
        "units": ["Linea Produccion A", "Caldera Principal", "Bodega Despacho"],
        "stages": ["Produccion", "Energia", "Caldera", "Residuos industriales", "Transporte interno"],
        "sources": [
            source("Energia", "Electricidad planta", "kWh", "0.390000", 700, 4200, "energia", "boleta_electrica", 43),
            source("Energia", "Diesel caldera", "litros diesel", "2.680000", 55, 340, "produccion", "factura_combustible", 34),
            source("Residuos", "Residuo industrial no peligroso", "kg", "0.120000", 400, 2600, "residuos", "ticket_pesaje", 17),
            source("Agua", "Consumo agua proceso", "m3", "0.450000", 20, 160, "agua", "otro", 11),
        ],
        "environmental": [
            ("informe_laboratorio", "Informe laboratorio RILES", "ph", "pH descarga", "RILES", "pH", "6.8", "6.0", ">=", "DS90"),
            ("informe_laboratorio", "Informe laboratorio RILES", "dbo5", "DBO5", "RILES", "mg/L", "38.0", "35.0", "<=", "DS90"),
            ("informe_laboratorio", "Informe laboratorio RILES", "dqo", "DQO", "RILES", "mg/L", "82.0", "90.0", "<=", "DS90"),
            ("informe_laboratorio", "Informe laboratorio RILES", "sst", "SST", "RILES", "mg/L", "52.0", "50.0", "<=", "DS90"),
            ("manifiesto_respel", "Manifiesto RESPEL", "respel_kg", "Residuos peligrosos", "RESPEL", "kg", "140.0", "150.0", "<=", "SIDREP"),
        ],
    },
    "mineria": {
        "id": "CZP_MINERA_CORDILLERA_SUR",
        "name": "Minera Cordillera Sur",
        "rubro": "Mineria",
        "preset": "industrial",
        "region": "Antofagasta",
        "comuna": "Calama",
        "units": ["Rajo Norte", "Planta Chancado", "Deposito Relaves"],
        "stages": ["Extraccion", "Chancado", "Agua industrial", "Relaves", "Monitoreo aire"],
        "sources": [
            source("Maquinaria", "Diesel maquinaria minera", "litros diesel", "2.680000", 80, 420, "produccion", "factura_combustible", 40),
            source("Energia", "Electricidad planta minera", "kWh", "0.390000", 1200, 6200, "energia", "boleta_electrica", 35),
            source("Agua", "Agua industrial", "m3", "0.450000", 90, 360, "agua", "otro", 15),
        ],
        "environmental": [
            ("balance_agua", "Balance agua industrial", "water_extracted_m3", "Agua extraida", "Agua", "m3", "1280.0", "1200.0", "<=", "RCA"),
            ("balance_agua", "Balance recirculacion", "recirculation_pct", "Recirculacion", "Agua", "%", "82.0", "80.0", ">=", "RCA"),
            ("monitoreo_aire", "Monitoreo MP10", "mp10", "MP10", "Aire", "ug/m3", "152.0", "150.0", "<=", "RCA"),
            ("registro_relaves", "Registro relaves", "tailings_m3", "Relaves", "Residuos mineros", "m3", "840.0", "900.0", "<=", "Sernageomin"),
        ],
    },
    "energia": {
        "id": "CZP_ENERGIA_BIOBIO",
        "name": "Energia Bio Bio",
        "rubro": "Energia generacion",
        "preset": "industrial",
        "region": "Biobio",
        "comuna": "Coronel",
        "units": ["Unidad Generacion 1", "Unidad Generacion 2", "Patio Combustible"],
        "stages": ["Generacion", "Combustion", "Monitoreo CEMS", "Mantencion", "Residuos"],
        "sources": [
            source("Energia", "Generacion termica", "MWh", "0.420000", 200, 900, "energia", "otro", 40),
            source("Energia", "Combustible central", "m3", "2.200000", 30, 160, "produccion", "factura_combustible", 34),
            source("Residuos", "Residuo mantencion central", "kg", "0.120000", 80, 360, "residuos", "registro_retiro_residuos", 12),
        ],
        "environmental": [
            ("cems", "Registro CEMS SO2", "so2", "SO2", "Emisiones atmosfericas", "mg/Nm3", "395.0", "400.0", "<=", "CEMS"),
            ("cems", "Registro CEMS NOx", "nox", "NOx", "Emisiones atmosfericas", "mg/Nm3", "214.0", "200.0", "<=", "CEMS"),
            ("cems", "Registro opacidad", "opacity", "Opacidad", "Emisiones atmosfericas", "%", "18.0", "20.0", "<=", "CEMS"),
            ("reporte_co2", "Reporte CO2 generacion", "co2", "CO2", "GEI", "ton", "980.0", "950.0", "<=", "RETC"),
        ],
    },
}


class Command(BaseCommand):
    help = "Crea empresas piloto realistas de Carbono Zero con registros ambientales historicos."

    def add_arguments(self, parser):
        parser.add_argument("--records", type=int, default=180)
        parser.add_argument("--days", type=int, default=180)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--seed", type=int, default=20260621)

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        count = max(1, int(options["records"]))
        days = max(30, int(options["days"]))
        if options["reset"]:
            self.reset_pilots()
        totals = {"empresas": 0, "etapas": 0, "unidades": 0, "lotes": 0, "factores": 0, "registros": 0, "evidencias": 0, "documentos_ambientales": 0, "variables_ambientales": 0, "limites_ambientales": 0, "alertas_cumplimiento": 0}
        for key, cfg in PILOT_COMPANIES.items():
            result = self.seed_company(key, cfg, count, days, rng)
            for total_key, value in result.items():
                totals[total_key] += value
        self.stdout.write(self.style.SUCCESS("Empresas piloto Carbono Zero creadas correctamente."))
        self.stdout.write(self.style.SUCCESS(str(totals)))

    def reset_pilots(self):
        empresas = Organizacion.objects.filter(Q(organizacion_id__startswith=ACTIVE_PREFIX) | Q(organizacion_id__startswith=LEGACY_PREFIX))
        AlertaCumplimientoAmbiental.objects.filter(organizacion__in=empresas).delete()
        VariableAmbientalExtraida.objects.filter(organizacion__in=empresas).delete()
        DocumentoAmbiental.objects.filter(organizacion__in=empresas).delete()
        LimiteNormativoAmbiental.objects.filter(organizacion__in=empresas).delete()
        TransporteObra.objects.filter(obra__organizacion__in=empresas).delete()
        TransporteLoteForestal.objects.filter(lote_forestal__organizacion__in=empresas).delete()
        EvidenciaObra.objects.filter(organizacion__in=empresas).delete()
        RegistroEmision.objects.filter(organizacion__in=empresas).delete()
        LoteForestal.objects.filter(organizacion__in=empresas).delete()
        Obra.objects.filter(organizacion__in=empresas).delete()
        EtapaObra.objects.filter(organizacion__in=empresas).delete()
        ConfiguracionOrganizacion.objects.filter(organizacion__in=empresas).delete()
        count = empresas.count()
        empresas.delete()
        self.stdout.write(self.style.WARNING(f"Empresas piloto eliminadas: {count}"))

    def seed_company(self, key, cfg, count, days, rng):
        empresa, created = Organizacion.objects.update_or_create(
            organizacion_id=cfg["id"],
            defaults={"nombre": cfg["name"], "rubro": cfg["rubro"], "preset": cfg["preset"], "region": cfg["region"], "comuna": cfg["comuna"], "direccion": f"{cfg['comuna']}, {cfg['region']}", "email": f"ambiental+{key}@carbonozero.cl", "telefono": "+56 9 4321 0000", "contacto": "Equipo ambiental", "observaciones": "Empresa piloto para validar gestion ambiental por industria.", "activa": True},
        )
        ConfiguracionOrganizacion.objects.get_or_create(organizacion=empresa)
        etapas = self.create_stages(empresa, cfg)
        unidades = self.create_units(empresa, etapas, cfg)
        lotes = self.create_lotes(empresa, cfg)
        factores = self.create_factors(cfg)
        registros = self.create_records(empresa, unidades, etapas, lotes, factores, cfg, count, days, rng)
        evidencias = self.create_evidences(empresa, registros)
        environmental = self.create_environmental_compliance(empresa, key, cfg)
        return {"empresas": int(created), "etapas": len(etapas), "unidades": len(unidades), "lotes": len(lotes), "factores": len(factores), "registros": len(registros), "evidencias": evidencias, **environmental}

    def create_stages(self, empresa, cfg):
        etapas = []
        for index, name in enumerate(cfg["stages"], 1):
            etapa, _ = EtapaObra.objects.update_or_create(etapa_id=f"{empresa.organizacion_id}_ETAPA_{index:02d}", defaults={"organizacion": empresa, "nombre": name, "tipo": self.stage_type(name), "region": empresa.region, "comuna": empresa.comuna, "direccion": empresa.direccion, "descripcion": f"Proceso operativo: {name}.", "estado": "activa", "activa": True})
            etapas.append(etapa)
        return etapas

    def create_units(self, empresa, etapas, cfg):
        unidades = []
        start = timezone.localdate() - timedelta(days=180)
        for index, name in enumerate(cfg["units"], 1):
            etapa = etapas[(index - 1) % len(etapas)]
            unidad, _ = Obra.objects.update_or_create(codigo_obra=f"{empresa.organizacion_id}_UNIDAD_{index:02d}", defaults={"organizacion": empresa, "etapa_principal": etapa, "nombre": name, "tipo_proyecto": self.unit_type(empresa.preset), "fecha_inicio": start + timedelta(days=index * 8), "fecha_termino_estimada": timezone.localdate() + timedelta(days=90), "superficie_m2": Decimal(str(1200 + index * 740)), "ubicacion": f"{empresa.comuna}, {empresa.region}", "region": empresa.region, "comuna": empresa.comuna, "mandante": "Mandante de referencia", "estado": "en_ejecucion", "descripcion": f"Unidad operativa para medicion ambiental de {empresa.rubro}."})
            unidades.append(unidad)
        return unidades

    def create_lotes(self, empresa, cfg):
        lotes = []
        start = timezone.localdate() - timedelta(days=90)
        for index, item in enumerate(cfg.get("lotes", []), 1):
            lote_id, especie, volumen, origen, destino, producto, densidad, carbono = item
            lote, _ = LoteForestal.objects.update_or_create(lote_id=f"{empresa.organizacion_id}_{lote_id}", defaults={"organizacion": empresa, "fecha": start + timedelta(days=index * 14), "especie": especie, "volumen_m3": Decimal(volumen), "origen": origen, "destino": destino, "tipo_producto": producto, "densidad_kg_m3": Decimal(densidad), "porcentaje_carbono": Decimal(carbono), "estado": "activo", "observaciones": "Lote trazable para balance neto, transporte y evidencias.", "metadata": {"preset": "aserradero", "module": "lotes_forestales", "quality_status": "validado"}})
            lotes.append(lote)
        return lotes

    def create_factors(self, cfg):
        factors = {}
        for item in cfg["sources"]:
            factor, _ = FactorEmision.objects.update_or_create(actividad=item["fuente"], unidad=item["unidad"], fuente=f"Factor de referencia Carbono Zero {YEAR}", anio=YEAR, defaults={"preset": cfg["preset"], "module": item["module"], "categoria": item["categoria"], "factor_emision": item["factor"], "alcance": "Referencia operativa", "descripcion": f"Factor usado para calcular emisiones de {item['fuente']}.", "metadata": {"preset": cfg["preset"], "module": item["module"], "quality_status": "validado"}, "activo": True})
            factors[item["fuente"]] = factor
        return factors

    def create_records(self, empresa, unidades, etapas, lotes, factors, cfg, count, days, rng):
        registros = []
        today = timezone.localdate()
        weighted = []
        for item in cfg["sources"]:
            weighted.extend([item] * max(1, item["weight"]))
        for index in range(count):
            item = rng.choice(weighted)
            factor = factors[item["fuente"]]
            obra = unidades[index % len(unidades)]
            etapa = etapas[index % len(etapas)]
            lote = rng.choice(lotes) if lotes else None
            cantidad = Decimal(str(round(rng.uniform(float(item["min"]), float(item["max"])), 3)))
            is_transport = item["categoria"] == "Transporte"
            metadata = {"preset": empresa.preset, "module": item["module"], "source_profile": item["fuente"], "quality_status": "validado", "evidence_expected": item["evidence"]}
            if lote:
                metadata["lote"] = lote.lote_id
            registro = RegistroEmision.objects.create(organizacion=empresa, obra=obra, etapa=etapa, lote_forestal=lote, categoria=item["categoria"], fuente_emision=item["fuente"], cantidad=cantidad, unidad=item["unidad"], factor_emision=factor.factor_emision, fecha=today - timedelta(days=max(0, days - int((index / max(count, 1)) * days))), proveedor=self.provider(item["fuente"], empresa.preset), origen_transporte=self.origin(empresa, lote) if is_transport else "", destino_transporte=self.destination(empresa, lote) if is_transport else "", distancia_km=Decimal(str(round(rng.uniform(8, 280), 3))) if is_transport else None, observaciones="Registro validado para seguimiento ambiental y analisis de puntos criticos.", metadata=metadata)
            registros.append(registro)
        return registros

    def create_evidences(self, empresa, registros):
        total = 0
        for index, registro in enumerate(registros):
            if index % 3 != 0:
                continue
            evidence = registro.metadata.get("evidence_expected") or "otro"
            content = f"Evidencia Carbono Zero\nEmpresa: {empresa.nombre}\nFuente: {registro.fuente_emision}\nCantidad: {registro.cantidad} {registro.unidad}\nFecha: {registro.fecha}\nEmisiones: {registro.emisiones_kg_co2e} kg CO2e\n"
            evidencia = EvidenciaObra(organizacion=empresa, obra=registro.obra, etapa=registro.etapa, registro_emision=registro, lote_forestal=registro.lote_forestal, tipo_evidencia=evidence, estado_documental=EvidenciaObra.EstadoDocumental.VINCULADA, fecha_documento=registro.fecha, nombre=f"Respaldo - {registro.fuente_emision}", observaciones="Documento vinculado al registro ambiental para trazabilidad.", texto_extraido=content, metadata_extraccion={"preset": empresa.preset, "module": registro.metadata.get("module"), "fuente_emision_sugerida": registro.fuente_emision, "categoria_sugerida": registro.categoria, "cantidad_sugerida": str(registro.cantidad), "unidad_sugerida": registro.unidad, "confianza_extraccion": 0.92, "quality_status": "validado"})
            evidencia.archivo.save(f"{empresa.organizacion_id}_{registro.id}_{evidence}.txt", ContentFile(content), save=True)
            total += 1
        return total

    def create_environmental_compliance(self, empresa, industry_key, cfg):
        created_docs = created_variables = created_limits = 0
        today = timezone.localdate()
        for index, item in enumerate(cfg.get("environmental", []), 1):
            tipo, doc_name, variable_id, variable_name, categoria, unidad, valor, limite, comparador, normativa = item
            limite_obj, limite_created = LimiteNormativoAmbiental.objects.update_or_create(organizacion=empresa, variable_id=variable_id, normativa=normativa, defaults={"industria": industry_key, "nombre": variable_name, "limite": Decimal(limite), "unidad": unidad, "comparador": comparador, "activo": True, "descripcion": f"Limite operativo para {variable_name}.", "metadata": {"seed": True, "industria": industry_key}})
            documento, doc_created = DocumentoAmbiental.objects.update_or_create(organizacion=empresa, tipo_documento=tipo, nombre=doc_name, defaults={"industria": industry_key, "fecha_documento": today - timedelta(days=index * 7), "periodo_inicio": today - timedelta(days=index * 7 + 30), "periodo_fin": today - timedelta(days=index * 7), "fuente_origen": "manual", "estado_procesamiento": "extraido", "estado_validacion": "valido", "resumen": f"Registro ambiental estructurado para {variable_name}.", "metadata": {"seed": True, "normativa": normativa}})
            _, variable_created = VariableAmbientalExtraida.objects.update_or_create(documento=documento, organizacion=empresa, variable_id=variable_id, defaults={"nombre": variable_name, "categoria": categoria, "valor": Decimal(valor), "unidad": unidad, "fecha_medicion": documento.fecha_documento, "punto_medicion": "Punto principal", "limite_aplicable": limite_obj.limite, "unidad_limite": limite_obj.unidad, "confianza_extraccion": Decimal("0.92"), "metadata": {"normativa": normativa, "comparador_limite": limite_obj.comparador, "limite_id": limite_obj.id, "seed": True}})
            created_docs += int(doc_created)
            created_variables += int(variable_created)
            created_limits += int(limite_created)
        return {"documentos_ambientales": created_docs, "variables_ambientales": created_variables, "limites_ambientales": created_limits, "alertas_cumplimiento": AlertaCumplimientoAmbiental.objects.filter(organizacion=empresa).count()}

    def stage_type(self, name):
        text = name.lower()
        if "fund" in text:
            return "Fundaciones"
        if "obra gruesa" in text:
            return "Obra gruesa"
        if "termin" in text:
            return "Terminaciones"
        if "resid" in text:
            return "Retiro de residuos"
        if "excav" in text:
            return "Excavacion"
        if "ruta" in text or "transporte" in text:
            return "Logistica"
        return "Otro"

    def unit_type(self, preset):
        return {"construccion": "Edificio habitacional", "industrial": "Industrial", "transporte": "Infraestructura"}.get(preset, "Otro")

    def provider(self, source_name, preset):
        source_name = source_name.lower()
        if "hormigon" in source_name:
            return "Hormigones Biobio"
        if "acero" in source_name:
            return "Aceros del Sur"
        if "diesel" in source_name or "combustible" in source_name:
            return "Distribuidora Combustibles Sur"
        if "electricidad" in source_name:
            return "Distribuidora Electrica Regional"
        if "residuo" in source_name or "escombro" in source_name:
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
