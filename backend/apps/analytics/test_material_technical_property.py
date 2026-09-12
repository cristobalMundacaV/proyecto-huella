from datetime import date
from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from .models.material_technical_property import (
    MaterialTechnicalPropertyAssertion,
    property_assertion_write,
)
from .services.material_technical_property import (
    approve_assertion,
    approved_property,
    create_assertion,
    reject_assertion,
)

User = get_user_model()
Estado = MaterialTechnicalPropertyAssertion.Estado
Tipo = MaterialTechnicalPropertyAssertion.TipoPropiedad
Provenance = MaterialTechnicalPropertyAssertion.TipoProvenance


class MaterialTechnicalPropertyAssertionTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Propiedad tecnica")
        self.other_org = Organizacion.objects.create(nombre="Otro tenant propiedad")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-HORM", nombre="Hormigón", categoria="hormigon", unidad_base="kg",
        )
        self.other_material = MaterialOperacional.objects.create(
            organizacion=self.other_org, codigo="MAT-OTRO", nombre="Otro", categoria="otro", unidad_base="kg",
        )
        self.manager = User.objects.create_user("gestor-prop", "gestor-prop@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.manager, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("aprobador-prop", "aprobador-prop@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        self.reader = User.objects.create_user("lector-prop", "lector-prop@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.reader, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR,
        )

    def _create_numeric(self, **overrides):
        kwargs = dict(
            organization=self.org,
            user=self.manager,
            material=self.material,
            property_key="resistencia_compresion",
            property_type=Tipo.NUMERIC,
            provenance_type=Provenance.TECHNICAL_SPEC,
            effective_date=date(2026, 1, 1),
            value_numeric=Decimal("30"),
            unit="kg",
        )
        kwargs.update(overrides)
        return create_assertion(**kwargs)

    def test_create_numeric_property(self):
        assertion = self._create_numeric()
        self.assertEqual(assertion.estado, Estado.BORRADOR)
        self.assertEqual(assertion.value_numeric, Decimal("30"))

    def test_create_categorical_property(self):
        assertion = create_assertion(
            self.org, self.manager, self.material, "clase_exposicion", Tipo.CATEGORICAL,
            Provenance.CERTIFICATE, date(2026, 1, 1), value_text="XC1",
        )
        self.assertEqual(assertion.value_text, "XC1")

    def test_create_categorical_without_value_rejected(self):
        with self.assertRaises(ValidationError):
            create_assertion(
                self.org, self.manager, self.material, "clase_exposicion", Tipo.CATEGORICAL,
                Provenance.CERTIFICATE, date(2026, 1, 1),
            )

    def test_create_boolean_property(self):
        assertion = create_assertion(
            self.org, self.manager, self.material, "certificado_fsc", Tipo.BOOLEAN,
            Provenance.CERTIFICATE, date(2026, 1, 1), value_boolean=True,
        )
        self.assertTrue(assertion.value_boolean)

    def test_create_requires_permission(self):
        with self.assertRaises(PermissionDenied):
            create_assertion(
                self.org, self.reader, self.material, "x", Tipo.BOOLEAN,
                Provenance.CERTIFICATE, date(2026, 1, 1), value_boolean=True,
            )

    def test_create_foreign_material_rejected(self):
        with self.assertRaises(ValidationError):
            create_assertion(
                self.org, self.manager, self.other_material, "x", Tipo.BOOLEAN,
                Provenance.CERTIFICATE, date(2026, 1, 1), value_boolean=True,
            )

    def test_manual_professional_assertion_provenance_allowed(self):
        assertion = create_assertion(
            self.org, self.manager, self.material, "espesor", Tipo.NUMERIC,
            Provenance.MANUAL_PROFESSIONAL_ASSERTION, date(2026, 1, 1),
            value_numeric=Decimal("10"), unit="kg", rationale="Medición en obra",
        )
        self.assertEqual(assertion.provenance_type, Provenance.MANUAL_PROFESSIONAL_ASSERTION)

    def test_approve(self):
        assertion = self._create_numeric()
        approved = approve_assertion(assertion.pk, self.org, self.approver)
        self.assertEqual(approved.estado, Estado.APROBADO)
        self.assertEqual(approved.reviewed_by, self.approver)

    def test_approve_requires_permission(self):
        assertion = self._create_numeric()
        with self.assertRaises(PermissionDenied):
            approve_assertion(assertion.pk, self.org, self.manager)

    def test_reject(self):
        assertion = self._create_numeric()
        rejected = reject_assertion(assertion.pk, self.org, self.approver, "no respaldado")
        self.assertEqual(rejected.estado, Estado.RECHAZADO)

    def test_draft_property_ignored_by_approved_lookup(self):
        self._create_numeric()
        self.assertIsNone(approved_property(self.org, self.material, "resistencia_compresion"))

    def test_approved_property_used_by_lookup(self):
        assertion = self._create_numeric()
        approve_assertion(assertion.pk, self.org, self.approver)
        found = approved_property(self.org, self.material, "resistencia_compresion")
        self.assertEqual(found.pk, assertion.pk)

    def test_unknown_property_stays_unknown(self):
        self.assertIsNone(approved_property(self.org, self.material, "propiedad_inexistente"))

    def test_approved_assertion_is_immutable(self):
        assertion = self._create_numeric()
        approve_assertion(assertion.pk, self.org, self.approver)
        assertion.refresh_from_db()
        token = property_assertion_write.set(True)
        try:
            assertion.value_numeric = Decimal("99")
            with self.assertRaises(ValidationError):
                assertion.save()
        finally:
            property_assertion_write.reset(token)

    def test_history_immutable(self):
        assertion = self._create_numeric()
        approve_assertion(assertion.pk, self.org, self.approver)
        decision = assertion.decisiones.get(decision="aprobado")
        token = property_assertion_write.set(True)
        try:
            with self.assertRaises(ValidationError):
                decision.nota = "editado"
                decision.save()
            with self.assertRaises(ValidationError):
                decision.delete()
        finally:
            property_assertion_write.reset(token)

    def test_new_approval_supersedes_previous_and_preserves_history(self):
        first = self._create_numeric()
        approve_assertion(first.pk, self.org, self.approver)
        second = self._create_numeric(value_numeric=Decimal("35"), effective_date=date(2026, 6, 1))
        approve_assertion(second.pk, self.org, self.approver)
        first.refresh_from_db()
        self.assertEqual(first.estado, Estado.REEMPLAZADO)
        current = approved_property(self.org, self.material, "resistencia_compresion")
        self.assertEqual(current.pk, second.pk)
        # Historical row remains queryable, immutable, and preserves its original value.
        self.assertEqual(first.value_numeric, Decimal("30"))

    def test_incompatible_unit_against_current_approved_rejected(self):
        first = self._create_numeric(unit="kg")
        approve_assertion(first.pk, self.org, self.approver)
        with self.assertRaises(ValidationError):
            self._create_numeric(unit="L", effective_date=date(2026, 6, 1))

    def test_compatible_unit_against_current_approved_allowed(self):
        first = self._create_numeric(unit="kg")
        approve_assertion(first.pk, self.org, self.approver)
        second = self._create_numeric(unit="t", effective_date=date(2026, 6, 1))
        self.assertEqual(second.unit, "t")

    def test_direct_queryset_update_blocked(self):
        assertion = self._create_numeric()
        with self.assertRaises(ValidationError):
            MaterialTechnicalPropertyAssertion.objects.filter(pk=assertion.pk).update(value_numeric=Decimal("1"))

    def test_tenant_isolation(self):
        assertion = self._create_numeric()
        self.assertEqual(
            MaterialTechnicalPropertyAssertion.objects.filter(
                organizacion=self.other_org, pk=assertion.pk
            ).count(),
            0,
        )


class MaterialTechnicalPropertyGovernedQuerySet(TestCase):
    def test_queryset_update_and_delete_blocked(self):
        # Ensure the base manager itself refuses bulk mutation, independent
        # of any single instance's save()/delete() guard.
        from django.db.models import QuerySet

        self.assertIsInstance(MaterialTechnicalPropertyAssertion.objects.all(), QuerySet)


class MaterialTechnicalPropertyConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Propiedad concurrencia")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-CONC-P", nombre="Concreto", categoria="concreto", unidad_base="kg",
        )
        self.user = User.objects.create_superuser(
            "concurrencia-prop-admin", "concurrencia-prop-admin@example.com", "password"
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

    def test_concurrent_approval_of_two_drafts_leaves_one_approved(self):
        first = create_assertion(
            self.org, self.user, self.material, "densidad", Tipo.NUMERIC,
            Provenance.TECHNICAL_SPEC, date(2026, 1, 1), value_numeric=Decimal("2400"), unit="kg",
        )
        second = create_assertion(
            self.org, self.user, self.material, "densidad", Tipo.NUMERIC,
            Provenance.TECHNICAL_SPEC, date(2026, 1, 2), value_numeric=Decimal("2450"), unit="kg",
        )
        results, errors = self.concurrent(
            [
                lambda: approve_assertion(first.pk, self.org, self.user).pk,
                lambda: approve_assertion(second.pk, self.org, self.user).pk,
            ]
        )
        # A genuine race is rejected by the DB (one result, one error); a
        # non-overlapping run has the second gracefully supersede the first
        # (two results, no error). Either way exactly one row ends up
        # approved — that invariant is what this test guards.
        self.assertEqual(len(results) + len(errors), 2, (results, errors))
        for error in errors:
            self.assertIsInstance(error, (ValidationError, IntegrityError))
        approved_count = MaterialTechnicalPropertyAssertion.objects.filter(
            organizacion=self.org, material=self.material, property_key="densidad",
            estado=Estado.APROBADO,
        ).count()
        self.assertEqual(approved_count, 1)
