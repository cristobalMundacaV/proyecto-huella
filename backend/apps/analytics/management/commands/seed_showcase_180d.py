"""Idempotent, synthetic construction showcase for the DEMO_HORIZONTE tenant.

The command augments the modern demo foundation without deleting governed
factors, observations, calculations or EC3 evidence. Codes prefixed CZ180
identify every regenerable activity; an end-date anchor is persisted so a
later invocation cannot silently shift the historical window.
"""

from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.ai.management.commands.seed_ai_demo_tenant import Command as DemoFoundation
from apps.analytics.models import (
    AccionMejoraAmbiental, ActividadOperacional, AlertaCumplimientoAmbiental,
    AplicabilidadCapacidadObra,
    DiagnosticoAmbientalInicial, DiscrepanciaDato, EspacioTrabajoOperacional,
    DocumentoAmbiental, EtapaObra, EventoMaterial, EvidenciaObra, FuenteDatos, HallazgoRevisionProfesional,
    IndicadorAmbiental, MaterialOperacional, Obra, Observacion, Organizacion,
    ProblematicaAmbiental, ProcesoOperacional, RegistroFlujoAmbiental,
    RevisionProfesionalAmbiental, RutaOperacional, UnidadOperacional,
    UsuarioObraAcceso, UsuarioOrganizacion, ValorIndicador, Vehiculo,
    ViajeOperacional, VersionFactorAmbiental,
)
from apps.analytics.models.assets import (
    ActivoOperacional, Maquinaria, MantenimientoActivo, PuntoAmbientalOperacional,
)
from apps.analytics.models.reporting import ExpedienteAmbiental
from apps.analytics.services.calculation_v2 import calculate_activity
from apps.analytics.services.capture import capture_observation
from apps.analytics.services.factor_governance import transition_factor_version
from apps.analytics.services.indicators_v2 import generate_indicator_value
from apps.analytics.services.material_factor_mapping import (
    approve_material_mapping, propose_material_mapping,
)
from apps.analytics.services.onboarding import apply_onboarding_step
from apps.analytics.services.system_environmental_catalog import ensure_system_environmental_catalog
from apps.iot.models import CalibracionSensor, DispositivoSensor, LecturaSensorV2
from apps.iot.services_v2 import registrar_lectura

TENANT = "DEMO_HORIZONTE"
PREFIX = "CZ180"
FLOWS = (
    "materiales", "transporte", "combustibles", "energia", "agua",
    "residuos_no_peligrosos", "residuos_peligrosos", "ruido",
    "emisiones_atmosfericas", "suelo",
)
ASSET_SPECS = (
    ("EXC-02", "Excavadora de fundaciones", "maquinaria", "operativo", "Norte"),
    ("RET-01", "Retroexcavadora de apoyo", "maquinaria", "requiere_revision", "Sur"),
    ("GRU-01", "Grúa torre", "equipo", "operativo", "Norte"),
    ("MAN-01", "Manipulador telescópico", "maquinaria", "operativo", "Norte"),
    ("COM-01", "Compactador", "maquinaria", "operativo", "Sur"),
    ("GEN-01", "Generador de respaldo", "equipo", "operativo", "Norte"),
    ("BOM-01", "Bomba de agua", "equipo", "operativo", "Sur"),
    ("CAM-02", "Camión de abastecimiento", "vehiculo", "operativo", "Norte"),
    ("MED-E", "Medidor eléctrico de faena", "medidor", "operativo", "Norte"),
    ("MED-A", "Medidor de agua de faena", "medidor", "operativo", "Norte"),
    ("PTO-L", "Punto limpio y segregación", "infraestructura", "operativo", "Norte"),
    ("EST-D", "Estanque de diésel", "infraestructura", "operativo", "Sur"),
    ("MINI-02", "Minicargador centro logístico", "maquinaria", "operativo", "Biobío"),
)


def at(day, hour=9, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def amount(base, offset, *, bump=0):
    """Small deterministic cadence, not random noise or copied daily rows."""
    return (Decimal(str(base)) * (Decimal("0.94") + Decimal(offset % 7) * Decimal("0.02")) *
            (Decimal("1") + Decimal(str(bump)))).quantize(Decimal("0.001"))


class Command(BaseCommand):
    help = "Extiende DEMO_HORIZONTE con un showcase sintético de 180 días, sin borrar historial gobernado."

    def add_arguments(self, parser):
        parser.add_argument("--end-date", help="Ancla YYYY-MM-DD; por defecto, fecha local de la primera ejecución.")
        parser.add_argument("--verify-only", action="store_true", help="Imprime y valida el dataset existente sin escribir.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["verify_only"]:
            org = Organizacion.objects.filter(organizacion_id=TENANT).first()
            if not org:
                raise CommandError("El tenant demo aún no existe.")
            self._summary(org)
            return
        foundation = DemoFoundation()
        ensure_system_environmental_catalog()
        org, admin = foundation._organization_and_admin()
        stored = dict(org.onboarding_data or {})
        requested = date.fromisoformat(options["end_date"]) if options["end_date"] else None
        anchored = date.fromisoformat(stored["showcase_180d_end"]) if stored.get("showcase_180d_end") else None
        if anchored and requested and anchored != requested:
            raise CommandError("El tenant ya tiene otra ancla; no se desplaza ni borra historial gobernado.")
        end = anchored or requested or timezone.localdate()
        start = end - timedelta(days=179)
        if end > timezone.localdate():
            raise CommandError("El showcase no puede terminar en el futuro.")
        stored["showcase_180d_end"] = end.isoformat()
        org.onboarding_data = stored
        org.save(update_fields=["onboarding_data"])

        obras = self._works(foundation, org, start, end)
        users = self._users(org, obras, admin)
        self._onboarding(org, admin)
        self._diagnoses(org, obras, start, end, admin)
        factors = foundation._factors(org)
        materials = foundation._materials(org)
        foundation._map_materials(org, admin, materials, factors)
        concrete = materials["HORIZONTE-HORMIGON"]
        if not concrete.mapeos_factor.filter(estado="aprobado").exists():
            mapping = propose_material_mapping(org, concrete, factors["HORIZONTE-HORMIGON"], start - timedelta(days=30), None, admin)
            approve_material_mapping(mapping.pk, org, admin)
        units, processes, source = self._operational_context(org, obras)
        assets = self._assets(org, obras, units, start)
        evidence = self._evidence(org, obras, start, end, users)
        materials = self._material_catalog(org, admin, start, materials)
        self._history(org, obras, start, end, units, processes, source, assets, evidence, materials)
        self._maintenance(org, assets, end)
        self._sensors(org, obras, assets, start, end, evidence)
        self._compliance(org, obras, start, end)
        problems = self._management(org, obras, users, start, end, evidence)
        self._governance(org, users, problems, evidence, end)
        self._indicators(org, obras, start, end)
        self._summary(org)

    def _works(self, foundation, org, start, end):
        north, south = foundation._obras(org)
        specs = ((north, "Edificio Horizonte Norte", "edificacion", "en_ejecucion", "mejora_en_curso"),
                 (south, "Condominio Horizonte Sur", "edificacion", "en_ejecucion", "requiere_atencion"))
        for obra, name, profile, state, env_state in specs:
            obra.nombre = name
            obra.perfil_ambiental = profile
            obra.tipo_proyecto = Obra.TipoProyecto.EDIFICIO
            obra.fecha_inicio = start
            obra.fecha_termino_estimada = end + timedelta(days=160)
            obra.estado = state
            obra.estado_ambiental = env_state
            obra.save()
        third, _ = Obra.objects.update_or_create(
            organizacion=org, codigo_obra=f"{TENANT}_OBRA_3",
            defaults={"nombre": "Centro Logístico Biobío", "tipo_proyecto": Obra.TipoProyecto.INDUSTRIAL,
                      "perfil_ambiental": "edificacion", "fecha_inicio": end - timedelta(days=55),
                      "fecha_termino_estimada": end + timedelta(days=300), "estado": Obra.Estado.EN_EJECUCION,
                      "estado_ambiental": "configuracion"},
        )
        for obra in (north, south, third):
            stage, _ = EtapaObra.objects.update_or_create(
                etapa_id=f"{PREFIX}-{obra.codigo_obra}-MAIN",
                defaults={"organizacion": org, "nombre": f"Etapa principal {obra.nombre}",
                          "tipo": EtapaObra.Tipo.OBRA_GRUESA if obra == north else EtapaObra.Tipo.FUNDACIONES,
                          "estado": "activa", "activa": True},
            )
            if obra.etapa_principal_id != stage.id:
                obra.etapa_principal = stage
                obra.save(update_fields=["etapa_principal", "updated_at"])
        return north, south, third

    def _users(self, org, obras, admin):
        specs = (
            ("ambiental", "Responsable ambiental", UsuarioOrganizacion.Rol.RESPONSABLE_AMBIENTAL, "organizacion", ()),
            ("jefe-norte", "Jefe de obra Norte", UsuarioOrganizacion.Rol.OPERADOR, "obras", (0,)),
            ("terreno-sur", "Profesional de terreno Sur", UsuarioOrganizacion.Rol.ANALISTA, "obras", (1,)),
            ("revisor", "Revisor ambiental", UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL, "organizacion", ()),
            ("consulta", "Consulta portafolio", UsuarioOrganizacion.Rol.LECTOR, "organizacion", ()),
        )
        User = get_user_model()
        users = {"admin": admin}
        for suffix, cargo, role, scope, indices in specs:
            username = f"demo-horizonte-{suffix}"
            user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.invalid"})
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            membership, _ = UsuarioOrganizacion.objects.update_or_create(
                user=user, organizacion=org,
                defaults={"rol": role, "alcance": scope, "cargo": cargo, "activo": True},
            )
            for index in indices:
                UsuarioObraAcceso.objects.get_or_create(usuario_organizacion=membership, obra=obras[index])
            users[suffix] = user
        return users

    def _onboarding(self, org, admin):
        apply_onboarding_step(org, admin, 1, {
            "nombre": "Constructora Horizonte Demo SpA", "rut": "77.684.219-2", "preset": "construccion",
            "rubro": "Construcción", "region": "Región del Biobío", "comuna": "Concepción",
            "direccion": "Av. Demo 180", "email": "demo@example.invalid",
        })
        area_types = ("oficina_tecnica", "bodega", "administracion", "medio_ambiente_sostenibilidad",
                      "logistica_transporte", "maquinaria_equipos", "calidad_laboratorio", "terreno_supervision", "mantenimiento")
        apply_onboarding_step(org, admin, 2, {"areas": list(area_types)})
        apply_onboarding_step(org, admin, 3, {
            "flujos": {key: "regular" for key in FLOWS},
            "relaciones": {
                "bodega": ["materiales", "residuos_no_peligrosos", "residuos_peligrosos"],
                "administracion": ["energia", "agua"],
                "logistica_transporte": ["transporte", "combustibles"],
                "maquinaria_equipos": ["combustibles", "ruido", "emisiones_atmosfericas"],
                "calidad_laboratorio": ["ruido", "emisiones_atmosfericas", "suelo"],
            },
        })
        apply_onboarding_step(org, admin, 4, {"confirmado": True})

    def _diagnoses(self, org, obras, start, end, admin):
        capabilities = list(org.capacidades_ambientales.select_related("capacidad").filter(capacidad__clave__in=FLOWS))
        for index, obra in enumerate(obras):
            completed = index == 0
            diagnosis, _ = DiagnosticoAmbientalInicial.objects.update_or_create(
                organizacion=org, obra=obra,
                defaults={"estado": "completado" if completed else "en_progreso",
                          "fecha_inicio": start if index < 2 else end - timedelta(days=55),
                          "fecha_finalizacion": start + timedelta(days=18) if completed else None,
                          "responsable": admin, "objetivo_principal": "Controlar consumos, abastecimiento y seguimiento ambiental.",
                          "descripcion_contexto": "Faena de construcción con suministros medidos y trazabilidad documental."},
            )
            for relation in capabilities:
                state = "aplica" if index == 0 or (index == 1 and relation.capacidad.clave not in {"suelo", "residuos_peligrosos"}) else "pendiente"
                AplicabilidadCapacidadObra.objects.update_or_create(
                    obra=obra, capacidad=relation.capacidad, defaults={"diagnostico": diagnosis, "estado": state},
                )

    def _operational_context(self, org, obras):
        units, processes = {}, {}
        area = org.areas_operacionales.get(tipo="medio_ambiente_sostenibilidad")
        membership = org.usuarios.get(user__username="demo-horizonte-admin")
        for index, obra in enumerate(obras):
            unit, _ = UnidadOperacional.objects.get_or_create(
                organizacion=org, nombre=f"Faena {obra.nombre}",
                defaults={"tipo": UnidadOperacional.Tipo.FAENA, "descripcion": "Unidad operacional de obra."},
            )
            units[obra.id] = unit
            EspacioTrabajoOperacional.objects.get_or_create(
                usuario_organizacion=membership, area=area, obra=obra,
                defaults={"nombre": f"Gestión ambiental {obra.nombre}"},
            )
            for domain, name in (("energia", "Servicios eléctricos"), ("agua", "Control hídrico"),
                                 ("combustibles", "Maquinaria y combustible"), ("transporte", "Logística de abastecimiento"),
                                 ("materiales", "Recepción de materiales"), ("residuos", "Gestión de residuos"),
                                 ("ruido", "Monitoreo perimetral"), ("aire", "Control de polvo"), ("suelo", "Control de suelo")):
                process, _ = ProcesoOperacional.objects.get_or_create(
                    organizacion=org, unidad=unit, nombre=name,
                    defaults={"descripcion": f"{name} en {obra.nombre}", "estado": "activo"},
                )
                processes[obra.id, domain] = process
        source, _ = FuenteDatos.objects.get_or_create(
            organizacion=org, nombre="Bitácora showcase 180D",
            defaults={"tipo": FuenteDatos.Tipo.MANUAL, "descripcion": "Datos sintéticos deterministas del showcase."},
        )
        return units, processes, source

    def _assets(self, org, obras, units, start):
        result = {}
        for code, name, kind, status, place in ASSET_SPECS:
            obra = obras[0] if place == "Norte" else obras[1] if place == "Sur" else obras[2]
            asset, _ = ActivoOperacional.objects.update_or_create(
                organizacion=org, codigo=f"{PREFIX}-{code}",
                defaults={"nombre": name, "tipo": kind, "estado": status,
                          "unidad_operacional": units[obra.id], "fecha_alta": start,
                          "metadata": {"obra_id": obra.id, "fabricante": "Equipo demo sintético"}},
            )
            if kind == "vehiculo":
                Vehiculo.objects.update_or_create(
                    activo=asset, defaults={"patente": "DEMO-18", "marca": "Demo", "modelo": "Camión 12 t",
                                             "anio": 2021, "tipo_vehiculo": "camion", "combustible": "diesel",
                                             "capacidad_carga": Decimal("12"), "unidad_capacidad_carga": "t"},
                )
            elif kind == "maquinaria":
                Maquinaria.objects.update_or_create(
                    activo=asset, defaults={"marca": "Demo", "modelo": name, "anio": 2020,
                                             "tipo_maquinaria": name, "combustible": "diesel",
                                             "horometro_actual": Decimal("2240")},
                )
            point_type = (PuntoAmbientalOperacional.Tipo.MEDIDOR_ENERGIA if code == "MED-E"
                          else PuntoAmbientalOperacional.Tipo.PUNTO_AGUA if code == "MED-A"
                          else PuntoAmbientalOperacional.Tipo.OTRO)
            point, _ = PuntoAmbientalOperacional.objects.update_or_create(
                organizacion=org, codigo=f"{PREFIX}-{code}-POINT",
                defaults={"nombre": f"Punto {name}", "tipo": point_type, "activo": asset,
                          "obra": obra, "unidad_operacional": units[obra.id],
                          "ubicacion": f"{obra.nombre} — sector operativo"},
            )
            result[code] = (asset, point)
        return result

    def _maintenance(self, org, assets, end):
        specs = (
            ("EXC-02", "Cambio de aceite y filtros", -92, "realizado"),
            ("RET-01", "Revisión hidráulica", -5, "vencido"),
            ("GEN-01", "Inspección preventiva generador", 12, "programado"),
            ("CAM-02", "Revisión de frenos y neumáticos", 28, "programado"),
            ("MED-E", "Calibración de medidor", -33, "realizado"),
        )
        for code, name, offset, state in specs:
            asset = assets[code][0]
            MantenimientoActivo.objects.update_or_create(
                organizacion=org, activo=asset, tipo=name, fecha_programada=end + timedelta(days=offset),
                defaults={"estado": state, "fecha_realizada": end + timedelta(days=offset + 1) if state == "realizado" else None,
                          "descripcion": f"Plan de mantenimiento de {asset.nombre}.",
                          "proveedor_responsable": "Taller demo de obra"},
            )

    def _evidence(self, org, obras, start, end, users):
        kinds = (
            ("boleta_electrica", "Cuenta eléctrica", "validada"),
            ("factura_agua", "Cuenta de agua", "validada"),
            ("factura_combustible", "Factura de diésel", "validada"),
            ("guia_despacho", "Guía de acero y hormigón", "validada"),
            ("ticket_pesaje", "Pesaje de residuos", "pendiente"),
            ("manifiesto_retiro", "Manifiesto de retiro", "observada"),
            ("documento_transporte", "Respaldo de viajes", "vinculada"),
            ("registro_mantenimiento", "Orden de mantenimiento", "validada"),
            ("informe_medicion_ruido", "Informe acústico", "validada"),
            ("informe_muestreo_atmosferico", "Informe de polvo", "pendiente"),
            ("ficha_tecnica_material", "Ficha técnica de insumos", "validada"),
        )
        result = {}
        for index, obra in enumerate(obras):
            periods = 6 if index == 0 else 4 if index == 1 else 2
            for period in range(periods):
                day = (min(end, start + timedelta(days=period * 30 + index * 10 + 8))
                       if index < 2 else end - timedelta(days=45 - period * 25))
                for kind, name, state in kinds[:11 if index == 0 else 8 if index == 1 else 5]:
                    label = f"{PREFIX} {name} {obra.nombre} {day:%Y-%m}"
                    evidence, _ = EvidenciaObra.objects.update_or_create(
                        organizacion=org, obra=obra, nombre=label,
                        defaults={"tipo_evidencia": kind, "estado_documental": state,
                                  "fecha_documento": day, "usuario_origen": users["ambiental"],
                                  "observaciones": "Respaldo sintético para revisión de producto; sin archivo real.",
                                  "metadata_extraccion": {"showcase": PREFIX, "periodo": day.isoformat()}},
                    )
                    result[obra.id, kind, period] = evidence
        return result

    def _material_catalog(self, org, admin, start, materials):
        extra = (
            ("ARIDOS", "Áridos clasificados", "ton", "4.0"),
            ("CEMENTO", "Cemento", "ton", "735.0"),
            ("MADERA", "Madera de moldaje", "ton", "120.0"),
            ("YESO", "Yeso-cartón", "ton", "210.0"),
            ("AISLANTE", "Aislante térmico", "ton", "360.0"),
        )
        from apps.analytics.models import FactorAmbiental
        for suffix, name, unit, factor_value in extra:
            code = f"HORIZONTE-{suffix}"
            material, _ = MaterialOperacional.objects.update_or_create(
                organizacion=org, codigo=code,
                defaults={"nombre": name, "categoria": "materiales", "unidad_base": unit},
            )
            factor, _ = FactorAmbiental.objects.update_or_create(
                organizacion=org, codigo=f"{code}-FACTOR",
                defaults={"nombre": f"Factor demo {name}", "categoria": "materiales",
                          "sustancia_impacto": "CO2e", "unidad_entrada": unit, "unidad_resultado": "kgCO2e",
                          "contexto": {"provider": "DEMO_SEED", "fuente": "Sintético; no oficial"}},
            )
            version = factor.versiones.order_by("-version").first()
            if version is None:
                version = VersionFactorAmbiental.objects.create(
                    factor=factor, version=1, valor=Decimal(factor_value),
                    fuente="Demo sintético — no usar en producción", referencia="N/A (showcase)",
                    contexto={"provider": "DEMO_SEED"}, vigencia_desde=start - timedelta(days=30),
                    estado=VersionFactorAmbiental.Estado.BORRADOR,
                )
            for state in ("pruebas", "validado", "activo"):
                if version.estado != state and version.estado != "activo":
                    version = transition_factor_version(version, state)
            if not material.mapeos_factor.filter(estado="aprobado").exists():
                mapping = propose_material_mapping(org, material, factor, start - timedelta(days=30), None, admin)
                approve_material_mapping(mapping.pk, org, admin)
            materials[code] = material
        return materials

    def _activity(self, org, obra, domain, day, slot, name, units, processes):
        code = f"{PREFIX}-{obra.codigo_obra[-1]}-{day:%Y%m%d}-{domain}-{slot:02d}"
        if ActividadOperacional.objects.filter(organizacion=org, codigo=code).exists():
            return None
        kind = {
            "energia": "consumo_energia", "agua": "consumo_agua", "combustibles": "consumo_combustible",
            "transporte": "transporte", "materiales": "movimiento_material", "residuos": "gestion_residuo",
            "ruido": "monitoreo_ruido", "aire": "monitoreo_emisiones_atmosfericas", "suelo": "gestion_suelo",
        }[domain]
        moment = at(day, 8 + slot % 8, (slot * 13 + day.day) % 50)
        return ActividadOperacional.objects.create(
            organizacion=org, obra=obra, codigo=code, nombre=name, tipo=kind,
            timestamp_inicio=moment, timestamp_fin=moment + timedelta(minutes=45),
            unidad_operacional=units[obra.id], proceso_operacional=processes[obra.id, domain],
            estado=ActividadOperacional.Estado.LISTA_EVALUACION,
            metadata={"showcase": PREFIX, "fase": self._phase((day - self.start).days)},
        )

    @staticmethod
    def _phase(offset):
        return "instalacion" if offset < 30 else "fundaciones" if offset < 70 else "estructura" if offset < 120 else "instalaciones" if offset < 150 else "terminaciones"

    def _observation(self, org, activity, source, concept, value, unit, evidence=None):
        return capture_observation(
            channel="manual", organization=org, activity=activity, source=source,
            concept=concept, numeric_value=value, unit=unit, timestamp=activity.timestamp_fin,
            evidence=evidence, state=Observacion.Estado.VALIDADA,
        )

    def _history(self, org, obras, start, end, units, processes, source, assets, evidence, materials):
        self.start = start
        vehicle = assets["CAM-02"][0].vehiculo
        for index, obra in enumerate(obras):
            route, _ = RutaOperacional.objects.update_or_create(
                organizacion=org, codigo=f"{PREFIX}-SUPPLY-ROUTE-{index + 1}",
                defaults={"nombre": f"Ruta proveedores–{obra.nombre}",
                          "origen_nombre": "Centro de distribución Biobío",
                          "destino_nombre": obra.nombre, "distancia_planificada": Decimal("48") + index * 8,
                          "fuente_distancia": "Planificación demo sintética"},
            )
            duration = 180 if index == 0 else 140 if index == 1 else 55
            first = 0 if index == 0 else 40 if index == 1 else 125
            cadence = 1 if index == 0 else 2 if index == 1 else 3
            for offset in range(first, min(first + duration, 180)):
                day = start + timedelta(days=offset)
                phase = self._phase(offset)
                period = min(5, offset // 30)
                ev = lambda kind: evidence.get((obra.id, kind, min(period, 5 if index == 0 else 3 if index == 1 else 1)))
                if offset % (7 * cadence) == index:
                    base = 210 if phase == "instalacion" else 380 if phase == "fundaciones" else 540 if phase == "estructura" else 700 if phase == "instalaciones" else 610
                    value = amount(base, offset, bump=Decimal("0.42") if 132 <= offset <= 139 else 0)
                    activity = self._activity(org, obra, "energia", day, 1, "Lectura eléctrica de faena", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="energia",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, tipo_recurso="red_electrica")
                        self._observation(org, activity, source, "consumo_energia", value, "kWh", ev("boleta_electrica"))
                        self._calculate_if_eligible(activity)
                if offset % (5 * cadence) == (index + 1) % (5 * cadence):
                    base = 17 if phase in {"instalacion", "terminaciones"} else 25
                    value = amount(base, offset, bump=Decimal("0.30") if 139 <= offset <= 145 else 0)
                    activity = self._activity(org, obra, "agua", day, 2, "Consumo de agua operativa", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="agua",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, tipo_recurso="red_publica")
                        self._observation(org, activity, source, "consumo_agua", value, "m3", ev("factura_agua"))
                if index < 2 and offset % (4 * cadence) == index:
                    base = 150 if phase == "instalacion" else 132 if phase == "fundaciones" else 92 if phase == "estructura" else 57 if phase == "instalaciones" else 38
                    machine_code = "EXC-02" if index == 0 else "RET-01"
                    asset, point = assets[machine_code]
                    activity = self._activity(org, obra, "combustibles", day, 3, f"Carga de diésel {asset.nombre}", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="combustible_movil",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="punto", punto=point, activo=asset, obra=obra,
                            destino_operacional="maquinaria", tipo_recurso="diesel")
                        self._observation(org, activity, source, "combustible_consumido", amount(base, offset), "L", ev("factura_combustible"))
                        activity.activos.add(asset)
                        self._calculate_if_eligible(activity)
                if offset % (6 * cadence) == (index + 2) % (6 * cadence):
                    distance = amount(42 + (offset % 4) * 8, offset)
                    load = amount(6 + (offset % 3) * 2, offset)
                    activity = self._activity(org, obra, "transporte", day, 4, "Viaje de abastecimiento de insumos", units, processes)
                    if activity:
                        od = self._observation(org, activity, source, "distancia_recorrida_km", distance, "km", ev("documento_transporte"))
                        oc = self._observation(org, activity, source, "masa_transportada_t", load, "t", ev("documento_transporte"))
                        fuel = self._observation(org, activity, source, "combustible_consumido_l", amount(13, offset), "L")
                        ViajeOperacional.objects.create(organizacion=org, actividad=activity, codigo=activity.codigo,
                            vehiculo=vehicle, ruta=route, origen_nombre="Centro de distribución Biobío",
                            destino_nombre=obra.nombre, fecha_salida=activity.timestamp_inicio,
                            fecha_llegada=activity.timestamp_fin, observacion_distancia=od,
                            observacion_carga=oc, observacion_combustible=fuel,
                            estado_carga="cargado", tipo_gestion="tercerizado" if offset % 3 == 0 else "propio",
                            estado="completado")
                        self._calculate_if_eligible(activity)
                if offset % (4 * cadence) == (index + 1) % (4 * cadence):
                    choices = ("HORIZONTE-ARIDOS", "HORIZONTE-CEMENTO", "HORIZONTE-HORMIGON") if phase in {"instalacion", "fundaciones"} else (
                        "HORIZONTE-HORMIGON", "HORIZONTE-ACERO", "HORIZONTE-ARIDOS") if phase == "estructura" else (
                        "HORIZONTE-MADERA", "HORIZONTE-YESO", "HORIZONTE-AISLANTE")
                    material = materials[choices[offset % len(choices)]]
                    base = 12 if material.unidad_base == "ton" else 18
                    value = amount(base, offset, bump=Decimal("0.35") if offset in {79, 81} else 0)
                    activity = self._activity(org, obra, "materiales", day, 5, f"Recepción {material.nombre}", units, processes)
                    if activity:
                        obs = self._observation(org, activity, source, "cantidad_material", value, material.unidad_base, ev("guia_despacho"))
                        EventoMaterial.objects.create(organizacion=org, material=material, actividad=activity, obra=obra,
                            tipo="recepcion", fecha_hora=activity.timestamp_inicio, observacion_cantidad=obs,
                            fuente=source, evidencia=ev("guia_despacho"), proceso=processes[obra.id, "materiales"])
                        self._calculate_if_eligible(activity)
                if offset % (7 * cadence) == (index + 3) % (7 * cadence):
                    waste = ("escombros", "madera", "carton", "metales", "mixtos")[offset % 5]
                    hazardous = index == 0 and offset == 157
                    value = amount(1250 if phase == "terminaciones" else 800, offset,
                                   bump=Decimal("0.33") if offset == 157 else 0)
                    activity = self._activity(org, obra, "residuos", day, 6, f"Retiro de residuos {waste}", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="residuo",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, tipo_residuo="aceites_usados" if hazardous else waste,
                            clasificacion_residuo="peligroso" if hazardous else "no_peligroso",
                            destino_operacional="disposicion" if hazardous else "reciclaje",
                            proveedor_gestor="Gestor demo autorizado")
                        self._observation(org, activity, source, "cantidad_residuo", value, "kg", ev("ticket_pesaje"))
                if offset % (14 * cadence) == (index + 5) % (14 * cadence):
                    activity = self._activity(org, obra, "ruido", day, 7, "Medición acústica diurna", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="ruido",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, metrica="laeq_diurno")
                        self._observation(org, activity, source, "nivel_ruido", amount(58 + offset % 5, offset), "dB(A)", ev("informe_medicion_ruido"))
                if index < 2 and offset % 30 == 11 + index:
                    activity = self._activity(org, obra, "aire", day, 8, "Muestreo de material particulado", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="emisiones_atmosfericas",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, metrica="mp10")
                        self._observation(org, activity, source, "mp10", amount(32 + offset % 11, offset), "ug/m3", ev("informe_muestreo_atmosferico"))
                if index == 0 and offset % 30 == 17:
                    activity = self._activity(org, obra, "suelo", day, 9, "Inspección de suelo de faena", units, processes)
                    if activity:
                        RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="suelo",
                            periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                            granularidad="obra", obra=obra, metrica="superficie_inspeccionada")
                        self._observation(org, activity, source, "superficie_inspeccionada", amount(180, offset), "m2")
        # A final-day utility reading closes the exact 180-day window rather
        # than relying on the weekly cadence to land on day 180 by chance.
        obra = obras[0]
        activity = self._activity(org, obra, "energia", end, 10, "Lectura eléctrica de cierre de período", units, processes)
        if activity:
            RegistroFlujoAmbiental.objects.create(organizacion=org, actividad=activity, flujo="energia",
                periodo_inicio=activity.timestamp_inicio, periodo_fin=activity.timestamp_fin,
                granularidad="obra", obra=obra, tipo_recurso="red_electrica")
            self._observation(org, activity, source, "consumo_energia", amount(610, 179), "kWh")
            self._calculate_if_eligible(activity)

    @staticmethod
    def _calculate_if_eligible(activity):
        if activity.calculos_ambientales.exists():
            return
        from apps.analytics.services.methodology_selector import select_methodology
        if select_methodology(activity)["seleccion"]:
            calculate_activity(activity)

    def _sensors(self, org, obras, assets, start, end, evidence):
        technical_source, _ = FuenteDatos.objects.get_or_create(
            organizacion=org, nombre="Instrumentación showcase 180D",
            defaults={"tipo": FuenteDatos.Tipo.SENSOR, "descripcion": "Fuente técnica sintética de sensores."},
        )
        specs = (
            ("ENERGIA", "Medidor eléctrico principal", "energia", "energia", "consumo_energia", "kWh", "MED-E", "operativo"),
            ("AGUA", "Medidor de agua principal", "agua", "agua", "consumo_agua", "m3", "MED-A", "operativo"),
            ("DIESEL", "Telemetría estanque diésel", "combustible", "combustibles", "combustible_consumido", "L", "EST-D", "operativo"),
            ("RUIDO", "Sonómetro de perímetro", "ambiente", "ruido", "nivel_ruido", "dB(A)", "PTO-L", "requiere_revision"),
            ("MP10", "Monitor de polvo MP10", "ambiente", "", "mp10", "ug/m3", "PTO-L", "operativo"),
            ("HORAS", "Horómetro excavadora", "maquinaria", "combustibles", "horas_operacion", "h", "EXC-02", "operativo"),
            ("HUMEDAD", "Humedad de faena", "ambiente", "agua", "humedad", "%", "MED-A", "operativo"),
            ("OFFLINE", "Sensor de apoyo temporal", "ambiente", "ruido", "nivel_ruido", "dB(A)", "PTO-L", "fuera_servicio"),
        )
        for index, (suffix, name, sensor_type, scope, concept, unit, asset_code, status) in enumerate(specs):
            obra = obras[1] if suffix == "DIESEL" else obras[0]
            asset, point = assets[asset_code]
            device, _ = DispositivoSensor.objects.update_or_create(
                dispositivo_id=f"{PREFIX}-{suffix}",
                defaults={"organizacion": org, "obra": obra, "nombre": name,
                          "tipo_sensor": sensor_type, "ambito_operacional": scope,
                          "activo_operacional": asset, "punto_ambiental": point,
                          "fuente_datos": technical_source, "estado": status, "fecha_alta": start,
                          "fabricante": "Instrumentación demo", "modelo": "Serie 180D",
                          "ubicacion": f"{obra.nombre} — sector controlado", "activo": status != "fuera_servicio"},
            )
            calibration_day = end - timedelta(days=40 + index * 3)
            if not device.calibraciones.filter(fecha=calibration_day).exists():
                from apps.iot.services_v2 import registrar_calibracion
                registrar_calibracion(device, {
                    "fecha": calibration_day, "tipo": "Calibración preventiva",
                    "resultado": CalibracionSensor.Resultado.APROBADA,
                    "fecha_proxima_calibracion": end + timedelta(days=20 + index * 5),
                    "responsable": "Equipo ambiental demo",
                    "evidencia": evidence.get((obra.id, "registro_mantenimiento", 0)),
                })
            if suffix == "RUIDO" and device.estado != DispositivoSensor.Estado.REQUIERE_REVISION:
                device.estado = DispositivoSensor.Estado.REQUIERE_REVISION
                device.save(update_fields=["estado", "updated_at"])
            # Roughly 26 readings per primary device; one offline device has
            # only a short historical run, never a fabricated current reading.
            offsets = range(0, 180, 7 + index % 3) if suffix != "OFFLINE" else range(12, 45, 9)
            for offset in offsets:
                day = start + timedelta(days=offset)
                if day > end:
                    break
                stamp = at(day, 7 + index % 4, index * 4)
                if device.lecturas_v2.filter(timestamp=stamp, concepto=concept).exists():
                    continue
                base = {"ENERGIA": 425, "AGUA": 23, "DIESEL": 155, "RUIDO": 59,
                        "MP10": 37, "HORAS": 7, "HUMEDAD": 63, "OFFLINE": 56}[suffix]
                registrar_lectura(device, {
                    "timestamp": stamp, "concepto": concept, "valor_numerico": amount(base, offset),
                    "unidad": unit, "metadata_tecnica": {"showcase": PREFIX, "origen": "lectura sintética"},
                })

    def _management(self, org, obras, users, start, end, evidence):
        specs = (
            (obras[0], "Alza de consumo eléctrico en instalaciones", "energia", "seguimiento", "alto", 135),
            (obras[0], "Segregación de residuos de terminaciones", "residuos", "implementando", "medio", 158),
            (obras[0], "Control de polvo en estructura", "emisiones_atmosfericas", "cerrada", "medio", 86),
            (obras[1], "Mantención hidráulica atrasada", "combustibles", "detectada", "alto", 149),
            (obras[1], "Conciliación de retiro de residuos", "residuos", "seguimiento", "medio", 160),
            (obras[2], "Completar trazabilidad inicial de agua", "agua", "analizando", "medio", 165),
        )
        result = []
        for index, (obra, title, category, state, risk, offset) in enumerate(specs):
            problem, _ = ProblematicaAmbiental.objects.update_or_create(
                organizacion=org, obra=obra, titulo=f"{PREFIX} {title}",
                defaults={"descripcion": "Situación sintética trazable a la historia de obra.",
                          "categoria": category, "indicador": f"{category}_showcase",
                          "unidad_indicador": "unidad operacional", "valor_inicial": Decimal("100"),
                          "objetivo_meta": Decimal("85"), "fecha_deteccion": start + timedelta(days=offset),
                          "nivel_riesgo": risk, "estado": state,
                          "responsable_usuario": users["ambiental"],
                          "metadata": {"showcase": PREFIX, "obra_codigo": obra.codigo_obra}},
            )
            result.append(problem)
            if state != "detectada":
                action_state = "evaluada" if state == "cerrada" else "seguimiento" if state == "seguimiento" else "en_implementacion"
                AccionMejoraAmbiental.objects.update_or_create(
                    problematica=problem, titulo=f"{PREFIX} Acción: {title}",
                    defaults={"descripcion": "Medida de control con responsable y fecha de revisión.",
                              "estado": action_state, "responsable_usuario": users["ambiental"],
                              "responsable": "Responsable ambiental",
                              "fecha_propuesta": start + timedelta(days=offset + 2),
                              "fecha_inicio": start + timedelta(days=offset + 5),
                              "fecha_objetivo": end + timedelta(days=14 if state != "cerrada" else -20),
                              "fecha_termino_real": end - timedelta(days=24) if state == "cerrada" else None,
                              "metadata": {"showcase": PREFIX}},
                )
        return result

    def _compliance(self, org, obras, start, end):
        """Documentary control only: no invented legal thresholds or compliance percent."""
        for index, obra in enumerate(obras):
            periods = 6 if index == 0 else 4 if index == 1 else 1
            for period in range(periods):
                day = min(end, start + timedelta(days=period * 30 + 26)) if index < 2 else end - timedelta(days=20)
                for kind, title in (("informe_gestion", "Seguimiento ambiental mensual"),
                                    ("registro_rcd", "Control de retiro de residuos")):
                    pending = period == periods - 1 and kind == "registro_rcd"
                    document, _ = DocumentoAmbiental.objects.update_or_create(
                        organizacion=org, obra=obra,
                        nombre=f"{PREFIX} {title} {obra.nombre} {day:%Y-%m}",
                        defaults={"tipo_documento": kind, "industria": "construccion",
                                  "fecha_documento": day, "periodo_inicio": day.replace(day=1),
                                  "periodo_fin": day, "fuente_origen": "manual",
                                  "estado_procesamiento": "extraido" if pending else "validado",
                                  "estado_validacion": "pendiente" if pending else "valido",
                                  "resumen": "Consolidado documental sintético, sujeto a revisión humana.",
                                  "metadata": {"showcase": PREFIX}},
                    )
                    if pending:
                        AlertaCumplimientoAmbiental.objects.update_or_create(
                            organizacion=org, documento=document, tipo_alerta="control_documental_demo",
                            defaults={"severidad": "amarillo", "titulo": f"{PREFIX} Revisar respaldo de retiro — {obra.nombre}",
                                      "descripcion": "El consolidado mensual de residuos espera validación documental.",
                                      "estado": "abierta", "fecha_evento": day,
                                      "accion_sugerida": "Revisar manifiesto y pesaje del período.",
                                      "metadata": {"showcase": PREFIX}},
                        )

    def _governance(self, org, users, problems, evidence, end):
        reviewer = users["revisor"]
        for index, problem in enumerate(problems[:3]):
            state = ("pendiente", "solicita_antecedentes", "validada")[index]
            if RevisionProfesionalAmbiental.objects.filter(organizacion=org, problematica=problem, version=1).exists():
                continue
            review = RevisionProfesionalAmbiental.objects.create(
                organizacion=org, tipo=RevisionProfesionalAmbiental.Tipo.PROBLEMATICA,
                problematica=problem, estado=state, profesional=reviewer,
                profesional_nombre="Revisor ambiental demo", profesional_cargo="Revisión técnica",
                fecha=at(end - timedelta(days=12 + index * 9)),
                conclusion="Requiere evidencia complementaria." if state != "validada" else "Control verificado.",
            )
            HallazgoRevisionProfesional.objects.create(
                revision=review, tipo="falta_antecedente" if state != "validada" else "validacion",
                severidad="alta" if index == 0 else "media",
                observacion=f"Hallazgo sintético asociado a {problem.titulo}.",
                recomendacion="Conciliar antecedente documental con resultado operacional.",
            )
        activity = ActividadOperacional.objects.filter(organizacion=org, codigo__startswith=PREFIX,
                                                       tipo="consumo_energia").order_by("timestamp_inicio").first()
        if activity and not DiscrepanciaDato.objects.filter(organizacion=org, actividad=activity,
                                                            concepto="consumo_energia").exists():
            observation = activity.observaciones.filter(concepto="consumo_energia").first()
            secondary_source, _ = FuenteDatos.objects.get_or_create(
                organizacion=org, nombre="Lectura secundaria de apoyo showcase",
                defaults={"tipo": FuenteDatos.Tipo.MANUAL,
                          "descripcion": "Lectura independiente para conciliación sintética."},
            )
            secondary = capture_observation(
                channel="manual", organization=org, activity=activity, source=secondary_source,
                concept="consumo_energia", numeric_value=(observation.valor_numerico * Decimal("1.06")).quantize(Decimal("0.001")),
                unit=observation.unidad, timestamp=activity.timestamp_fin + timedelta(minutes=2),
                state=Observacion.Estado.PENDIENTE,
            )
            difference = abs(secondary.valor_numerico - observation.valor_numerico)
            discrepancy = DiscrepanciaDato.objects.create(
                organizacion=org, actividad=activity, concepto="consumo_energia",
                estado="requiere_revision", severidad="media",
                diferencia_absoluta=difference,
                diferencia_relativa=(difference / observation.valor_numerico).quantize(Decimal("0.00000001")),
                motivo="Dos lecturas manuales de apoyo presentan una diferencia moderada y requieren conciliación.",
                responsable=reviewer,
            )
            discrepancy.observaciones.add(observation, secondary)
        for index, problem in enumerate(problems[:2]):
            ExpedienteAmbiental.objects.update_or_create(
                problematica=problem, version=1,
                defaults={"resumen_ejecutivo": f"Antecedentes sintéticos de {problem.titulo}.",
                          "contenido_procesado": {"showcase": PREFIX, "problematica_id": problem.id},
                          "estado": "en_revision" if index == 0 else "recopilando_antecedentes",
                          "responsable": reviewer, "generado_por": "seed_showcase_180d"},
            )

    def _indicators(self, org, obras, start, end):
        for obra in obras:
            for domain, concept, unit in (("energia", "consumo_energia", "kWh"),
                                          ("agua", "consumo_agua", "m3"),
                                          ("combustibles", "combustible_consumido", "L")):
                indicator, _ = IndicadorAmbiental.objects.update_or_create(
                    organizacion=org, obra=obra, alcance=IndicadorAmbiental.Alcance.OBRA,
                    codigo=f"{PREFIX.lower()}-{domain}",
                    defaults={"nombre": f"{domain.capitalize()} mensual showcase", "tipo": "absoluto",
                              "unidad": unit, "origen_numerador": concept, "activo": True,
                              "direccion_deseable": "menor_es_mejor"},
                )
                cursor = start.replace(day=1)
                while cursor <= end:
                    next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
                    period_start = max(start, cursor)
                    period_end = min(end, next_month - timedelta(days=1))
                    if not ValorIndicador.objects.filter(indicador=indicator, periodo_inicio=period_start,
                                                          periodo_fin=period_end).exists():
                        generate_indicator_value(indicator, period_start, period_end)
                    cursor = next_month

    def _summary(self, org):
        activities = ActividadOperacional.objects.filter(organizacion=org, codigo__startswith=PREFIX)
        rows = Counter(activities.values_list("tipo", flat=True))
        works = Obra.objects.filter(organizacion=org)
        period = activities.order_by("timestamp_inicio").values_list("timestamp_inicio", flat=True).first()
        last = activities.order_by("-timestamp_inicio").values_list("timestamp_inicio", flat=True).first()
        summary = {
            "tenant": org.organizacion_id, "onboarding": org.onboarding_completado,
            "obras": works.count(), "usuarios": org.usuarios.count(),
            "activos": org.activos_operacionales.count(), "infraestructura": org.puntos_ambientales.count(),
            "sensores": org.dispositivos_iot.count(),
            "lecturas": LecturaSensorV2.objects.filter(sensor__organizacion=org).count(),
            "mantenimientos": org.mantenimientos_activos.count(),
            "registros_por_flujo": dict(sorted(rows.items())),
            "evidencias": org.evidencias.count(), "problemas": org.problematicas_ambientales.count(),
            "documentos": org.documentos_ambientales.count(),
            "alertas_documentales": org.alertas_cumplimiento.filter(tipo_alerta="control_documental_demo").count(),
            "acciones": AccionMejoraAmbiental.objects.filter(problematica__organizacion=org).count(),
            "revisiones": org.revisiones_profesionales.count(),
            "discrepancias": org.discrepancias_dato.count(),
            "expedientes": ExpedienteAmbiental.objects.filter(problematica__organizacion=org).count(),
            "calculos": activities.filter(calculos_ambientales__isnull=False).distinct().count(),
            "periodo": f"{period.date()}..{last.date()}" if period and last else "sin actividades",
            "actividades_showcase": activities.count(),
        }
        summary["total_registros_creados"] = sum(summary[key] for key in (
            "actividades_showcase", "activos", "infraestructura", "sensores", "lecturas", "mantenimientos",
            "evidencias", "documentos", "alertas_documentales", "problemas", "acciones",
            "revisiones", "discrepancias", "expedientes",
        ))
        if summary["obras"] < 3 or not summary["onboarding"]:
            raise CommandError("El showcase no supera la validación de obras/onboarding.")
        self.stdout.write(self.style.SUCCESS(str(summary)))
