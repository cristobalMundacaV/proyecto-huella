import calendar
import random
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.analytics.models import (
    AccionMejoraAmbiental,
    ActivoOperacional,
    ActividadOperacional,
    AlertaCumplimientoAmbiental,
    AplicabilidadCapacidadObra,
    CapacidadAmbiental,
    CapacidadOrganizacion,
    DiagnosticoAmbientalInicial,
    DocumentoAmbiental,
    ElementoDiagnosticoAmbiental,
    EtapaObra,
    EvidenciaObra,
    FuenteDatos,
    IndicadorAmbiental,
    LineaBaseAmbiental,
    LimiteNormativoAmbiental,
    MedicionSeguimientoAmbiental,
    Obra,
    Observacion,
    Organizacion,
    ProblematicaAmbiental,
    ProcesoOperacional,
    RegistroEmision,
    UnidadOperacional,
    UsuarioOrganizacion,
    ValorIndicador,
    VariableAmbientalExtraida,
)
from apps.analytics.services.environmental_records import create_environmental_record
from apps.analytics.services.indicators_v2 import build_baseline, generate_indicator_value


TENANT_ID = "CONSTRUCTORA_VALLE_SUR"
TENANT_NAME = "Constructora Valle Sur SpA"
OBRA_CODE = "CVS-PARQUE-ALERCES"


class Command(BaseCommand):
    help = "Crea una obra de construccion con historia ambiental profesional y deterministica."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=20260821)
        parser.add_argument("--days", type=int, default=180)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--username")

    @transaction.atomic
    def handle(self, *args, **options):
        days = int(options["days"])
        if days < 180:
            raise CommandError("--days debe ser al menos 180 para construir la historia requerida.")
        user = None
        if options["username"]:
            try:
                user = User.objects.get(username=options["username"])
            except User.DoesNotExist as exc:
                raise CommandError(f"No existe el usuario '{options['username']}'.") from exc
        rng = random.Random(options["seed"])
        if options["reset"]:
            removed = self.reset_tenant()
            self.stdout.write(self.style.WARNING(f"Registros del tenant eliminados: {removed}"))
        elif Organizacion.objects.filter(organizacion_id=TENANT_ID).exists():
            raise CommandError("El tenant ya existe. Use --reset para recrearlo de forma deterministica.")

        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        org, obra, stages = self.create_foundation(start_date, end_date)
        if user:
            UsuarioOrganizacion.objects.update_or_create(
                user=user,
                organizacion=org,
                defaults={"rol": UsuarioOrganizacion.Rol.ADMIN, "activo": True},
            )
        sources, unit, processes, assets = self.create_operational_context(org, obra, start_date)
        evidence = self.create_evidence(org, obra, stages, start_date, end_date)
        activities, observations = self.create_history(
            org, obra, stages, sources, unit, processes, assets, evidence,
            start_date, days, rng,
        )
        documents, variables, limits, alerts = self.create_compliance(
            org, obra, stages, start_date, end_date, rng
        )
        indicators, values, baselines = self.create_indicators(org, obra, start_date, end_date)
        problems, actions, followups = self.create_problems(
            org, obra, indicators, evidence, start_date, end_date
        )
        legacy = self.create_legacy(org, obra, stages, activities, observations)

        summary = {
            "organizaciones": 1, "obras": 1, "actividades": len(activities),
            "observaciones": len(observations), "evidencias": len(evidence),
            "documentos_ambientales": len(documents), "variables": len(variables),
            "limites": len(limits), "alertas_abiertas": sum(a.estado == "abierta" for a in alerts),
            "indicadores": len(indicators), "valores_historicos": len(values),
            "lineas_base": len(baselines), "problematicas": len(problems),
            "acciones": len(actions), "seguimientos": len(followups),
            "registros_legacy": legacy,
        }
        self.stdout.write(self.style.SUCCESS("Historia ambiental de construccion creada correctamente."))
        self.stdout.write(self.style.SUCCESS("Resumen: " + ", ".join(f"{k}={v}" for k, v in summary.items())))

    def reset_tenant(self):
        """Elimina exclusivamente este tenant respetando las relaciones PROTECT V2."""
        tenants = Organizacion.objects.filter(organizacion_id=TENANT_ID)
        if not tenants.exists():
            return 0
        org = tenants.get()
        MedicionSeguimientoAmbiental.objects.filter(problematica__organizacion=org).delete()
        LineaBaseAmbiental.objects.filter(organizacion=org).delete()
        ValorIndicador.objects.filter(indicador__organizacion=org).delete()
        RegistroEmision.objects.filter(organizacion=org).delete()
        Observacion.objects.filter(organizacion=org).delete()
        ProblematicaAmbiental.objects.filter(organizacion=org).delete()
        AlertaCumplimientoAmbiental.objects.filter(organizacion=org).delete()
        VariableAmbientalExtraida.objects.filter(organizacion=org).delete()
        DocumentoAmbiental.objects.filter(organizacion=org).delete()
        EvidenciaObra.objects.filter(organizacion=org).delete()
        IndicadorAmbiental.objects.filter(organizacion=org).delete()
        ActividadOperacional.objects.filter(organizacion=org).delete()
        Obra.objects.filter(organizacion=org).delete()
        EtapaObra.objects.filter(organizacion=org).delete()
        removed, _ = tenants.delete()
        return removed

    def aware(self, day, hour=8, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour, minute)))

    def create_foundation(self, start, end):
        org = Organizacion.objects.create(
            organizacion_id=TENANT_ID, nombre=TENANT_NAME, rut="77.684.219-3",
            region="Biobío", comuna="Los Ángeles", direccion="Avenida Sor Vicenta 2450",
            rubro="Construcción de edificios habitacionales", preset="construccion",
            email="gestion.ambiental@vallesur.cl", telefono="+56 43 245 1180",
            contacto="Jefatura de Medio Ambiente",
            observaciones="Sistema de gestión ambiental aplicado a obras de edificación.",
        )
        stage_specs = [
            ("EXC", "Excavación y movimiento de tierras", "Excavacion", "finalizada"),
            ("FUN", "Fundaciones", "Fundaciones", "finalizada"),
            ("OG", "Obra gruesa", "Obra gruesa", "activa"),
            ("INS", "Instalaciones", "Instalaciones", "activa"),
            ("TER", "Terminaciones", "Terminaciones", "activa"),
            ("RES", "Gestión y retiro de residuos", "Retiro de residuos", "activa"),
        ]
        stages = {}
        for code, name, kind, status in stage_specs:
            stages[code] = EtapaObra.objects.create(
                etapa_id=f"{OBRA_CODE}-{code}", organizacion=org, nombre=name, tipo=kind,
                region=org.region, comuna=org.comuna, direccion=org.direccion,
                descripcion=f"Etapa controlada del proyecto: {name}.", estado=status,
                activa=status == "activa",
            )
        obra = Obra.objects.create(
            codigo_obra=OBRA_CODE, organizacion=org, etapa_principal=stages["OG"],
            nombre="Edificio Parque Los Alerces", tipo_proyecto="Edificio habitacional",
            perfil_ambiental="edificacion", fecha_inicio=start - timedelta(days=24),
            fecha_termino_estimada=end + timedelta(days=210), superficie_m2=Decimal("14860"),
            ubicacion="Los Ángeles, Biobío", region="Biobío", comuna="Los Ángeles",
            mandante="Inmobiliaria Parque Los Alerces SpA", estado="en_ejecucion",
            estado_ambiental="mejora_en_curso",
            descripcion="Edificio habitacional de doce niveles, dos subterráneos y urbanización exterior.",
        )
        diagnosis = DiagnosticoAmbientalInicial.objects.create(
            organizacion=org, obra=obra, estado="completado", fecha_inicio=start,
            fecha_finalizacion=start + timedelta(days=12),
            objetivo_principal="Establecer controles ambientales y trazabilidad operacional de la obra.",
            descripcion_contexto="Faena urbana próxima a receptores residenciales, con excavación, estructura de hormigón y especialidades.",
            observaciones="Se priorizan combustibles, materiales, residuos, agua, energía, transporte y ruido.",
        )
        elements = [
            ("proceso", "Control de consumos", "Lectura diaria y conciliación mensual de suministros."),
            ("proceso", "Recepción de materiales", "Trazabilidad mediante guías de despacho y cubicaciones."),
            ("informacion_disponible", "Registros de faena", "Bitácoras, facturas, pesajes y mediciones acústicas disponibles."),
            ("fuente", "Medidores y documentación", "Fuentes instrumentales, ERP y documentación de proveedores."),
            ("brecha", "Segregación de residuos", "Requiere consolidar clasificación en frentes de terminaciones."),
        ]
        ElementoDiagnosticoAmbiental.objects.bulk_create([
            ElementoDiagnosticoAmbiental(diagnostico=diagnosis, tipo=t, nombre=n, descripcion=d)
            for t, n, d in elements
        ])
        capability_specs = [
            ("energia", "Gestión de energía"), ("agua", "Gestión hídrica"),
            ("combustibles", "Gestión de combustibles"), ("transporte", "Gestión de transporte"),
            ("materiales", "Trazabilidad de materiales"), ("residuos", "Gestión de residuos"),
            ("ruido", "Control de ruido"),
        ]
        for order, (key, name) in enumerate(capability_specs, 1):
            capability, _ = CapacidadAmbiental.objects.get_or_create(
                clave=key, defaults={"nombre": name, "descripcion": f"Capacidad para {name.lower()}.", "orden": order}
            )
            CapacidadOrganizacion.objects.create(
                organizacion=org, capacidad=capability, estado="operativa",
                recomendada_por_preset=True, configuracion="Control activo con revisión mensual.",
            )
            AplicabilidadCapacidadObra.objects.create(
                obra=obra, capacidad=capability, diagnostico=diagnosis, estado="aplica"
            )
        return org, obra, stages

    def create_operational_context(self, org, obra, start):
        unit = UnidadOperacional.objects.create(
            organizacion=org, nombre="Faena Edificio Parque Los Alerces", tipo="faena",
            descripcion="Unidad operacional correspondiente al recinto completo de la obra."
        )
        process_names = {
            "energia": "Abastecimiento eléctrico", "agua": "Uso y control de agua",
            "combustibles": "Operación de maquinaria", "transporte": "Logística de abastecimiento",
            "materiales": "Recepción e incorporación de materiales", "residuos": "Gestión de residuos",
            "ruido": "Monitoreo de ruido perimetral",
        }
        processes = {key: ProcesoOperacional.objects.create(
            organizacion=org, unidad=unit, nombre=name,
            descripcion=f"Proceso operacional para {name.lower()}.", estado="activo"
        ) for key, name in process_names.items()}
        source_specs = [
            ("Bitácora digital de faena", "sistema"), ("ERP de abastecimiento", "erp"),
            ("Medidores de servicios", "sensor"), ("Documentación de proveedores", "documento"),
            ("Sonómetro integrador", "sensor"),
        ]
        sources = {name: FuenteDatos.objects.create(
            organizacion=org, nombre=name, tipo=kind,
            descripcion=f"Fuente controlada: {name.lower()}.", identificador_externo=f"CVS-FUENTE-{i:02d}",
            metadata={"alcance": "obra", "obra_codigo": OBRA_CODE}
        ) for i, (name, kind) in enumerate(source_specs, 1)}
        asset_specs = [
            ("EXC-01", "Excavadora sobre orugas", "maquinaria", "combustibles"),
            ("GRU-01", "Grúa torre principal", "equipo", "energia"),
            ("GEN-01", "Grupo electrógeno de respaldo", "equipo", "combustibles"),
            ("MED-E-01", "Medidor eléctrico de faena", "medidor", "energia"),
            ("MED-A-01", "Medidor de agua de faena", "medidor", "agua"),
            ("SON-01", "Sonómetro integrador clase 2", "medidor", "ruido"),
            ("PTO-LIM", "Punto limpio de obra", "infraestructura", "residuos"),
        ]
        assets = {}
        for code, name, kind, domain in asset_specs:
            assets[domain] = assets.get(domain, []) + [ActivoOperacional.objects.create(
                organizacion=org, codigo=f"{OBRA_CODE}-{code}", nombre=name, tipo=kind,
                descripcion=f"Activo asignado a {process_names[domain].lower()}.", unidad_operacional=unit,
                proceso_operacional=processes[domain], estado="operativo", fecha_alta=start - timedelta(days=20),
                metadata={"obra_codigo": OBRA_CODE, "control_mantencion": True},
            )]
        return sources, unit, processes, assets

    def create_evidence(self, org, obra, stages, start, end):
        types = ["factura_combustible", "boleta_electrica", "guia_despacho", "factura_material",
                 "ticket_pesaje", "registro_retiro_residuos", "registro_maquinaria", "documento_transporte"]
        names = [
            "Conciliación mensual de combustible", "Estado de consumo eléctrico", "Guías de hormigón premezclado",
            "Certificados de acero de refuerzo", "Comprobantes de pesaje de residuos", "Informe de retiro valorizado",
            "Bitácora de maquinaria pesada", "Consolidado de transporte de materiales",
        ]
        evidence = []
        for i in range(20):
            month_day = min(end, start + timedelta(days=5 + i * max(1, (end - start).days // 31)))
            status = "validada" if i < 23 else ("vinculada" if i < 28 else "pendiente")
            item = EvidenciaObra.objects.create(
                organizacion=org, obra=obra, etapa=list(stages.values())[i % len(stages)],
                tipo_evidencia=types[i % len(types)], estado_documental=status,
                fecha_documento=month_day, archivo="", nombre=f"{names[i % len(names)]} {month_day:%Y-%m}",
                observaciones="Respaldo consolidado para revisión ambiental mensual.",
                texto_extraido="Resumen de cantidades, período informado y responsable de validación.",
                metadata_extraccion={"obra_codigo": OBRA_CODE, "confianza_extraccion": 0.94 if status == "validada" else 0.82},
            )
            evidence.append(item)
        return evidence

    def stage_for_day(self, index, days, stages):
        ratio = index / max(days - 1, 1)
        if ratio < .17: return stages["EXC"]
        if ratio < .38: return stages["FUN"]
        if ratio < .72: return stages["OG"]
        if ratio < .88: return stages["INS"]
        return stages["TER"]

    def create_history(self, org, obra, stages, sources, unit, processes, assets, evidence, start, days, rng):
        profiles = {
            "energia": ("consumo_energia", "Consumo eléctrico de faena", "electricidad_kwh", "kWh"),
            "agua": ("consumo_agua", "Consumo de agua de faena", "agua_m3", "m3"),
            "combustibles": ("consumo_combustible", "Consumo diésel de maquinaria", "diesel_l", "L"),
            "transporte": ("transporte", "Transporte de materiales", "transporte_ton_km", "t·km"),
            "materiales": ("movimiento_material", "Recepción de materiales", "material_ton", "t"),
            "residuos": ("gestion_residuo", "Gestión de residuos de construcción", "residuo_kg", "kg"),
            "ruido": ("monitoreo_ruido", "Monitoreo de ruido perimetral", "ruido_db", "dB(A)"),
        }
        activity_rows, plan = [], []
        for offset in range(days):
            day = start + timedelta(days=offset)
            weekday = day.weekday()
            daily_count = 5 if weekday < 5 else (3 if weekday == 5 else 1)
            stage = self.stage_for_day(offset, days, stages)
            stage_key = stage.etapa_id.rsplit("-", 1)[-1]
            weights = {
                "EXC": ["combustibles", "combustibles", "transporte", "agua", "ruido"],
                "FUN": ["materiales", "materiales", "transporte", "agua", "combustibles"],
                "OG": ["materiales", "transporte", "residuos", "agua", "energia"],
                "INS": ["energia", "energia", "residuos", "transporte", "agua"],
                "TER": ["energia", "residuos", "residuos", "materiales", "ruido"],
            }[stage_key]
            for slot in range(daily_count):
                domain = weights[(slot + offset) % len(weights)]
                kind, name, _, _ = profiles[domain]
                begin = self.aware(day, 8 + min(slot, 7), (offset * 7 + slot * 11) % 50)
                row = ActividadOperacional(
                    organizacion=org, obra=obra, tipo=kind,
                    codigo=f"CVS-{day:%Y%m%d}-{slot + 1:02d}", nombre=name,
                    timestamp_inicio=begin, timestamp_fin=begin + timedelta(minutes=35 + slot * 8),
                    unidad_operacional=unit, proceso_operacional=processes[domain],
                    estado="lista_para_evaluacion", referencia_externa=f"BIT-{day:%Y%m%d}-{slot + 1:02d}",
                    metadata={"dominio": domain, "etapa_id": stage.id, "jornada": "normal" if weekday < 5 else "reducida"},
                )
                activity_rows.append(row)
                plan.append((domain, stage_key, weekday, offset, slot))
        activities = ActividadOperacional.objects.bulk_create(activity_rows, batch_size=500)
        for activity, (domain, _, _, _, _) in zip(activities, plan):
            if assets.get(domain):
                activity.activos.add(assets[domain][0])

        obs_rows = []
        for idx, (activity, spec) in enumerate(zip(activities, plan)):
            domain, stage_key, weekday, offset, slot = spec
            _, _, concept, unit_name = profiles[domain]
            work = Decimal("1") if weekday < 5 else (Decimal("0.52") if weekday == 5 else Decimal("0.12"))
            progress = Decimal(str(offset / max(days - 1, 1)))
            base = {
                "energia": Decimal("145") * (Decimal("0.75") + progress * Decimal("0.75")),
                "agua": Decimal("18"), "combustibles": Decimal("72") if stage_key == "EXC" else Decimal("34"),
                "transporte": Decimal("980"), "materiales": Decimal("24") if stage_key in {"FUN", "OG"} else Decimal("8"),
                "residuos": Decimal("520") * (Decimal("1.45") if stage_key in {"OG", "TER"} else Decimal("0.65")),
                "ruido": Decimal("61") if weekday < 6 else Decimal("49"),
            }[domain]
            if domain == "agua":
                base *= Decimal("1.15") if stage_key in {"FUN", "OG"} else Decimal("0.85")
            if domain == "transporte":
                base *= Decimal("1.35") if stage_key in {"FUN", "OG"} else Decimal("0.72")
            variation = Decimal(str(rng.uniform(.92, 1.08)))
            value = (base * work * variation).quantize(Decimal("0.001"))
            source = (sources["Sonómetro integrador"] if domain == "ruido" else
                      sources["Medidores de servicios"] if domain in {"energia", "agua"} else
                      sources["ERP de abastecimiento"] if domain in {"materiales", "transporte"} else
                      sources["Bitácora digital de faena"])
            ev = evidence[(idx // 24) % len(evidence)] if idx % 9 == 0 else None
            obs_rows.append(Observacion(
                organizacion=org, actividad=activity, fuente=source, concepto=concept,
                valor_numerico=value, unidad=unit_name, timestamp_observacion=activity.timestamp_fin,
                metodo_captura="instrumental" if domain in {"energia", "agua", "ruido"} else "importado",
                naturaleza="instrumental" if domain in {"energia", "agua", "ruido"} else "documental",
                evidencia=ev, estado="validada" if idx % 17 else "pendiente",
            ))
            obs_rows.append(Observacion(
                organizacion=org, actividad=activity, fuente=sources["Bitácora digital de faena"],
                concepto="horas_operacion", valor_numerico=(Decimal("7.8") * work * variation).quantize(Decimal("0.001")),
                unidad="h", timestamp_observacion=activity.timestamp_fin, metodo_captura="manual",
                naturaleza="declarativo", estado="validada",
            ))
        observations = Observacion.objects.bulk_create(obs_rows, batch_size=1000)
        return activities, observations

    def create_compliance(self, org, obra, stages, start, end, rng):
        limit_specs = [
            ("ruido_diurno_db", "Ruido diurno en receptor", "DS38", Decimal("60"), "dB(A)"),
            ("residuos_trazabilidad_pct", "Residuos con trazabilidad", "Ley 20.920", Decimal("90"), "%"),
            ("combustible_conciliado_pct", "Combustible conciliado", "ISO 14001", Decimal("95"), "%"),
        ]
        limits = [LimiteNormativoAmbiental.objects.create(
            organizacion=org, industria="construccion", variable_id=key, nombre=name,
            normativa=rule, limite=value, unidad=unit, comparador=">=" if unit == "%" else "<=",
            region="Biobío", tipo_instalacion="Obra de edificación", vigencia_desde=start,
            fuente_normativa="Matriz legal y compromisos ambientales de la obra", validado=True, activo=True,
            descripcion=f"Criterio aplicable a {name.lower()}.", metadata={"obra_codigo": OBRA_CODE}
        ) for key, name, rule, value, unit in limit_specs]
        documents, variables = [], []
        doc_names = ["Informe mensual de desempeño ambiental", "Consolidado de residuos de construcción",
                     "Informe de medición acústica", "Conciliación de consumos de obra"]
        for i in range(6):
            month_end = end - timedelta(days=i * 30)
            # Veinte documentos en seis cierres; junto a veinte evidencias deja
            # un expediente compacto de 40 respaldos, no uno por observacion.
            for j, name in enumerate(doc_names[:4 if i < 2 else 3]):
                status = "pendiente" if (i, j) in {(0, 1), (0, 3), (1, 2)} else "valido"
                doc = DocumentoAmbiental.objects.create(
                    organizacion=org, obra=obra, etapa=stages["TER"] if i < 2 else stages["OG"],
                    tipo_documento=["informe_gestion", "registro_rcd", "medicion_ruido", "balance_consumos"][j],
                    industria="construccion", nombre=f"{name} {month_end:%Y-%m}", fecha_documento=month_end,
                    periodo_inicio=month_end.replace(day=1), periodo_fin=month_end,
                    fuente_origen="laboratorio" if j == 2 else "pdf", estado_procesamiento="validado" if status == "valido" else "extraido",
                    estado_validacion=status, resumen=f"Resultados consolidados de {name.lower()}.",
                    metadata={"obra_codigo": OBRA_CODE, "responsable": "Coordinación ambiental"},
                )
                documents.append(doc)
                key, label, unit_name, value = [
                    ("desempeno_ambiental_pct", "Cumplimiento del programa ambiental", "%", Decimal("93") + Decimal(str(rng.uniform(-2, 2)))),
                    ("residuos_trazabilidad_pct", "Residuos con trazabilidad", "%", Decimal("89") + Decimal(str(rng.uniform(-3, 4)))),
                    ("ruido_diurno_db", "Ruido diurno en receptor", "dB(A)", Decimal("58.5") + Decimal(str(rng.uniform(-2, 3.5)))),
                    ("combustible_conciliado_pct", "Combustible conciliado", "%", Decimal("96") + Decimal(str(rng.uniform(-3, 2)))),
                ][j]
                limit = next((x for x in limits if x.variable_id == key), None)
                compliance = "sin_limite"
                if limit:
                    compliance = "cumple" if ((limit.comparador == "<=" and value <= limit.limite) or (limit.comparador == ">=" and value >= limit.limite)) else "alerta"
                var = VariableAmbientalExtraida.objects.create(
                    documento=doc, organizacion=org, variable_id=key, nombre=label,
                    categoria=["Gestión", "Residuos", "Ruido", "Combustibles"][j], valor=value.quantize(Decimal("0.01")),
                    unidad=unit_name, fecha_medicion=month_end, punto_medicion="Obra completa" if j != 2 else "Receptor sensible nororiente",
                    limite_aplicable=limit.limite if limit else None, unidad_limite=limit.unidad if limit else "",
                    estado_cumplimiento=compliance, confianza_extraccion=Decimal("0.94"),
                    metadata={"obra_codigo": OBRA_CODE, "revisión": "mensual"},
                )
                variables.append(var)
        alerts = []
        alert_vars = [v for v in variables if v.estado_cumplimiento == "alerta"][-3:]
        while len(alert_vars) < 3:
            alert_vars.append(variables[len(alert_vars) + 1])
        for i, var in enumerate(alert_vars[:3]):
            alerts.append(AlertaCumplimientoAmbiental.objects.create(
                organizacion=org, documento=var.documento, variable=var,
                severidad="amarillo" if i < 2 else "rojo", tipo_alerta="desviacion_operacional",
                titulo=["Reforzar trazabilidad de residuos", "Revisar conciliación de combustible", "Control acústico preventivo"][i],
                descripcion="Desviación acotada detectada en la revisión del período más reciente.", estado="abierta",
                accion_sugerida="Aplicar control semanal y verificar el resultado en el próximo cierre.",
                normativa=next((x.normativa for x in limits if x.variable_id == var.variable_id), "ISO 14001"),
                fecha_evento=var.fecha_medicion, metadata={"obra_codigo": OBRA_CODE, "prioridad": i + 1},
            ))
        return documents, variables, limits, alerts

    def month_periods(self, start, end):
        periods, cursor = [], start.replace(day=1)
        while cursor <= end:
            last = calendar.monthrange(cursor.year, cursor.month)[1]
            period_start, period_end = max(start, cursor), min(end, cursor.replace(day=last))
            periods.append((period_start, period_end))
            cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        return periods

    def create_indicators(self, org, obra, start, end):
        specs = [
            ("electricidad_mensual", "Electricidad consumida", "electricidad_kwh", "kWh", "absoluto"),
            ("agua_mensual", "Agua consumida", "agua_m3", "m3", "absoluto"),
            ("diesel_mensual", "Diésel consumido", "diesel_l", "L", "absoluto"),
            ("transporte_materiales", "Transporte de materiales", "transporte_ton_km", "t·km", "operacional"),
            ("materiales_incorporados", "Materiales incorporados", "material_ton", "t", "operacional"),
            ("residuos_generados", "Residuos generados", "residuo_kg", "kg", "absoluto"),
            ("ruido_acumulado", "Nivel acústico registrado", "ruido_db", "dB(A) acumulado", "operacional"),
            ("horas_operacion", "Horas de operación registradas", "horas_operacion", "h", "operacional"),
            ("agua_por_hora", "Intensidad hídrica operacional", "agua_m3", "m3/h", "intensidad"),
            ("diesel_por_hora", "Intensidad de diésel operacional", "diesel_l", "L/h", "intensidad"),
        ]
        indicators, values, baselines = [], [], []
        periods = self.month_periods(start, end)
        for code, name, numerator, unit, kind in specs:
            indicator = IndicadorAmbiental.objects.create(
                organizacion=org, alcance="obra", obra=obra, codigo=code, nombre=name, tipo=kind,
                unidad=unit, descripcion=f"Seguimiento mensual de {name.lower()}.", origen_numerador=numerator,
                origen_denominador="horas_operacion" if kind == "intensidad" else "",
                direccion_deseable="menor_es_mejor", activo=True,
            )
            indicators.append(indicator)
            for period_start, period_end in periods:
                values.append(generate_indicator_value(indicator, period_start, period_end))
            baselines.append(build_baseline(indicator))
        return indicators, values, baselines

    def create_problems(self, org, obra, indicators, evidence, start, end):
        by_code = {x.codigo: x for x in indicators}
        specs = [
            ("Consumo elevado de diésel durante excavación", "Combustibles", "diesel_mensual", 4200, 3600, 3420, "resuelta", "efectiva", "alto"),
            ("Pérdidas de agua en red provisoria", "Agua", "agua_mensual", 510, 430, 405, "cerrada", "efectiva", "medio"),
            ("Baja segregación inicial de residuos", "Residuos", "residuos_generados", 9200, 7600, 7420, "resuelta", "efectiva", "medio"),
            ("Desvíos de ruido en receptor nororiente", "Ruido", "ruido_acumulado", 62, 60, 60.8, "seguimiento", "parcialmente_efectiva", "alto"),
            ("Intensidad eléctrica creciente en instalaciones", "Energía", "electricidad_mensual", 6900, 6200, None, "implementando", "pendiente", "medio"),
            ("Trazabilidad incompleta de viajes de abastecimiento", "Transporte", "transporte_materiales", 28500, 25000, 26100, "seguimiento", "parcialmente_efectiva", "medio"),
            ("Aumento de residuos en terminaciones", "Residuos", "residuos_generados", 10800, 8800, None, "detectada", "pendiente", "alto"),
        ]
        problems, actions, followups = [], [], []
        for i, (title, category, indicator_code, initial, target, posterior, state, result, risk) in enumerate(specs):
            detected = start + timedelta(days=20 + i * 21)
            problem = ProblematicaAmbiental.objects.create(
                organizacion=org, obra=obra, titulo=title,
                descripcion=f"Tendencia identificada mediante revisión de {category.lower()} y antecedentes de terreno.",
                categoria=category, indicador=indicator_code, unidad_indicador=by_code[indicator_code].unidad,
                area_operacional="Frentes de obra", unidad_operacional="Faena Edificio Parque Los Alerces",
                valor_inicial=Decimal(str(initial)), objetivo_meta=Decimal(str(target)),
                valor_posterior=Decimal(str(posterior)) if posterior is not None else None,
                mejora_absoluta=Decimal(str(initial - posterior)) if posterior is not None else None,
                mejora_porcentaje=(Decimal(str((initial - posterior) / initial * 100)).quantize(Decimal("0.01")) if posterior is not None else None),
                fecha_deteccion=detected, nivel_riesgo=risk, estado=state, resultado_evaluacion=result,
                origen_deteccion="indicador_v2", objetivo_ambiental=f"Reducir y controlar el desempeño asociado a {category.lower()}.",
                metadata={"obra_codigo": OBRA_CODE, "indicador_v2_id": by_code[indicator_code].id},
            )
            problems.append(problem)
            if state == "detectada":
                continue
            action_state = "evaluada" if state in {"resuelta", "cerrada"} else ("seguimiento" if state == "seguimiento" else "en_implementacion")
            action = AccionMejoraAmbiental.objects.create(
                problematica=problem, titulo=[
                    "Optimizar despacho y ralentí de maquinaria", "Sectorizar red provisoria y controlar fugas",
                    "Implementar estaciones de segregación", "Instalar barrera acústica y ajustar horarios",
                    "Programar tableros y desconexión fuera de jornada", "Digitalizar control de guías y rutas",
                ][i], descripcion="Medida operacional con responsable, plazo y verificación mediante indicador.",
                justificacion="La tendencia histórica muestra una oportunidad de reducción medible.", estado=action_state,
                fecha_propuesta=detected + timedelta(days=2), fecha_seleccion=detected + timedelta(days=5),
                fecha_inicio_efectiva=detected + timedelta(days=7),
                fecha_termino_real=detected + timedelta(days=28) if action_state == "evaluada" else None,
                responsable="Encargado de Medio Ambiente y Administrador de Obra",
                fecha_inicio=detected + timedelta(days=7), fecha_objetivo=min(end + timedelta(days=20), detected + timedelta(days=45)),
                implementada_at=self.aware(detected + timedelta(days=7), 9),
                observaciones="Avance revisado en reunión de coordinación ambiental.", metadata={"obra_codigo": OBRA_CODE},
            )
            actions.append(action)
            measure_values = [Decimal(str(initial * .94)), Decimal(str(posterior if posterior is not None else initial * .91))]
            for j, value in enumerate(measure_values):
                measure_date = min(end, detected + timedelta(days=18 + j * 18))
                if measure_date <= detected:
                    continue
                followups.append(MedicionSeguimientoAmbiental.objects.create(
                    problematica=problem, accion=action, fecha=measure_date, valor=value,
                    unidad=problem.unidad_indicador, fuente="indicador_v2", indicador_v2=by_code[indicator_code],
                    referencia=f"Cierre operacional {measure_date:%Y-%m}",
                    observaciones="Resultado verificado contra la condición inicial y la meta definida.",
                    evidencia=evidence[(i * 4 + j) % len(evidence)], metadata={"obra_codigo": OBRA_CODE},
                ))
        return problems, actions, followups

    def create_legacy(self, org, obra, stages, activities, observations):
        by_day = defaultdict(list)
        for obs in observations:
            if obs.concepto != "diesel_l":
                continue
            by_day[obs.timestamp_observacion.date()].append(obs)
        created = 0
        # Compatibilidad secundaria: un consolidado diario solo cuando hubo consumo de combustible.
        for day, rows in sorted(by_day.items()):
            amount = sum((row.valor_numerico for row in rows), Decimal("0"))
            create_environmental_record(
                {"obra": obra, "etapa": stages["EXC"] if day < obra.fecha_inicio + timedelta(days=55) else stages["OG"],
                 "actividad": "Consumo diario de diésel en maquinaria", "categoria": "Maquinaria",
                 "cantidad": amount, "unidad": "L", "factor_emision": Decimal("0"), "fecha": day,
                 "proveedor": "Distribuidora de Combustibles Biobío", "area_operacional": "Frentes de obra",
                 "unidad_operacional": "Faena Edificio Parque Los Alerces",
                 "identificador_externo": f"CVS-LEG-{day:%Y%m%d}",
                 "estado_validacion": "validado", "observaciones": "Consolidado de compatibilidad para consulta histórica.",
                 "metadata": {"compatibilidad_secundaria": True, "fuente_v2": "observaciones_operacionales"}},
                organizacion=org, tipo_ingreso=RegistroEmision.TipoIngreso.SISTEMA,
                fuente_ingreso="Consolidación del núcleo operacional V2",
            )
            created += 1
        return created
