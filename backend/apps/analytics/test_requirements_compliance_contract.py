from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import LimiteNormativoAmbiental, Organizacion, RestriccionContextual
from .policies.requirements_compliance import EvaluationState, RequirementClass
from .selectors.requirements_compliance import (
    active_operational_restrictions,
    applicable_normative_limits,
)
from .services.requirements_compliance import (
    explain_requirement_result,
    internal_target_contract,
    normative_limit_contract,
    operational_restriction_contract,
)


class RequirementsComplianceContractTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(
            nombre="Contrato Compliance", preset="construccion", region="Biobío"
        )

    def test_normative_limit_is_scoped_and_explainable(self):
        limit = LimiteNormativoAmbiental.objects.create(
            organizacion=self.organization,
            industria="construccion",
            variable_id="ruido_db",
            nombre="Límite de ruido configurado",
            normativa=LimiteNormativoAmbiental.Normativa.DS38,
            limite=Decimal("55"),
            unidad="dB",
            comparador="<=",
            fuente_normativa="Fuente configurada y validada",
            validado=True,
        )
        other = Organizacion.objects.create(nombre="Otro tenant")
        LimiteNormativoAmbiental.objects.create(
            organizacion=other,
            variable_id="ruido_db",
            nombre="Límite externo",
            normativa=LimiteNormativoAmbiental.Normativa.DS38,
            limite=Decimal("20"),
            unidad="dB",
            validado=True,
        )

        selected = applicable_normative_limits(self.organization, "ruido_db").get()
        requirement = normative_limit_contract(selected)
        result = explain_requirement_result(
            requirement,
            observed_value="54.5",
            observed_unit="dB",
            evidence_refs=("evidence:11",),
            result_refs=("calculation:9",),
        )

        self.assertEqual(
            requirement.requirement_class, RequirementClass.NORMATIVE_LIMIT
        )
        self.assertEqual(result.state, EvaluationState.COMPLIES)
        self.assertEqual(result.evidence_refs, ("evidence:11",))
        self.assertEqual(result.result_refs, ("calculation:9",))
        self.assertIn("satisface", result.explanation)

    def test_operational_restriction_uses_explicit_condition(self):
        restriction = RestriccionContextual.objects.create(
            organizacion=self.organization,
            tipo="restriccion_operacional",
            descripcion="Horario máximo configurado",
            contenido={
                "variable": "hora_fin",
                "comparador": "<=",
                "umbral": 20,
                "unidad": "hora",
                "fuente": "Plan operacional aprobado",
            },
        )

        selected = active_operational_restrictions(self.organization).get()
        requirement = operational_restriction_contract(selected)
        result = explain_requirement_result(
            requirement, observed_value=21, observed_unit="hora"
        )

        self.assertEqual(
            requirement.requirement_class, RequirementClass.OPERATIONAL_RESTRICTION
        )
        self.assertEqual(result.state, EvaluationState.DOES_NOT_COMPLY)
        self.assertIn("no satisface", result.explanation)

    def test_internal_target_is_explicit_and_not_an_improvement_record(self):
        requirement = internal_target_contract(
            target_id="energy-intensity-2026",
            organization_id=self.organization.pk,
            variable="intensidad_energia",
            comparator="<=",
            threshold="12.5",
            unit="kWh/m2",
            valid_from=date(2026, 1, 1),
            valid_until=date(2026, 12, 31),
            scope={"work_id": 70},
        )
        result = explain_requirement_result(
            requirement,
            observed_value="12.4",
            observed_unit="kWh/m2",
            evaluated_on=date(2026, 8, 28),
            result_refs=("indicator-value:4",),
        )

        self.assertEqual(
            requirement.requirement_class, RequirementClass.INTERNAL_TARGET
        )
        self.assertEqual(result.state, EvaluationState.COMPLIES)
        self.assertEqual(requirement.scope["work_id"], 70)

    def test_missing_value_and_unit_mismatch_are_not_invented(self):
        requirement = internal_target_contract(
            target_id="water",
            organization_id=self.organization.pk,
            variable="agua",
            comparator="<=",
            threshold=10,
            unit="m3",
        )

        missing = explain_requirement_result(requirement, observed_value=None)
        mismatch = explain_requirement_result(
            requirement, observed_value=5, observed_unit="litros"
        )

        self.assertEqual(missing.state, EvaluationState.NO_DATA)
        self.assertIsNone(missing.observed_value)
        self.assertEqual(mismatch.state, EvaluationState.REQUIRES_REVIEW)

    def test_validity_is_part_of_the_deterministic_result(self):
        today = date.today()
        requirement = internal_target_contract(
            target_id="expired",
            organization_id=self.organization.pk,
            variable="energia",
            comparator="<=",
            threshold=10,
            unit="kWh",
            valid_until=today - timedelta(days=1),
        )

        result = explain_requirement_result(
            requirement, observed_value=5, observed_unit="kWh", evaluated_on=today
        )

        self.assertEqual(result.state, EvaluationState.NOT_APPLICABLE)

    def test_inactive_or_unvalidated_requirements_are_not_selected(self):
        for validated, active in ((False, True), (True, False)):
            LimiteNormativoAmbiental.objects.create(
                organizacion=self.organization,
                variable_id="agua",
                nombre="No aplicable",
                normativa=LimiteNormativoAmbiental.Normativa.OTRO,
                limite=1,
                unidad="m3",
                validado=validated,
                activo=active,
            )
        RestriccionContextual.objects.create(
            organizacion=self.organization,
            tipo="restriccion_operacional",
            descripcion="Expirada",
            contenido={},
            vigente_hasta=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(
            applicable_normative_limits(self.organization, "agua").exists()
        )
        self.assertFalse(active_operational_restrictions(self.organization).exists())
