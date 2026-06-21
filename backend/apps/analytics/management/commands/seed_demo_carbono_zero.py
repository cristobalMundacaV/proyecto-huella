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
    ConfiguracionConstructora,
    Constructora,
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
    "constructora": {
        "id": "CZP_CONSTRUCTORA_BIOBIO",
        "name": "Constructora Bío Bío Infraestructura",
        "rubro": "Construcción",
        "preset": "construccion",
        "region": "Biobío",
        "comuna": "Los Ángeles",
        "units": ["Edificio Centro", "Urbanización Norte", "Obra Vial Acceso Sur"],
        "stages": ["Excavacion", "Fundaciones", "Obra gruesa", "Terminaciones", "Retiro de residuos"],
        "sources": [
            source("Materiales", "Hormigón H30", "m3", "310.000000", 4, 22, "materiales", "factura_material", 36),
            source("Materiales", "Acero de refuerzo", "ton", "1850.000000", "0.05", "0.50", "materiales", "factura_material", 18),
            source("Maquinaria", "Excavadora diésel", "litros diesel", "2.680000", 18, 110, "maquinaria", "registro_maquinaria", 18),
            source("Transporte", "Camión tolva obra", "litros diesel", "2.680000", 25, 150, "transporte", "factura_combustible", 18),
            source("Residuos", "Retiro de escombros RCD", "kg", "0.080000", 260, 1800, "residuos", "ticket_pesaje", 10),
        ],
        "environmental": [
            ("registro_rcd", "Registro mensual RCD", "rcd_ton", "RCD generados", "Residuos", "ton", "12.5", "10.0", "<=", "SINADER"),
            ("medicion_ruido", "Medición de ruido obra", "noise_db", "Ruido diurno", "Ruido", "dB(A)", "61.0", "60.0", "<=", "DS38"),
            ("factura_combustible", "Factura combustible maquinaria", "diesel_l", "Diésel maquinaria", "Combustible", "L", "820.0", "900.0", "<=", "RETC"),
        ],
    },
    "aserradero": {
        "id": "CZP_ASERRADERO_LAJA",
        "name": "Aserradero Laja Sur",
        "rubro": "Forestal / Aserradero",
        "preset": "aserradero",
        "region": "Biobío",
        "comuna": "Laja",
        "units": ["Línea Aserrío", "Secado Cámara 1", "Patio Trozas"],
        "stages": ["Recepcion de trozas", "Produccion", "Secado", "Energia", "Transporte forestal", "Residuos y subproductos"],
        "sources": [
            source("Materiales", "Recepción de trozas", "m3", "18.000000", 8, 42, "recepcion_trozas", "guia_despacho", 26),
            source("Procesos externos", "Proceso de aserrío", "m3", "22.000000", 7, 34, "produccion", "registro_produccion", 20),
            source("Energia", "Electricidad secado", "kWh", "0.390000", 320, 1900, "secado", "boleta_electrica", 26),
            source("Transporte", "Diésel transporte forestal", "litros diesel", "2.680000", 35, 180, "transporte_forestal", "factura_combustible", 18),
            source("Residuos", "Subproductos de madera", "kg", "0.030000", 220, 1500, "residuos_subproductos", "registro_retiro_residuos", 10),
        ],
        "environmental": [
            ("registro_subproductos", "Registro de aserrín", "sawdust_ton", "Aserrín generado", "Residuos", "ton", "8.2", "9.0", "<=", "SINADER"),
            ("bitacora_caldera", "Bitácora caldera biomasa", "biomass_boiler_ton", "Biomasa caldera", "Energia", "ton", "18.5", "17.0", "<=", "RCA"),
            ("medicion_ruido", "Medición ruido planta", "noise_db", "Ruido perimetral", "Ruido", "dB(A)", "58.0", "60.0", "<=", "DS38"),
            ("guia_trozas", "Volumen madera recepcionada", "wood_volume_m3", "Volumen madera", "Produccion", "m3", "84.5", "70.0", ">=", "RCA"),
        ],
        "lotes": [
            ("LOTE-PINO-A", "Pino radiata", "84.500", "Predio Santa Clara", "Planta Laja", "Troza aserrable"),
            ("LOTE-PINO-B", "Pino radiata", "66.200", "Predio El Roble", "Planta Laja", "Madera estructural"),
        ],
    },
    "transporte": {
        "id": "CZP_TRANSPORTE_ANDES",
        "name": "Transportes Andes del Sur",
        "rubro": "Transporte y logística",
        "preset": "transporte",
        "region": "Metropolitana",
        "comuna": "Santiago",
        "units": ["Camión FL-01", "Camión FL-02", "Ruta Centro Sur"],
        "stages": ["Planificacion de rutas", "Operacion de flota", "Combustible", "Mantenciones", "Carga y distribucion"],
        "sources": [
            source("Transporte", "Diésel camión ruta", "litros diesel", "2.680000", 45, 260, "combustible", "factura_combustible", 55),
            source("Transporte", "Ruta larga distancia", "km", "0.850000", 60, 540, "rutas", "documento_transporte", 30),
            source("Maquinaria", "Mantención flota", "unidad", "35.000000", 1, 4, "mantenciones", "otro", 8),
            source("Residuos", "Neumáticos fuera de uso", "kg", "0.120000", 20, 160, "mantenciones", "registro_retiro_residuos", 7),
        ],
        "environmental": [
            ("factura_combustible", "Factura combustible flota", "diesel_l", "Diésel flota", "Combustible", "L", "2450.0", "2300.0", "<=", "RETC"),
            ("hoja_ruta", "Hoja de ruta mensual", "km_traveled", "Km recorridos", "Transporte", "km", "14500.0", "13000.0", "<=", "RCA"),
            ("registro_neumaticos", "Registro neumáticos usados", "tire_waste_kg", "Neumáticos", "Residuos", "kg", "280.0", "250.0", "<=", "REP"),
        ],
    },
    "industrial": {
        "id": "CZP_INDUSTRIAS_NAHUELBUTA",
        "name": "Industrias Nahuelbuta SpA",
        "rubro": "Industrial / Agroindustria",
        "preset": "industrial",
        "region": "Biobío",
        "comuna": "Nacimiento",
        "units": ["Planta Proceso", "Caldera", "Tratamiento RILES"],
        "stages": ["Procesos", "Energia", "Combustible", "RILES", "Residuos"],
        "sources": [
            source("Energia", "Electricidad planta", "kWh", "0.390000", 800, 4800, "energia", "boleta_electrica", 30),
            source("Combustible", "Gas caldera", "m3 gas", "2.050000", 120, 820, "combustibles", "factura_combustible", 24),
            source("Residuos", "Residuo no peligroso", "kg", "0.060000", 180, 1300, "residuos", "ticket_pesaje", 16),
            source("Agua", "Agua proceso", "m3", "0.180000", 70, 420, "riles", "otro", 10),
        ],
        "environmental": [
            ("informe_riles", "Informe RILES DBO5", "dbo5", "DBO5", "RILES", "mg/L", "420.0", "300.0", "<=", "DS90"),
            ("informe_riles", "Informe RILES pH", "ph", "pH", "RILES", "pH", "7.2", "9.0", "<=", "DS90"),
            ("manifiesto_respel", "Manifiesto RESPEL aceites", "respel_kg", "RESPEL", "Residuos peligrosos", "kg", "180.0", "200.0", "<=", "SIDREP"),
        ],
    },
    "mineria": {
        "id": "CZP_MINERA_CORDILLERA_SUR",
        "name": "Minera Cordillera Sur SpA",
        "rubro": "Minería",
        "preset": "industrial",
        "region": "Antofagasta",
        "comuna": "Calama",
        "units": ["Faena Norte", "Planta Chancado", "Depósito Relaves"],
        "stages": ["Extraccion", "Procesos", "Agua", "Relaves", "Monitoreos"],
        "sources": [
            source("Combustible", "Diésel camión extracción", "litros diesel", "2.680000", 90, 520, "combustible", "factura_combustible", 40),
            source("Energia", "Electricidad chancado", "kWh", "0.390000", 1500, 9000, "energia", "boleta_electrica", 24),
            source("Agua", "Agua captada proceso", "m3", "0.180000", 120, 760, "agua", "otro", 18),
            source("Residuos", "Residuo peligroso faena", "kg", "0.090000", 80, 600, "residuos", "registro_retiro_residuos", 18),
        ],
        "environmental": [
            ("registro_agua", "Registro hidrológico", "water_extracted_m3", "Agua captada", "Agua", "m3", "760.0", "700.0", "<=", "RCA"),
            ("monitoreo_mp10", "Monitoreo MP10", "mp10", "MP10", "Aire", "ug/m3", "155.0", "150.0", "<=", "RCA"),
            ("reporte_relaves", "Reporte relaves", "tailings_m3", "Relaves", "Relaves", "m3", "4800.0", "5000.0", "<=", "Sernageomin"),
        ],
    },
    "energia": {
        "id": "CZP_ENERGIA_BIOBIO",
        "name": "Energía Biobío Generación",
        "rubro": "Energía / Termoeléctrica",
        "preset": "industrial",
        "region": "Biobío",
        "comuna": "Coronel",
        "units": ["Unidad Generadora 1", "Chimenea Principal", "Patio Combustible"],
        "stages": ["Generacion", "CEMS", "Combustible", "Mantencion", "Residuos"],
        "sources": [
            source("Combustible", "Combustible unidad generadora", "ton", "3150.000000", 1, 8, "combustible", "factura_combustible", 42),
            source("Energia", "Generación eléctrica", "MWh", "0.000000", 600, 2800, "energia", "otro", 28),
            source("Residuos", "Cenizas", "kg", "0.050000", 300, 2600, "residuos", "ticket_pesaje", 16),
        ],
        "environmental": [
            ("log_cems", "Log CEMS SO2", "so2_mg_m3", "SO2", "Aire", "mg/m3", "145.0", "150.0", "<=", "CEMS"),
            ("log_cems", "Log CEMS NOx", "nox_mg_m3", "NOx", "Aire", "mg/m3", "210.0", "200.0", "<=", "CEMS"),
            ("log_cems", "Opacidad chimenea", "opacity_pct", "Opacidad", "Aire", "%", "18.0", "20.0", "<=", "CEMS"),
        ],
    },
}


class Command(BaseCommand):
    help = "Crea empresas piloto realistas para probar Carbono Zero."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Elimina datos piloto CZP_ y legacy antes de crear nuevos.")
        parser.add_argument("--records", type=int, default=180, help="Registros de emisión por empresa.")
        parser.add_argument("--days", type=int, default=180, help="Ventana de días hacia atrás para distribuir datos.")
        parser.add_argument("--seed", type=int, default=42, help="Semilla determinística.")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(options["seed"])
        if options["reset"]:
            self.reset_pilot_data()

        total_records = 0
        total_docs = 0
        total_variables = 0
        for profile in PILOT_COMPANIES.values():
            company, stages, units = self.create_company_base(profile)
            self.create_lotes(profile, company)
            total_records += self.create_emission_records(company, stages, units, profile, options["records"], options["days"])
            docs, variables = self.create_environmental_compliance(company, profile)
            total_docs += docs
            total_variables += variables

        self.stdout.write(self.style.SUCCESS(f"Empresas piloto creadas: {len(PILOT_COMPANIES)}"))
        self.stdout.write(self.style.SUCCESS(f"Registros de emisión creados: {total_records}"))
        self.stdout.write(self.style.SUCCESS(f"Documentos ambientales creados: {total_docs}"))
        self.stdout.write(self.style.SUCCESS(f"Variables ambientales creadas: {total_variables}"))

    def reset_pilot_data(self):
        companies = Constructora.objects.filter(Q(constructora_id__startswith=ACTIVE_PREFIX) | Q(constructora_id__startswith=LEGACY_PREFIX))
        company_ids = list(companies.values_list("id", flat=True))
        if not company_ids:
            return
        qs = Constructora.objects.filter(id__in=company_ids)
        AlertaCumplimientoAmbiental.objects.filter(constructora__in=qs).delete()
        VariableAmbientalExtraida.objects.filter(constructora__in=qs).delete()
        LimiteNormativoAmbiental.objects.filter(constructora__in=qs).delete()
        DocumentoAmbiental.objects.filter(constructora__in=qs).delete()
        EvidenciaObra.objects.filter(constructora__in=qs).delete()
        RegistroEmision.objects.filter(constructora__in=qs).delete()
        TransporteObra.objects.filter(obra__constructora__in=qs).delete()
        TransporteLoteForestal.objects.filter(lote_forestal__constructora__in=qs).delete()
        LoteForestal.objects.filter(constructora__in=qs).delete()
        Obra.objects.filter(constructora__in=qs).delete()
        EtapaObra.objects.filter(constructora__in=qs).delete()
        ConfiguracionConstructora.objects.filter(constructora__in=qs).delete()
        qs.delete()

    def create_company_base(self, profile):
        company, _ = Constructora.objects.update_or_create(
            constructora_id=profile["id"],
            defaults={
                "nombre": profile["name"],
                "rubro": profile["rubro"],
                "preset": profile["preset"],
                "region": profile["region"],
                "comuna": profile["comuna"],
                "activa": True,
                "email": f"ambiental@{profile['id'].lower()}.cl",
                "telefono": "+56 43 220 0000",
                "contacto": "Encargado ambiental",
                "observaciones": "Empresa piloto con datos operacionales y ambientales para validación funcional.",
            },
        )
        ConfiguracionConstructora.objects.update_or_create(
            constructora=company,
            defaults={
                "modo_importacion": "estricto",
                "requerir_obra_registro": False,
                "requerir_etapa_obra": False,
                "evidencia_obligatoria": True,
                "permitir_registros_sin_factor": False,
            },
        )
        stages = [
            EtapaObra.objects.create(
                constructora=company,
                nombre=stage,
                tipo=self.stage_type(stage),
                region=profile["region"],
                comuna=profile["comuna"],
                descripcion=f"Etapa operacional {stage} para {profile['name']}.",
            )
            for stage in profile["stages"]
        ]
        units = [
            Obra.objects.create(
                constructora=company,
                etapa_principal=random.choice(stages),
                nombre=unit,
                tipo_proyecto="Industrial" if profile["preset"] == "industrial" else "Otro",
                fecha_inicio=timezone.localdate() - timedelta(days=240),
                fecha_termino_estimada=timezone.localdate() + timedelta(days=180),
                superficie_m2=Decimal(str(random.randint(1200, 9000))),
                ubicacion=f"{profile['comuna']}, {profile['region']}",
                region=profile["region"],
                comuna=profile["comuna"],
                mandante=profile["name"],
                descripcion=f"Unidad operacional para validación ambiental: {unit}.",
            )
            for unit in profile["units"]
        ]
        return company, stages, units

    def create_lotes(self, profile, company):
        for lote in profile.get("lotes", []):
            LoteForestal.objects.update_or_create(
                lote_id=f"{company.constructora_id}_{lote[0]}",
                defaults={
                    "constructora": company,
                    "fecha": timezone.localdate() - timedelta(days=random.randint(5, 90)),
                    "especie": lote[1],
                    "volumen_m3": Decimal(lote[2]),
                    "origen": lote[3],
                    "destino": lote[4],
                    "tipo_producto": lote[5],
                    "densidad_kg_m3": Decimal("420.000"),
                    "porcentaje_carbono": Decimal("0.5000"),
                    "estado": "Recepcionado",
                },
            )

    def create_emission_records(self, company, stages, units, profile, records, days):
        created = 0
        sources = profile["sources"]
        weights = [item["weight"] for item in sources]
        for index in range(records):
            item = random.choices(sources, weights=weights, k=1)[0]
            amount = self.random_decimal(item["min"], item["max"])
            factor = self.get_factor(company.preset, item)
            date = timezone.localdate() - timedelta(days=random.randint(0, days))
            unit = random.choice(units)
            stage = random.choice(stages)
            record = RegistroEmision.objects.create(
                constructora=company,
                obra=unit,
                etapa=stage,
                categoria=item["categoria"],
                fuente_emision=item["fuente"],
                cantidad=amount,
                unidad=item["unidad"],
                factor_emision=item["factor"],
                fecha=date,
                proveedor=random.choice(["Proveedor local", "Operador interno", "Contratista ambiental", "Servicio externo"]),
                distancia_km=Decimal(str(random.randint(5, 380))) if item["categoria"] == "Transporte" else None,
                metadata={"module": item["module"], "factor_id": factor.id, "pilot": True},
                observaciones=f"Registro operacional de {item['fuente']} para análisis ambiental.",
            )
            if index % 2 == 0:
                self.create_evidence(company, unit, stage, record, item, date)
            created += 1
        return created

    def create_environmental_compliance(self, company, profile):
        documents = 0
        variables = 0
        for doc_type, doc_name, variable_id, variable_name, category, unit, value, limit, comparator, regulation in profile["environmental"]:
            limite = LimiteNormativoAmbiental.objects.create(
                constructora=company,
                industria=profile["rubro"],
                variable_id=variable_id,
                nombre=f"Límite {variable_name}",
                normativa=regulation,
                limite=Decimal(limit),
                unidad=unit,
                comparador=comparator,
                activo=True,
                descripcion=f"Umbral de control para {variable_name} en {company.nombre}.",
            )
            document = DocumentoAmbiental.objects.create(
                constructora=company,
                tipo_documento=doc_type,
                industria=profile["rubro"],
                nombre=doc_name,
                fecha_documento=timezone.localdate() - timedelta(days=random.randint(1, 45)),
                periodo_inicio=timezone.localdate() - timedelta(days=45),
                periodo_fin=timezone.localdate(),
                fuente_origen="manual",
                estado_procesamiento="extraido",
                estado_validacion="valido",
                resumen=f"Documento ambiental validado para {variable_name}.",
                metadata={"pilot": True, "normativa": regulation},
            )
            VariableAmbientalExtraida.objects.create(
                documento=document,
                constructora=company,
                variable_id=variable_id,
                nombre=variable_name,
                categoria=category,
                valor=Decimal(value),
                unidad=unit,
                fecha_medicion=document.fecha_documento,
                punto_medicion=random.choice(profile["units"]),
                limite_aplicable=limite.limite,
                unidad_limite=limite.unidad,
                confianza_extraccion=Decimal("0.92"),
                metadata={"comparador_limite": comparator, "normativa": regulation, "limite_id": limite.id, "pilot": True},
            )
            documents += 1
            variables += 1
        return documents, variables

    def get_factor(self, preset, item):
        factor, _ = FactorEmision.objects.update_or_create(
            actividad=item["fuente"],
            unidad=item["unidad"],
            fuente="Factor piloto Carbono Zero",
            anio=YEAR,
            defaults={
                "preset": preset if preset in {"construccion", "aserradero", "transporte", "industrial"} else "industrial",
                "module": item["module"],
                "categoria": item["categoria"] if item["categoria"] in dict(FactorEmision.Categoria.choices) else "Otros",
                "factor_emision": item["factor"],
                "alcance": "Alcance 1/2/3",
                "descripcion": "Factor piloto para validación funcional.",
                "activo": True,
            },
        )
        return factor

    def create_evidence(self, company, unit, stage, record, item, date):
        filename = f"{company.constructora_id}_{record.id}_{item['evidence']}.txt"
        EvidenciaObra.objects.create(
            constructora=company,
            obra=unit,
            etapa=stage,
            registro_emision=record,
            tipo_evidencia=item["evidence"] if item["evidence"] in dict(EvidenciaObra.TipoEvidencia.choices) else "otro",
            estado_documental="validada",
            fecha_documento=date,
            archivo=ContentFile(f"Evidencia piloto para {record.fuente_emision}\n", name=filename),
            nombre=f"Respaldo {record.fuente_emision}",
            observaciones="Evidencia generada para probar trazabilidad ambiental.",
            metadata_extraccion={"pilot": True, "module": item["module"]},
        )

    def random_decimal(self, lower, upper):
        value = random.uniform(float(lower), float(upper))
        return Decimal(str(round(value, 3)))

    def stage_type(self, name):
        normalized = str(name).lower()
        if "excav" in normalized:
            return "Excavacion"
        if "fund" in normalized:
            return "Fundaciones"
        if "gruesa" in normalized:
            return "Obra gruesa"
        if "termin" in normalized:
            return "Terminaciones"
        if "resid" in normalized:
            return "Retiro de residuos"
        if "log" in normalized or "ruta" in normalized or "transporte" in normalized:
            return "Logistica"
        if "energia" in normalized or "combustible" in normalized or "mantencion" in normalized:
            return "Instalaciones"
        return "Otro"
