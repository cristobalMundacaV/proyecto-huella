"""SOURCE-WATCH-01E — Downstream Impact Routing tests."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import MaterialFactorMapping, MaterialOperacional, Organizacion, UsuarioOrganizacion
from apps.analytics.services.factor_governance import transition_factor_version
from apps.analytics.services.material_candidates import (
    build_material_candidate,
    promote_material_candidate,
    review_material_candidate,
)
from apps.analytics.services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from apps.analytics.test_material_candidates import material_fixture

from .change_classification import classify_change
from .impact_routing import NO_KNOWN_IMPACT, UNKNOWN_IMPACT, route_impact
from .models import EnvironmentalSource, SourceState

User = get_user_model()


class OekobaudatImpactRoutingTests(TestCase):
    def setUp(self):
        self.reviewer = User.objects.create_superuser(
            "sw01e-reviewer", "sw01e-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="SOURCE-WATCH-01E org")
        UsuarioOrganizacion.objects.create(user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)

        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")
        self.factor = factor
        self.fixture_profile = fixture_profile

        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-SW01E", nombre="Material", categoria="materiales", unidad_base="kg",
        )
        mapping = propose_material_mapping(self.org, self.material, factor, date(2026, 1, 1), None, self.reviewer)
        self.mapping = approve_material_mapping(mapping.pk, self.org, self.reviewer)

    def _event(self, classification="changed"):
        return {
            "external_id": str(self.fixture_profile.process.process_uuid),
            "classification": classification,
            "snapshot_id": self.fixture_profile.snapshot_id,
            "content_hash": self.fixture_profile.snapshot.content_hash,
            "retrieved_at": None,
        }

    def test_no_impact_when_nothing_changed(self):
        source = self.fixture_profile.process.snapshot.source
        classification = classify_change(self._event(), source)
        impact = route_impact(classification)
        self.assertEqual(impact["impact_level"], NO_KNOWN_IMPACT)

    def test_direct_impact_lists_affected_mapping(self):
        source = self.fixture_profile.process.snapshot.source
        classification = classify_change(self._event(), source)
        # Force a non-no_impact detail to exercise the affected-objects
        # path deterministically, using the real detail shape produced by
        # assess_candidate_impact (mapping_ids always includes our mapping
        # once any impact level above no_impact is returned).
        classification["detail"]["impact"] = "review_required"
        impact = route_impact(classification)
        mapping_ids = [obj["id"] for obj in impact["affected_objects"] if obj["type"] == "MaterialFactorMapping"]
        self.assertIn(self.mapping.pk, mapping_ids)

    def test_routing_never_mutates_mapping(self):
        source = self.fixture_profile.process.snapshot.source
        classification = classify_change(self._event(), source)
        route_impact(classification)
        self.mapping.refresh_from_db()
        self.assertEqual(self.mapping.estado, MaterialFactorMapping.Estado.APROBADO)

    def test_missing_detail_is_unknown_impact_not_no_impact(self):
        classification = {
            "domain": "okobaudat", "detail": {}, "reasons": [], "source_id": 1,
            "source_codigo": "x", "external_id": "y", "classification": "z", "provenance": {},
        }
        impact = route_impact(classification)
        self.assertEqual(impact["impact_level"], UNKNOWN_IMPACT)


class UnmodeledDomainImpactRoutingTests(TestCase):
    def test_legal_domain_fails_closed_to_unknown_impact(self):
        classification = {
            "domain": "legal", "detail": {}, "reasons": ["cambio_en_fuente_legal_requiere_revision_humana"],
            "source_id": 1, "source_codigo": "bcn", "external_id": "norma-1",
            "classification": "legal_norm_changed", "provenance": {},
        }
        impact = route_impact(classification)
        self.assertEqual(impact["impact_level"], UNKNOWN_IMPACT)

    def test_generic_domain_fails_closed_to_unknown_impact(self):
        classification = {
            "domain": "generic", "detail": {}, "reasons": [], "source_id": 1,
            "source_codigo": "retc", "external_id": "x", "classification": UNKNOWN_IMPACT, "provenance": {},
        }
        impact = route_impact(classification)
        self.assertEqual(impact["impact_level"], UNKNOWN_IMPACT)
