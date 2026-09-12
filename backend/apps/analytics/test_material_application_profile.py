from datetime import date
from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import Obra, Organizacion, UsuarioOrganizacion
from .models.material_application_profile import (
    MaterialApplicationProfile,
    application_profile_write,
)
from .services.material_application_profile import (
    approve_profile,
    create_profile,
    create_revision,
    reject_profile,
    retire_profile,
    update_draft,
)
from .services.material_application_requirements import (
    validate_requirement,
    validate_requirements,
)

User = get_user_model()


class RequirementValidationTests(TestCase):
    def test_numeric_eq_valid(self):
        req = validate_requirement({"key": "densidad", "type": "numeric", "operator": "eq", "value": "5", "unit": "kg"})
        self.assertEqual(req["value"], "5")
        self.assertEqual(req["unit"], "kg")

    def test_numeric_gte_valid(self):
        req = validate_requirement({"key": "resistencia", "type": "numeric", "operator": "gte", "value": 30})
        self.assertEqual(req["operator"], "gte")

    def test_numeric_lte_valid(self):
        req = validate_requirement({"key": "espesor", "type": "numeric", "operator": "lte", "value": 10})
        self.assertEqual(req["operator"], "lte")

    def test_numeric_range_valid(self):
        req = validate_requirement(
            {"key": "espesor", "type": "numeric", "operator": "range", "min": 5, "max": 10, "unit": "kg"}
        )
        self.assertEqual(req["min"], "5")
        self.assertEqual(req["max"], "10")

    def test_numeric_range_min_gte_max_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement({"key": "espesor", "type": "numeric", "operator": "range", "min": 10, "max": 5})

    def test_categorical_equals_valid(self):
        req = validate_requirement({"key": "clase", "type": "categorical", "operator": "equals", "value": "A"})
        self.assertEqual(req["value"], "A")

    def test_categorical_one_of_valid(self):
        req = validate_requirement(
            {"key": "clase", "type": "categorical", "operator": "one_of", "values": ["A", "B"]}
        )
        self.assertEqual(req["values"], ["A", "B"])

    def test_categorical_one_of_empty_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement({"key": "clase", "type": "categorical", "operator": "one_of", "values": []})

    def test_boolean_valid(self):
        req = validate_requirement({"key": "certificado", "type": "boolean", "operator": "is_true"})
        self.assertEqual(req["operator"], "is_true")

    def test_boolean_value_must_be_bool(self):
        with self.assertRaises(ValidationError):
            validate_requirement(
                {"key": "certificado", "type": "boolean", "operator": "is_true", "value": "si"}
            )

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement({"key": "x", "type": "text", "operator": "eq", "value": "1"})

    def test_invalid_operator_for_type_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement({"key": "clase", "type": "categorical", "operator": "gte", "value": "A"})

    def test_incompatible_unit_in_range_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement(
                {
                    "key": "mixto",
                    "type": "numeric",
                    "operator": "range",
                    "min": 1,
                    "max": 2,
                    "min_unit": "kg",
                    "max_unit": "L",
                }
            )

    def test_compatible_unit_in_range_allowed(self):
        req = validate_requirement(
            {
                "key": "mixto",
                "type": "numeric",
                "operator": "range",
                "min": 1,
                "max": 2000,
                "min_unit": "t",
                "max_unit": "kg",
            }
        )
        self.assertEqual(req["min_unit"], "t")
        self.assertEqual(req["max_unit"], "kg")

    def test_missing_key_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirement({"type": "numeric", "operator": "eq", "value": 1})

    def test_no_arbitrary_python_fields_ignored_safely(self):
        # Extra/unsupported keys never get executed; only the typed shape is read.
        req = validate_requirement(
            {"key": "x", "type": "numeric", "operator": "eq", "value": 1, "eval": "os.system('rm -rf /')"}
        )
        self.assertNotIn("eval", req)

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValidationError):
            validate_requirements(
                [
                    {"key": "a", "type": "boolean", "operator": "is_true"},
                    {"key": "a", "type": "boolean", "operator": "is_false"},
                ]
            )

    def test_requirements_must_be_list(self):
        with self.assertRaises(ValidationError):
            validate_requirements({"key": "a"})

    def test_none_requirements_normalizes_to_empty(self):
        self.assertEqual(validate_requirements(None), [])


class MaterialApplicationProfileLifecycleTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Perfil aplicacion")
        self.other_org = Organizacion.objects.create(nombre="Otro tenant perfil")
        self.work = Obra.objects.create(
            organizacion=self.org, nombre="Obra A", codigo_obra="OBRA-A", fecha_inicio=date(2026, 1, 1)
        )
        self.manager = User.objects.create_user("gestor", "gestor@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.manager, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ANALISTA,
        )
        self.approver = User.objects.create_user("aprobador", "aprobador@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.approver, organizacion=self.org, rol=UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL,
        )
        self.reader = User.objects.create_user("lector", "lector@example.com", "password")
        UsuarioOrganizacion.objects.create(
            user=self.reader, organizacion=self.org, rol=UsuarioOrganizacion.Rol.LECTOR,
        )
        self.requisitos = [
            {"key": "resistencia", "type": "numeric", "operator": "gte", "value": 30, "unit": "kg"},
            {"key": "clase", "type": "categorical", "operator": "equals", "value": "estructural"},
        ]

    def _create(self, **overrides):
        kwargs = dict(
            organization=self.org,
            user=self.manager,
            codigo="MURO-EXT",
            nombre="Muro exterior",
            cantidad_unidad_funcional=Decimal("1"),
            unidad_funcional="m2",
            requisitos=self.requisitos,
        )
        kwargs.update(overrides)
        return create_profile(**kwargs)

    def test_create_draft(self):
        profile = self._create()
        self.assertEqual(profile.estado, MaterialApplicationProfile.Estado.BORRADOR)
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.decisiones.count(), 1)

    def test_create_requires_permission(self):
        with self.assertRaises(PermissionDenied):
            create_profile(
                self.org, self.reader, "X", "X", Decimal("1"), "m2",
            )

    def test_create_with_work_scoped(self):
        profile = self._create(obra=self.work)
        self.assertEqual(profile.obra_id, self.work.id)

    def test_create_with_foreign_work_rejected(self):
        other_work = Obra.objects.create(
            organizacion=self.other_org, nombre="Obra B", codigo_obra="OBRA-B", fecha_inicio=date(2026, 1, 1)
        )
        with self.assertRaises(ValidationError):
            self._create(obra=other_work)

    def test_approve(self):
        profile = self._create()
        approved = approve_profile(profile.pk, self.org, self.approver)
        self.assertEqual(approved.estado, MaterialApplicationProfile.Estado.APROBADO)
        self.assertEqual(approved.reviewed_by, self.approver)
        self.assertIsNotNone(approved.reviewed_at)

    def test_approve_requires_permission(self):
        profile = self._create()
        with self.assertRaises(PermissionDenied):
            approve_profile(profile.pk, self.org, self.manager)

    def test_reject(self):
        profile = self._create()
        rejected = reject_profile(profile.pk, self.org, self.approver, "no aplica")
        self.assertEqual(rejected.estado, MaterialApplicationProfile.Estado.RECHAZADO)

    def test_retire_requires_approved(self):
        profile = self._create()
        with self.assertRaises(ValidationError):
            retire_profile(profile.pk, self.org, self.approver)

    def test_retire_after_approval(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        retired = retire_profile(profile.pk, self.org, self.approver, "obsoleto")
        self.assertEqual(retired.estado, MaterialApplicationProfile.Estado.RETIRADO)

    def test_approved_profile_is_immutable(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        profile.refresh_from_db()
        token = application_profile_write.set(True)
        try:
            profile.nombre = "Otro nombre"
            with self.assertRaises(ValidationError):
                profile.save()
        finally:
            application_profile_write.reset(token)

    def test_update_draft_allowed(self):
        profile = self._create()
        updated = update_draft(profile.pk, self.org, self.manager, nombre="Muro exterior v2")
        self.assertEqual(updated.nombre, "Muro exterior v2")

    def test_update_after_approval_rejected(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        with self.assertRaises(ValidationError):
            update_draft(profile.pk, self.org, self.manager, nombre="X")

    def test_history_immutable(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        decision = profile.decisiones.get(decision="aprobado")
        token = application_profile_write.set(True)
        try:
            with self.assertRaises(ValidationError):
                decision.nota = "editado"
                decision.save()
            with self.assertRaises(ValidationError):
                decision.delete()
        finally:
            application_profile_write.reset(token)

    def test_version_history_via_revision(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        revision = create_revision(profile.pk, self.org, self.manager)
        self.assertEqual(revision.version, 2)
        self.assertEqual(revision.reemplaza_a_id, profile.pk)
        self.assertEqual(revision.estado, MaterialApplicationProfile.Estado.BORRADOR)

    def test_revision_approval_supersedes_predecessor(self):
        profile = self._create()
        approve_profile(profile.pk, self.org, self.approver)
        revision = create_revision(profile.pk, self.org, self.manager)
        approved_revision = approve_profile(revision.pk, self.org, self.approver)
        self.assertEqual(approved_revision.estado, MaterialApplicationProfile.Estado.APROBADO)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, MaterialApplicationProfile.Estado.REEMPLAZADO)

    def test_revision_requires_approved_source(self):
        profile = self._create()
        with self.assertRaises(ValidationError):
            create_revision(profile.pk, self.org, self.manager)

    def test_tenant_isolation_on_lookup(self):
        profile = self._create()
        self.assertEqual(
            MaterialApplicationProfile.objects.filter(
                organizacion=self.other_org, pk=profile.pk
            ).count(),
            0,
        )

    def test_duplicate_identity_rejected_by_db(self):
        self._create()
        # A second, independent v1 draft with the same (org, obra, codigo)
        # identity conflicts with the existing lineage at creation time.
        with self.assertRaises(ValidationError):
            create_profile(
                self.org, self.manager, "MURO-EXT", "Muro exterior dup",
                Decimal("1"), "m2", requisitos=self.requisitos,
            )


class MaterialApplicationProfileConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Perfil concurrencia")
        self.user = User.objects.create_superuser(
            "concurrencia-perfil-admin", "concurrencia-perfil-admin@example.com", "password"
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

    def test_concurrent_revision_creation_from_same_predecessor_leaves_one_row(self):
        source = create_profile(
            self.org, self.user, "MURO-CONC", "A", Decimal("1"), "m2",
        )
        approve_profile(source.pk, self.org, self.user)
        results, errors = self.concurrent(
            [
                lambda: create_revision(source.pk, self.org, self.user).pk,
                lambda: create_revision(source.pk, self.org, self.user).pk,
            ]
        )
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        self.assertIsInstance(errors[0], (ValidationError, IntegrityError))
        revision_count = MaterialApplicationProfile.objects.filter(
            organizacion=self.org, codigo="MURO-CONC", version=2,
        ).count()
        self.assertEqual(revision_count, 1)

    def test_concurrent_approval_of_revision_and_retirement_of_predecessor(self):
        source = create_profile(
            self.org, self.user, "MURO-CONC2", "A", Decimal("1"), "m2",
        )
        approve_profile(source.pk, self.org, self.user)
        revision = create_revision(source.pk, self.org, self.user)
        results, errors = self.concurrent(
            [
                lambda: approve_profile(revision.pk, self.org, self.user).estado,
                lambda: retire_profile(source.pk, self.org, self.user).estado,
            ]
        )
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        source.refresh_from_db()
        self.assertIn(
            source.estado,
            {MaterialApplicationProfile.Estado.RETIRADO, MaterialApplicationProfile.Estado.REEMPLAZADO},
        )
