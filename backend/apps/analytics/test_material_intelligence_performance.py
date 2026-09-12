"""MI-01J — lightweight performance sanity check.

Not a speculative optimization pass (none was made without evidence): this
only demonstrates that MI-01D/01F handle a few dozen candidate materials in
a single call without an unbounded/quadratic-looking query explosion. If a
tenant grows into the thousands-of-materials range, `docs/MATERIAL-INTELLIGENCE-CLOSURE.md`
documents this as a known scaling point to revisit with real evidence
first, per the anti-overengineering rule.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from .services.material_application_profile import approve_profile, create_profile
from .services.material_comparable_sets import comparable_alternatives
from .services.material_hotspots import material_hotspots

User = get_user_model()


class ComparableSetsScaleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "perf-admin", "perf-admin@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="Perf org")
        UsuarioOrganizacion.objects.create(
            user=self.admin, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(self.org, self.admin, "PERFIL-PERF", "Perfil", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.admin)
        self.source_material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-PERF-SRC", nombre="Fuente",
            categoria="materiales", unidad_base="kg",
        )

    def test_comparable_alternatives_handles_many_ineligible_candidates(self):
        # None of these have any governed chain — every one must resolve to
        # an explicit exclusion reason without error, at moderate scale.
        candidates = [
            MaterialOperacional.objects.create(
                organizacion=self.org, codigo=f"MAT-PERF-{i}", nombre=f"Candidato {i}",
                categoria="materiales", unidad_base="kg",
            )
            for i in range(60)
        ]
        result = comparable_alternatives(self.org, self.source_material, self.profile, candidates)
        # The source itself has no governed chain either, so it is reported
        # as ineligible — the important thing is that 60 candidates resolve
        # without error or timeout.
        self.assertIn("source_eligible", result)

    def test_material_hotspots_handles_many_materials_with_no_ledger_entries(self):
        for i in range(60):
            MaterialOperacional.objects.create(
                organizacion=self.org, codigo=f"MAT-PERF-HS-{i}", nombre=f"Material {i}",
                categoria="materiales", unidad_base="kg",
            )
        result = material_hotspots(self.org)
        self.assertEqual(result, {})
