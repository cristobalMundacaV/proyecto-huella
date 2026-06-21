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
    "construccion": {
        "id": "CZP_CONSTRUCTORA_BIOBIO",
        "name": "Constructora Bio Bio Infraestructura",
        "rubro": "Construccion",
        "preset": "construccion",
<<<<<<< HEAD
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
        "comuna": "Los Angeles",
        "units": ["Planta Aserrio", "Secado Norte", "Patio Trozas"],
        "stages": ["Recepcion de trozas", "Produccion", "Secado", "Energia", "Transporte forestal", "Residuos"],
        "lotes": [
            ("LOTE-PINO-A", "Pino radiata", "84.500", "Predio Santa Clara", "Planta Los Angeles", "Troza aserrable", "420.000", "0.5000"),
            ("LOTE-PINO-B", "Pino radiata", "66.200", "Predio El Roble", "Planta Los Angeles", "Madera estructural", "420.000", "0.5000"),
            ("LOTE-EUCA-C", "Eucalipto", "52.700", "Predio Las Vertientes", "Planta Los Angeles", "Madera seca", "560.000", "0.4800"),
        ],
        "sources": [
            source("Materiales", "Recepcion de trozas", "m3", "18.000000", 8, 38, "recepcion_trozas", "guia_despacho", 22),
            source("Procesos externos", "Proceso de aserrio", "m3", "22.000000", 7, 34, "produccion", "registro_produccion", 18),
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
            source("Maquinaria", "Mantencion flota", "unidad", "35.000000", 1, 4, "mantenciones", "otro", 9),
            source("Energia", "Electricidad oficina logistica", "kWh", "0.390000", 90, 420, "flota", "boleta_electrica", 7),
        ],
        "environmental": [
            ("factura_combustible", "Factura diesel flota", "diesel_l", "Diesel flota", "Combustible", "L", "2450.0", "2200.0", "<=", "RETC"),
            ("documento_ruta", "Resumen kilometros ruta", "km_traveled", "Kilometros recorridos", "Rutas", "km", "12800.0", "14000.0", "<=", "RETC"),
            ("registro_residuos", "Registro residuos neumaticos", "tire_waste_kg", "Neumaticos fuera de uso", "Residuos REP", "kg", "460.0", "420.0", "<=", "REP"),
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
        ],
    },
    "industrial": {
        "id": "CZP_INDUSTRIAS_NAHUELBUTA",
<<<<<<< HEAD
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
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
        ],
    },
    "energia": {
        "id": "CZP_ENERGIA_BIOBIO",
<<<<<<< HEAD
        "name": "Energia Bio Bio",
        "rubro": "Energia generacion",
        "preset": "industrial",
        "region": "Valparaiso",
        "comuna": "Quintero",
        "units": ["Unidad Generacion 1", "Unidad Generacion 2", "Patio Combustible"],
        "stages": ["Generacion", "Combustion", "Monitoreo CEMS", "Mantencion", "Residuos"],
        "sources": [
            source("Energia", "Generacion termica", "MWh", "0.420000", 200, 900, "energia", "otro", 40),
            source("Energia", "Combustible central", "m3", "2.200000", 30, 160, "produccion", "factura_combustible", 34),
            source("Residuos", "Residuo mantencion central", "kg", "0.120000", 80, 360, "residuos", "registro_retiro_residuos", 12),
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
        ],
        "environmental": [
            ("log_cems", "Log CEMS SO2", "so2_mg_m3", "SO2", "Aire", "mg/m3", "145.0", "150.0", "<=", "CEMS"),
            ("log_cems", "Log CEMS NOx", "nox_mg_m3", "NOx", "Aire", "mg/m3", "210.0", "200.0", "<=", "CEMS"),
            ("log_cems", "Opacidad chimenea", "opacity_pct", "Opacidad", "Aire", "%", "18.0", "20.0", "<=", "CEMS"),
        ],
    },
}


class Command(BaseCommand):
<<<<<<< HEAD
    help = "Crea empresas piloto realistas de Carbono Zero con registros ambientales historicos."

    def add_arguments(self, parser):
        parser.add_argument("--records", type=int, default=180, help="Cantidad de registros por empresa.")
        parser.add_argument("--days", type=int, default=180, help="Ventana historica en dias.")
        parser.add_argument("--reset", action="store_true", help="Elimina empresas piloto anteriores antes de crear datos.")
        parser.add_argument("--seed", type=int, default=20260621, help="Semilla deterministica para reproducir los datos.")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        records_per_company = max(1, int(options["records"]))
        days = max(30, int(options["days"]))
        if options["reset"]:
            self.reset_pilots()

        totals = {
            "empresas": 0,
            "etapas": 0,
            "unidades": 0,
            "lotes": 0,
            "factores": 0,
            "registros": 0,
            "evidencias": 0,
            "documentos_ambientales": 0,
            "variables_ambientales": 0,
            "limites_ambientales": 0,
            "alertas_cumplimiento": 0,
        }
        for key, cfg in PILOT_COMPANIES.items():
            result = self.seed_company(key, cfg, records_per_company, days, rng)
            for total_key, value in result.items():
                totals[total_key] += value

        self.stdout.write(self.style.SUCCESS("Empresas piloto Carbono Zero creadas correctamente."))
        self.stdout.write(self.style.SUCCESS(str(totals)))

    def reset_pilots(self):
        query = Q(constructora_id__startswith=ACTIVE_PREFIX) | Q(constructora_id__startswith=LEGACY_PREFIX)
        empresas = Constructora.objects.filter(query)
        AlertaCumplimientoAmbiental.objects.filter(constructora__in=empresas).delete()
        VariableAmbientalExtraida.objects.filter(constructora__in=empresas).delete()
        DocumentoAmbiental.objects.filter(constructora__in=empresas).delete()
        LimiteNormativoAmbiental.objects.filter(constructora__in=empresas).delete()
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
                "email": f"ambiental+{key}@carbonozero.cl",
                "telefono": "+56 9 4321 0000",
                "contacto": "Equipo ambiental",
                "observaciones": "Empresa piloto para validar gestion ambiental por industria.",
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
                "activa": True,
                "email": f"ambiental@{profile['id'].lower()}.cl",
                "telefono": "+56 43 220 0000",
                "contacto": "Encargado ambiental",
                "observaciones": "Empresa piloto con datos operacionales y ambientales para validación funcional.",
            },
        )
<<<<<<< HEAD
        ConfiguracionConstructora.objects.get_or_create(constructora=empresa)
        etapas = self.create_stages(empresa, cfg)
        unidades = self.create_units(empresa, etapas, cfg)
        lotes = self.create_lotes(empresa, cfg)
        factores = self.create_factors(cfg)
        registros = self.create_records(empresa, unidades, etapas, lotes, factores, cfg, records_per_company, days, rng)
        evidencias = self.create_evidences(empresa, registros)
        environmental = self.create_environmental_compliance(empresa, key, cfg)
        return {
            "empresas": int(created),
            "etapas": len(etapas),
            "unidades": len(unidades),
            "lotes": len(lotes),
            "factores": len(factores),
            "registros": len(registros),
            "evidencias": evidencias,
            **environmental,
        }
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f

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

<<<<<<< HEAD
    def create_units(self, empresa, etapas, cfg):
        unidades = []
        start = timezone.localdate() - timedelta(days=180)
        for index, name in enumerate(cfg["units"], 1):
            etapa = etapas[(index - 1) % len(etapas)]
            unidad, _ = Obra.objects.update_or_create(
                codigo_obra=f"{empresa.constructora_id}_UNIDAD_{index:02d}",
                defaults={
                    "constructora": empresa,
                    "etapa_principal": etapa,
                    "nombre": name,
                    "tipo_proyecto": self.unit_type(empresa.preset),
                    "fecha_inicio": start + timedelta(days=index * 8),
                    "fecha_termino_estimada": timezone.localdate() + timedelta(days=90),
                    "superficie_m2": Decimal(str(1200 + index * 740)),
                    "ubicacion": f"{empresa.comuna}, {empresa.region}",
                    "region": empresa.region,
                    "comuna": empresa.comuna,
                    "mandante": "Mandante de referencia",
                    "estado": "en_ejecucion",
                    "descripcion": f"Unidad operativa para medicion ambiental de {empresa.rubro}.",
                },
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
                defaults={
                    "constructora": empresa,
                    "fecha": start + timedelta(days=index * 14),
                    "especie": especie,
                    "volumen_m3": Decimal(volumen),
                    "origen": origen,
                    "destino": destino,
                    "tipo_producto": producto,
                    "densidad_kg_m3": Decimal(densidad),
                    "porcentaje_carbono": Decimal(carbono),
                    "estado": "activo",
                    "observaciones": "Lote trazable para balance neto, transporte y evidencias.",
                    "metadata": {"preset": "aserradero", "module": "lotes_forestales", "quality_status": "validado"},
                },
            )
            lotes.append(lote)
        return lotes

    def create_factors(self, cfg):
        factors = {}
        for item in cfg["sources"]:
            factor, _ = FactorEmision.objects.update_or_create(
                actividad=item["fuente"],
                unidad=item["unidad"],
                fuente=f"Factor de referencia Carbono Zero {YEAR}",
                anio=YEAR,
                defaults={
                    "preset": cfg["preset"],
                    "module": item["module"],
                    "categoria": item["categoria"],
                    "factor_emision": item["factor"],
                    "alcance": "Referencia operativa",
                    "descripcion": f"Factor usado para calcular emisiones de {item['fuente']}.",
                    "metadata": {"preset": cfg["preset"], "module": item["module"], "quality_status": "validado"},
                    "activo": True,
                },
            )
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
            metadata = {
                "preset": empresa.preset,
                "module": item["module"],
                "source_profile": item["fuente"],
                "quality_status": "validado",
                "evidence_expected": item["evidence"],
            }
            if lote:
                metadata["lote"] = lote.lote_id
            registro = RegistroEmision.objects.create(
                constructora=empresa,
                obra=obra,
                etapa=etapa,
                lote_forestal=lote,
                categoria=item["categoria"],
                fuente_emision=item["fuente"],
                cantidad=cantidad,
                unidad=item["unidad"],
                factor_emision=factor.factor_emision,
                fecha=today - timedelta(days=max(0, days - int((index / max(count, 1)) * days))),
                proveedor=self.provider(item["fuente"], empresa.preset),
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
            content = (
                f"Evidencia Carbono Zero\nEmpresa: {empresa.nombre}\nFuente: {registro.fuente_emision}\n"
                f"Cantidad: {registro.cantidad} {registro.unidad}\nFecha: {registro.fecha}\n"
                f"Emisiones: {registro.emisiones_kg_co2e} kg CO2e\n"
            )
            evidencia = EvidenciaObra(
                constructora=empresa,
                obra=registro.obra,
                etapa=registro.etapa,
                registro_emision=registro,
                lote_forestal=registro.lote_forestal,
                tipo_evidencia=evidence,
                estado_documental=EvidenciaObra.EstadoDocumental.VINCULADA,
                fecha_documento=registro.fecha,
                nombre=f"Respaldo - {registro.fuente_emision}",
                observaciones="Documento vinculado al registro ambiental para trazabilidad.",
                texto_extraido=content,
                metadata_extraccion={
                    "preset": empresa.preset,
                    "module": registro.metadata.get("module"),
                    "fuente_emision_sugerida": registro.fuente_emision,
                    "categoria_sugerida": registro.categoria,
                    "cantidad_sugerida": str(registro.cantidad),
                    "unidad_sugerida": registro.unidad,
                    "confianza_extraccion": 0.92,
                    "quality_status": "validado",
                },
            )
            evidencia.archivo.save(f"{empresa.constructora_id}_{registro.id}_{evidence}.txt", ContentFile(content), save=True)
            total += 1
        return total

    def create_environmental_compliance(self, empresa, industry_key, cfg):
        created_docs = 0
        created_variables = 0
        created_limits = 0
        today = timezone.localdate()
        for index, item in enumerate(cfg.get("environmental", []), 1):
            tipo, doc_name, variable_id, variable_name, categoria, unidad, valor, limite, comparador, normativa = item
            limite_obj, limite_created = LimiteNormativoAmbiental.objects.update_or_create(
                constructora=empresa,
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
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
<<<<<<< HEAD
            metadata = {
                "normativa": normativa,
                "comparador_limite": limite_obj.comparador,
                "limite_id": limite_obj.id,
                "seed": True,
            }
            _, variable_created = VariableAmbientalExtraida.objects.update_or_create(
                documento=documento,
                constructora=empresa,
=======
            VariableAmbientalExtraida.objects.create(
                documento=document,
                constructora=company,
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
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
<<<<<<< HEAD
            created_docs += int(doc_created)
            created_variables += int(variable_created)
            created_limits += int(limite_created)
        return {
            "documentos_ambientales": created_docs,
            "variables_ambientales": created_variables,
            "limites_ambientales": created_limits,
            "alertas_cumplimiento": AlertaCumplimientoAmbiental.objects.filter(constructora=empresa).count(),
        }

    def stage_type(self, name):
        name = name.lower()
        if "fund" in name:
            return "Fundaciones"
        if "obra gruesa" in name:
=======
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
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
            return "Obra gruesa"
        if "termin" in name:
            return "Terminaciones"
        if "resid" in name:
            return "Retiro de residuos"
<<<<<<< HEAD
        if "excav" in name:
            return "Excavacion"
        if "ruta" in name or "transporte" in name:
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
=======
        if "log" in normalized or "ruta" in normalized or "transporte" in normalized:
            return "Logistica"
        if "energia" in normalized or "combustible" in normalized or "mantencion" in normalized:
            return "Instalaciones"
        return "Otro"
>>>>>>> 5970f50377041bafdb1683dd81766dd712cf418f
