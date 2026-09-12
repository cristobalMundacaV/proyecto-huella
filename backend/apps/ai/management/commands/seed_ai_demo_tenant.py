"""AI-INTELLIGENCE-01 — idempotent demo tenant seed.

Company: "Constructora Horizonte Demo SpA" — entirely synthetic, for
exercising the conversational assistant end to end. Never used for real
client data (this repository is public; see docs/ai-context/08_TENANCY_
RBAC_SECURITY.md). Safe to re-run: every object is keyed by a fixed,
recognizable id/code and created via `update_or_create`/`get_or_create`.

Builds exclusively on the modern v2 stack (MaterialOperacional,
ActividadOperacional, CalculoAmbiental via `calculate_activity`,
MaterialFactorMapping, IndicadorAmbiental v2, ProblematicaAmbiental) —
never the legacy RegistroEmision/EtapaObra/AlertaCumplimientoAmbiental
models other seed commands use, per this project's own rule against
building new capability on legacy boundaries.
"""
import json
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import (
    ActividadOperacional, EventoMaterial, FactorAmbiental, FuenteDatos, IndicadorAmbiental,
    MaterialOperacional, Obra, Observacion, Organizacion, ProblematicaAmbiental, UsuarioOrganizacion,
    ValorIndicador, VersionFactorAmbiental,
)
from apps.analytics.services.calculation_v2 import calculate_activity
from apps.analytics.services.factor_governance import transition_factor_version
from apps.analytics.services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from apps.analytics.services.system_environmental_catalog import ensure_system_environmental_catalog
from apps.ec3.client import Ec3Client
from apps.ec3.services import ingest_epd, promote_candidate, propose_candidate, propose_mapping, review_candidate

DEMO_ORG_ID = "DEMO_HORIZONTE"
DEMO_ADMIN_USERNAME = "demo-horizonte-admin"
TODAY = timezone.localdate()

MATERIALS = [
    # codigo, nombre, categoria, unidad, factor_kgco2e_por_unidad, cantidad_mensual_kg_equivalente, is_hotspot
    ("HORIZONTE-HORMIGON", "Hormigón H30", "materiales", "m3", Decimal("310.0"), Decimal("40"), True),
    ("HORIZONTE-ACERO", "Acero de refuerzo", "materiales", "ton", Decimal("1850.0"), Decimal("2"), False),
    ("HORIZONTE-DIESEL", "Diésel maquinaria", "combustible", "L", Decimal("2.68"), Decimal("900"), False),
    ("HORIZONTE-ELECTRICIDAD", "Electricidad obra", "energia", "kWh", Decimal("0.39"), Decimal("3200"), False),
    ("HORIZONTE-AGUA", "Agua faena", "agua", "m3", Decimal("0.45"), Decimal("180"), False),
    ("HORIZONTE-RESIDUOS", "Retiro de escombros", "residuos", "kg", Decimal("0.08"), Decimal("2600"), False),
]

MONTHS_OF_HISTORY = 4


def _steel_like_epd(id_, product_name, mean_gwp, category="StructuralSteel"):
    return {
        "id": id_, "doctype": "OpenEPD", "openepd_version": "0.1", "version": 1, "private": False,
        "product_name": f"DEMO SYNTHETIC — {product_name}",
        "declaration_url": "https://example.org/demo-synthetic-epd",
        "program_operator_doc_id": "DEMO-001", "program_operator_version": "1",
        "date_of_issue": "2023-01-01T00:00:00Z", "valid_until": "2033-01-01T00:00:00Z",
        # HORIZONTE-HORMIGON operates in m3 (concrete) — the declared unit
        # must match, never rely on an invented cross-dimension conversion.
        "declared_unit": {"qty": 1, "unit": "m3"},
        "manufacturer": {"web_domain": "demo-manufacturer.example.org", "name": "Demo Manufacturer"},
        "program_operator": {"web_domain": "demo-operator.example.org"},
        "third_party_verifier": {"web_domain": "demo-verifier.example.org"},
        "pcr": {"id": "https://example.org/demo-pcr", "name": "Demo PCR"},
        "compliance": [{"short_name": "EN 15804+A2", "link": "https://example.org/standard"}],
        "applicable_in": ["CL"], "ec3": {"category": category, "product_specific": True},
        "impacts": {"EF 3.0": {"gwp": {"A1A2A3": {"mean": mean_gwp, "unit": "kgCO2e", "rsd": 0.1}}}},
    }


@contextmanager
def _temporarily(**overrides):
    from django.conf import settings

    previous = {key: getattr(settings, key, None) for key in overrides}
    for key, value in overrides.items():
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            setattr(settings, key, value)


class Command(BaseCommand):
    help = ("Crea/actualiza el tenant demo 'Constructora Horizonte Demo SpA' para "
            "ejercitar el asistente de inteligencia ambiental de punta a punta. "
            "Datos 100% sintéticos, seguro de re-ejecutar (idempotente).")

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Limpia el historial operacional regenerable (actividades, cálculos, "
                                 "indicadores, alertas, conversaciones) antes de recrearlo. La "
                                 "organización, obras, materiales y evidencia EC3 (inmutable) se "
                                 "conservan siempre.")

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()
        # EC3_ENABLED/STORAGE_ALLOWED/rights must stay set for the whole run:
        # calculate_activity re-checks them live (factor_block_reason), not
        # only at ingestion time — a real behavior discovered while building
        # this seed, not a guess.
        with _temporarily(EC3_ENABLED=True, EC3_STORAGE_ALLOWED=True,
                          EC3_API_TOKEN="demo-seed-synthetic-not-a-real-credential",
                          EC3_RIGHTS_REFERENCE="DEMO SEED — synthetic rights, not a real license",
                          EC3_RIGHTS_VALID_UNTIL="2099-01-01"), transaction.atomic():
            ensure_system_environmental_catalog()
            org, admin = self._organization_and_admin()
            obras = self._obras(org)
            factors = self._factors(org)
            materials = self._materials(org)
            self._map_materials(org, admin, materials, factors)
            self._ec3_material(org, admin, materials["HORIZONTE-HORMIGON"])
            self._activity_history(org, admin, materials, obras)
            self._indicators(org, obras)
            self._alert(org, obras[0])
        self.stdout.write(self.style.SUCCESS(
            f"Tenant demo listo: organizacion_id={org.organizacion_id}, "
            f"admin={admin.username}, obras={len(obras)}, materiales={len(materials)}."
        ))

    def _reset(self):
        """Clears the demo tenant's alerts, indicators and conversations and
        re-runs `handle()` to rebuild them.

        Deliberately does NOT delete activities/observations/calculations,
        the organization, obras, materials, factor mappings, or any EC3
        evidence/candidate/review: `CalculoAmbiental` is protected by
        `ImpactoAmbiental`/`InputCalculoAmbiental`/`EvaluacionCalidadDato`,
        and `Review`/`EpdVersion` are immutable by design (this codebase's
        core "never delete a historical scientific calculation or governed
        evidence" guarantee, the same one verified throughout EC3-01) — a
        full wipe of those rows is not just inconvenient here, it is
        architecturally impossible, exactly as intended for real historical
        data. `_activity_history`/`_materials`/`_factors`/`_map_materials`/
        `_ec3_material` are already idempotent (they skip anything that
        already exists by a fixed code/id), so leaving that history in
        place and re-running `handle()` is the correct "reset" for this
        demo tenant — it never fabricates a second copy of the same month's
        activity.
        """
        org = Organizacion.objects.filter(organizacion_id=DEMO_ORG_ID).first()
        if org is None:
            return
        from apps.ai.models import Conversation

        Conversation.objects.filter(organizacion=org).delete()
        ProblematicaAmbiental.objects.filter(organizacion=org).delete()
        ValorIndicador.objects.filter(indicador__organizacion=org).delete()
        IndicadorAmbiental.objects.filter(organizacion=org).delete()
        self.stdout.write(self.style.WARNING(
            "Alertas, indicadores y conversaciones del tenant demo eliminados; "
            "historial operacional, materiales y evidencia EC3 (inmutables) se "
            "conservan y se reutilizan."
        ))

    def _organization_and_admin(self):
        org, _ = Organizacion.objects.update_or_create(
            organizacion_id=DEMO_ORG_ID,
            defaults={
                "nombre": "Constructora Horizonte Demo SpA", "preset": "construccion",
                "activa": True,
            },
        )
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username=DEMO_ADMIN_USERNAME,
            defaults={"email": "demo-horizonte-admin@example.invalid", "is_staff": False},
        )
        if created:
            admin.set_unusable_password()
            admin.save(update_fields=["password"])
        UsuarioOrganizacion.objects.update_or_create(
            user=admin, organizacion=org, defaults={"rol": UsuarioOrganizacion.Rol.ADMIN, "activo": True},
        )
        return org, admin

    def _obras(self, org):
        obras = []
        for index, nombre in enumerate(["Edificio Horizonte Norte", "Condominio Horizonte Sur"], start=1):
            obra, _ = Obra.objects.update_or_create(
                organizacion=org, codigo_obra=f"{DEMO_ORG_ID}_OBRA_{index}",
                defaults={"nombre": nombre, "fecha_inicio": TODAY - timedelta(days=200 + index * 10),
                         "estado": "en_ejecucion"},
            )
            obras.append(obra)
        return obras

    def _factors(self, org):
        factors = {}
        for codigo, nombre, categoria, unidad, valor, _, _ in MATERIALS:
            factor, _ = FactorAmbiental.objects.update_or_create(
                organizacion=org, codigo=f"{codigo}-FACTOR",
                defaults={"nombre": f"Factor demo {nombre}", "categoria": categoria,
                         "sustancia_impacto": "CO2e", "unidad_entrada": unidad, "unidad_resultado": "kgCO2e",
                         "contexto": {"provider": "DEMO_SEED", "fuente": "Factor sintético de demostración, no oficial"}},
            )
            version = factor.versiones.order_by("-version").first()
            if version is None:
                version = VersionFactorAmbiental.objects.create(
                    factor=factor, version=1, valor=valor, fuente="Demo sintético — no usar en producción",
                    referencia="N/A (dato de demostración)", contexto={"provider": "DEMO_SEED"},
                    vigencia_desde=TODAY - timedelta(days=365), vigencia_hasta=None,
                    estado=VersionFactorAmbiental.Estado.BORRADOR,
                )
            if version.estado != VersionFactorAmbiental.Estado.ACTIVO:
                for state in ("pruebas", "validado", "activo"):
                    if version.estado == state:
                        continue
                    version = transition_factor_version(version, state)
            factors[codigo] = factor
        return factors

    def _materials(self, org):
        materials = {}
        for codigo, nombre, categoria, unidad, _, _, _ in MATERIALS:
            material, _ = MaterialOperacional.objects.update_or_create(
                organizacion=org, codigo=codigo,
                defaults={"nombre": nombre, "categoria": categoria, "unidad_base": unidad},
            )
            materials[codigo] = material
        return materials

    def _map_materials(self, org, admin, materials, factors):
        # HORIZONTE-HORMIGON is mapped further down via a real EC3 governance
        # chain instead (_ec3_material) — mapping it generically here first
        # would overlap and block that EC3 mapping from being approved.
        for codigo in materials:
            if codigo == "HORIZONTE-HORMIGON":
                continue
            material = materials[codigo]
            factor = factors[codigo]
            if material.mapeos_factor.filter(estado="aprobado").exists():
                continue
            mapping = propose_material_mapping(org, material, factor, TODAY - timedelta(days=365), None, admin)
            approve_material_mapping(mapping.pk, org, admin)

    def _activity_history(self, org, admin, materials, obras):
        source, _ = FuenteDatos.objects.get_or_create(organizacion=org, nombre="Registro manual demo", tipo="manual")
        for month_index in range(MONTHS_OF_HISTORY):
            at = timezone.make_aware(
                timezone.datetime.combine(TODAY - timedelta(days=30 * month_index), timezone.datetime.min.time()),
            )
            for material_index, (codigo, _, _, unidad, _, cantidad_base, is_hotspot) in enumerate(MATERIALS):
                material = materials[codigo]
                obra = obras[material_index % len(obras)]
                # Deliberately incomplete: skip creating a real observation for
                # the water material in the most recent month, so the
                # assistant must say "no data" rather than invent a value.
                if codigo == "HORIZONTE-AGUA" and month_index == 0:
                    continue
                cantidad = cantidad_base * (Decimal("1.6") if is_hotspot else Decimal("1.0"))
                activity_code = f"{DEMO_ORG_ID}_{codigo}_{month_index:02d}"
                if ActividadOperacional.objects.filter(organizacion=org, codigo=activity_code).exists():
                    continue
                activity = ActividadOperacional.objects.create(
                    organizacion=org, obra=obra, codigo=activity_code,
                    nombre=f"Recepción {material.nombre} — mes {month_index}",
                    tipo="movimiento_material", timestamp_inicio=at,
                )
                observation = Observacion.objects.create(
                    organizacion=org, actividad=activity, fuente=source, concepto="cantidad_material",
                    valor_numerico=cantidad, unidad=unidad, timestamp_observacion=at,
                    estado=Observacion.Estado.VALIDADA,
                )
                EventoMaterial.objects.create(
                    organizacion=org, material=material, actividad=activity, obra=obra,
                    tipo=EventoMaterial.Tipo.RECEPCION, fecha_hora=at, observacion_cantidad=observation,
                    fuente=source,
                )
                calculate_activity(activity)

    def _indicators(self, org, obras):
        indicator, _ = IndicadorAmbiental.objects.update_or_create(
            organizacion=org, codigo="co2e_total_demo", alcance=IndicadorAmbiental.Alcance.ORGANIZACION,
            defaults={"nombre": "Emisiones totales A1-A3 (demo)", "tipo": IndicadorAmbiental.Tipo.ABSOLUTO,
                     "unidad": "kgCO2e", "origen_numerador": "material_ledger", "activo": True},
        )
        for month_index in range(MONTHS_OF_HISTORY):
            start = TODAY - timedelta(days=30 * (month_index + 1))
            end = TODAY - timedelta(days=30 * month_index)
            ValorIndicador.objects.get_or_create(
                indicador=indicator, periodo_inicio=start, periodo_fin=end, version=1,
                defaults={"valor": Decimal("12000") - Decimal(month_index * 400), "unidad": "kgCO2e",
                         "fuente_calculo": "material_ledger_totals (demo)"},
            )
        # Deliberately incomplete indicator: no ValorIndicador history at all,
        # so the assistant must say so explicitly instead of inventing a trend.
        IndicadorAmbiental.objects.update_or_create(
            organizacion=org, codigo="agua_intensidad_demo", alcance=IndicadorAmbiental.Alcance.ORGANIZACION,
            defaults={"nombre": "Intensidad de agua (demo, sin histórico aún)",
                     "tipo": IndicadorAmbiental.Tipo.INTENSIDAD, "unidad": "m3/m2",
                     "origen_numerador": "agua_consumida", "activo": True},
        )

    def _alert(self, org, obra):
        ProblematicaAmbiental.objects.get_or_create(
            organizacion=org, titulo="Consumo de hormigón sobre lo esperado",
            defaults={"descripcion": "El hotspot de hormigón supera el patrón histórico de la obra (dato demo).",
                     "categoria": "materiales", "obra": obra, "valor_inicial": Decimal("12000"),
                     "objetivo_meta": Decimal("9000"), "fecha_deteccion": TODAY,
                     "estado": ProblematicaAmbiental.Estado.DETECTADA,
                     "nivel_riesgo": ProblematicaAmbiental.Riesgo.ALTO},
        )

    def _ec3_reviewer(self):
        # EC3 governance (apps.ec3.services.require_reviewer) always requires
        # a superuser, deliberately independent of any tenant's own ADMIN
        # role — this is a distinct internal actor-of-record for that
        # governed step, not a login-capable demo account: it never gets a
        # usable password and is not added as a member of the demo tenant.
        User = get_user_model()
        reviewer, created = User.objects.get_or_create(
            username="demo-horizonte-ec3-reviewer",
            defaults={"email": "demo-horizonte-ec3-reviewer@example.invalid", "is_superuser": True, "is_staff": True},
        )
        if created:
            reviewer.set_unusable_password()
            reviewer.save(update_fields=["password"])
        return reviewer

    def _ec3_material(self, org, admin, material):
        # Called from within handle()'s outer _temporarily(...) block, which
        # keeps EC3_ENABLED/etc. set for the whole run — required because
        # calculate_activity re-checks them live, not only at ingestion time.
        reviewer = self._ec3_reviewer()
        baseline_session = Mock()
        baseline_session.get.return_value = _mock_response(_steel_like_epd("demohrz1", "Concreto premezclado", 1800))
        baseline_client = Ec3Client(session=baseline_session, limiter=Mock(), sleep=Mock())
        if not material.ec3_candidates.filter(promoted_version__isnull=False).exists():
            version = ingest_epd("demohrz1", reviewer, client=baseline_client)
            candidate = propose_candidate(material, version, reviewer)
            context = {field: "Demo sintético — revisión humana simulada, no real"
                      for field in ("technical_basis", "geographic_basis", "temporal_basis",
                                   "standard_basis", "verification_basis", "note")}
            review_candidate(candidate.pk, reviewer, "approved", "EF 3.0", context)
            candidate = promote_candidate(candidate.pk, reviewer)
            for state in ("pruebas", "validado", "activo"):
                transition_factor_version(candidate.promoted_version, state)
            candidate = propose_mapping(candidate.pk, reviewer, TODAY - timedelta(days=300))
            approve_material_mapping(candidate.mapping_id, org, admin)

        # A second, cheaper EPD proposed for the same material but never
        # mapped/promoted — a real "potential opportunity" preview
        # (apps.ec3.opportunity.material_candidate_opportunities) without
        # asserting adoption.
        if not material.ec3_candidates.filter(promoted_version__isnull=True).exists():
            cheaper_session = Mock()
            cheaper_session.get.return_value = _mock_response(
                _steel_like_epd("demohrz2", "Concreto premezclado bajo carbono", 900),
            )
            cheaper_client = Ec3Client(session=cheaper_session, limiter=Mock(), sleep=Mock())
            cheaper_version = ingest_epd("demohrz2", reviewer, client=cheaper_client)
            propose_candidate(material, cheaper_version, reviewer)


def _mock_response(payload):
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.iter_content.return_value = [json.dumps(payload).encode()]
    return response
