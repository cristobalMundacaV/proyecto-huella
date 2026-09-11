from datetime import date
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import (
    FactorAmbiental,
    MaterialOperacional,
    Organizacion,
    UsuarioOrganizacion,
    VersionFactorAmbiental,
)
from .models.material_factor_mapping import MaterialFactorMapping, mapping_write
from .services.material_factor_mapping import (
    approve_material_mapping,
    propose_material_mapping,
    reject_material_mapping,
    revoke_material_mapping,
)

User = get_user_model()


class MaterialFactorMappingLifecycleTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Mapeo material")
        self.other_org = Organizacion.objects.create(nombre="Otro tenant mapeo")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-ACERO", nombre="Acero", categoria="acero", unidad_base="kg",
        )
        self.global_factor = FactorAmbiental.objects.create(
            organizacion=None, codigo="factor-global-acero", nombre="Acero global",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.tenant_factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-tenant-acero", nombre="Acero tenant",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.other_org_factor = FactorAmbiental.objects.create(
            organizacion=self.other_org, codigo="factor-otro-tenant", nombre="Ajeno",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.proposer = User.objects.create_user("proponente", "proponente@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.proposer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("aprobador", "aprobador@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        self.reader = User.objects.create_user("lector", "lector@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.reader, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR,
        )

    def test_create_proposed(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        self.assertEqual(mapping.estado, MaterialFactorMapping.Estado.PROPUESTO)
        self.assertEqual(mapping.decisiones.count(), 1)
        self.assertEqual(mapping.decisiones.get().decision, "propuesto")

    def test_approve(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        approved = approve_material_mapping(mapping.pk, self.org, self.approver, "ok")
        self.assertEqual(approved.estado, MaterialFactorMapping.Estado.APROBADO)
        self.assertEqual(
            list(approved.decisiones.order_by("pk").values_list("decision", flat=True)),
            ["propuesto", "aprobado"],
        )

    def test_reject(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        rejected = reject_material_mapping(mapping.pk, self.org, self.approver, "no aplica")
        self.assertEqual(rejected.estado, MaterialFactorMapping.Estado.RECHAZADO)

    def test_unauthorized_approval(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        with self.assertRaises(PermissionDenied):
            approve_material_mapping(mapping.pk, self.org, self.reader)

    def test_tenant_factor_allowed(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        self.assertEqual(mapping.factor, self.tenant_factor)

    def test_global_factor_allowed(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.global_factor, date(2026, 1, 1), None, self.proposer,
        )
        self.assertEqual(mapping.factor, self.global_factor)

    def test_other_tenant_factor_rejected(self):
        with self.assertRaises(ValidationError):
            propose_material_mapping(
                self.org, self.material, self.other_org_factor, date(2026, 1, 1), None, self.proposer,
            )

    def test_history_immutable(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        approve_material_mapping(mapping.pk, self.org, self.approver)
        decision = mapping.decisiones.get(decision="aprobado")
        token = mapping_write.set(True)
        try:
            with self.assertRaises(ValidationError):
                decision.nota = "editado"
                decision.save()
            with self.assertRaises(ValidationError):
                decision.delete()
        finally:
            mapping_write.reset(token)

    def test_approved_mapping_is_immutable_outside_transitions(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        approve_material_mapping(mapping.pk, self.org, self.approver)
        mapping.refresh_from_db()
        token = mapping_write.set(True)
        try:
            mapping.vigencia_desde = date(2025, 1, 1)
            with self.assertRaises(ValidationError):
                mapping.save()
        finally:
            mapping_write.reset(token)

    def test_overlapping_validity_rejected(self):
        first = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), date(2026, 6, 30), self.proposer,
        )
        approve_material_mapping(first.pk, self.org, self.approver)
        second = propose_material_mapping(
            self.org, self.material, self.global_factor, date(2026, 6, 1), None, self.proposer,
        )
        with self.assertRaises(ValidationError):
            approve_material_mapping(second.pk, self.org, self.approver)

    def test_non_overlapping_sequential_validity_allowed(self):
        first = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), date(2026, 6, 30), self.proposer,
        )
        approve_material_mapping(first.pk, self.org, self.approver)
        second = propose_material_mapping(
            self.org, self.material, self.global_factor, date(2026, 7, 1), None, self.proposer,
        )
        approved_second = approve_material_mapping(second.pk, self.org, self.approver)
        self.assertEqual(approved_second.estado, MaterialFactorMapping.Estado.APROBADO)

    def test_revoke_requires_approved_state(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        with self.assertRaises(ValidationError):
            revoke_material_mapping(mapping.pk, self.org, self.approver)

    def test_revoke_and_supersede(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        approve_material_mapping(mapping.pk, self.org, self.approver)
        revoked = revoke_material_mapping(mapping.pk, self.org, self.approver, "ya no aplica")
        self.assertEqual(revoked.estado, MaterialFactorMapping.Estado.REVOCADO)

        mapping2 = propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        approve_material_mapping(mapping2.pk, self.org, self.approver)
        replacement = propose_material_mapping(
            self.org, self.material, self.global_factor, date(2027, 1, 1), None, self.proposer,
        )
        superseded = revoke_material_mapping(
            mapping2.pk, self.org, self.approver, replacement=replacement,
        )
        self.assertEqual(superseded.estado, MaterialFactorMapping.Estado.REEMPLAZADO)
        self.assertEqual(superseded.reemplazado_por, replacement)
        approved_replacement = approve_material_mapping(replacement.pk, self.org, self.approver)
        self.assertEqual(approved_replacement.estado, MaterialFactorMapping.Estado.APROBADO)

    def test_duplicate_proposal_rejected(self):
        propose_material_mapping(
            self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
        )
        with self.assertRaises(ValidationError):
            propose_material_mapping(
                self.org, self.material, self.tenant_factor, date(2026, 1, 1), None, self.proposer,
            )


class MaterialFactorMappingConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Mapeo concurrencia")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-CONC", nombre="Concreto", categoria="concreto", unidad_base="kg",
        )
        self.factor_a = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-conc-a", nombre="A", categoria="materiales",
            unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.factor_b = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-conc-b", nombre="B", categoria="materiales",
            unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.user = User.objects.create_superuser(
            "concurrencia-admin", "concurrencia-admin@example.com", "password"
        )

    def concurrent(self, actions):
        barrier = Barrier(len(actions))
        results, errors = [], []

        def worker(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(action())
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker, args=(action,)) for action in actions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return results, errors

    def test_concurrent_approval_of_overlapping_mappings_leaves_one_authority(self):
        first = propose_material_mapping(
            self.org, self.material, self.factor_a, date(2026, 1, 1), None, self.user,
        )
        second = propose_material_mapping(
            self.org, self.material, self.factor_b, date(2026, 1, 1), None, self.user,
        )
        results, errors = self.concurrent(
            [
                lambda: approve_material_mapping(first.pk, self.org, self.user).pk,
                lambda: approve_material_mapping(second.pk, self.org, self.user).pk,
            ]
        )
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        self.assertIsInstance(errors[0], (ValidationError, IntegrityError))
        approved_count = MaterialFactorMapping.objects.filter(
            organizacion=self.org, material=self.material,
            estado=MaterialFactorMapping.Estado.APROBADO,
        ).count()
        self.assertEqual(approved_count, 1)

    def test_concurrent_duplicate_proposal_leaves_one_row(self):
        def propose():
            return propose_material_mapping(
                self.org, self.material, self.factor_a, date(2026, 1, 1), None, self.user,
            ).pk

        results, errors = self.concurrent([propose, propose])
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        self.assertEqual(
            MaterialFactorMapping.objects.filter(
                material=self.material, factor=self.factor_a, vigencia_desde=date(2026, 1, 1),
            ).count(),
            1,
        )

    def test_concurrent_revocation_and_supersession(self):
        mapping = propose_material_mapping(
            self.org, self.material, self.factor_a, date(2026, 1, 1), None, self.user,
        )
        approve_material_mapping(mapping.pk, self.org, self.user)
        replacement = propose_material_mapping(
            self.org, self.material, self.factor_b, date(2027, 1, 1), None, self.user,
        )

        results, errors = self.concurrent(
            [
                lambda: revoke_material_mapping(mapping.pk, self.org, self.user, "a").estado,
                lambda: revoke_material_mapping(
                    mapping.pk, self.org, self.user, "b", replacement=replacement
                ).estado,
            ]
        )
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        mapping.refresh_from_db()
        self.assertIn(mapping.estado, {"revocado", "reemplazado"})
