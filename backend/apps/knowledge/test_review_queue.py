"""SOURCE-WATCH-01F — Review Queue & Human Governance tests."""

from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied

from apps.knowledge import test_okobaudat_detail as detail_tests

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState, SourceWatchReviewItem
from .review_queue import acknowledge_review_item, open_review_item, resolve_review_item
from .services import sync_environmental_source

User = get_user_model()


def _impact(external_id="one", content_hash="hash-1", domain="generic", classification="changed_unknown_impact", affected_objects=None):
    return {
        "external_id": external_id,
        "domain": domain,
        "classification": classification,
        "severity": "medium",
        "impact_level": "unknown_impact",
        "reasons": ["sin_regla_de_dominio"],
        "affected_objects": affected_objects or [],
        "provenance": {"content_hash": content_hash},
    }


class ReviewQueueLifecycleTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="review-source", nombre="Review", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        self.run = sync_environmental_source(self.source)
        self.admin = User.objects.create_superuser("review-admin", "review-admin@example.com", "password")
        self.plain_user = User.objects.create_user("review-plain", "review-plain@example.com", "password")

    def test_open_review_item(self):
        item, created = open_review_item(self.run, _impact())
        self.assertTrue(created)
        self.assertEqual(item.estado, SourceWatchReviewItem.Estado.OPEN)

    def test_duplicate_open_is_idempotent(self):
        first, created_first = open_review_item(self.run, _impact())
        second, created_second = open_review_item(self.run, _impact())
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SourceWatchReviewItem.objects.count(), 1)

    def test_different_content_hash_opens_new_item(self):
        open_review_item(self.run, _impact(content_hash="hash-1"))
        _, created = open_review_item(self.run, _impact(content_hash="hash-2"))
        self.assertTrue(created)
        self.assertEqual(SourceWatchReviewItem.objects.count(), 2)

    def test_full_lifecycle(self):
        item, _ = open_review_item(self.run, _impact())
        acknowledged = acknowledge_review_item(item.pk, self.admin, "visto")
        self.assertEqual(acknowledged.estado, SourceWatchReviewItem.Estado.ACKNOWLEDGED)
        resolved = resolve_review_item(item.pk, self.admin, "resuelto")
        self.assertEqual(resolved.estado, SourceWatchReviewItem.Estado.RESOLVED)
        self.assertEqual(
            list(resolved.decisiones.order_by("pk").values_list("decision", flat=True)),
            ["acknowledged", "resolved"],
        )

    def test_resolve_without_acknowledge_allowed(self):
        item, _ = open_review_item(self.run, _impact())
        resolved = resolve_review_item(item.pk, self.admin)
        self.assertEqual(resolved.estado, SourceWatchReviewItem.Estado.RESOLVED)

    def test_resolved_item_is_immutable(self):
        item, _ = open_review_item(self.run, _impact())
        resolve_review_item(item.pk, self.admin)
        item.refresh_from_db()
        item.impact_level = "blocked"
        with self.assertRaises(ValidationError):
            item.save()

    def test_decisions_are_immutable(self):
        item, _ = open_review_item(self.run, _impact())
        acknowledge_review_item(item.pk, self.admin)
        decision = item.decisiones.get()
        with self.assertRaises(ValidationError):
            decision.note = "editado"
            decision.save()
        with self.assertRaises(ValidationError):
            decision.delete()

    def test_non_admin_cannot_acknowledge(self):
        item, _ = open_review_item(self.run, _impact())
        with self.assertRaises(PermissionDenied):
            acknowledge_review_item(item.pk, self.plain_user)

    def test_non_admin_cannot_resolve(self):
        item, _ = open_review_item(self.run, _impact())
        with self.assertRaises(PermissionDenied):
            resolve_review_item(item.pk, self.plain_user)

    def test_direct_queryset_mutation_blocked(self):
        item, _ = open_review_item(self.run, _impact())
        with self.assertRaises(ValidationError):
            SourceWatchReviewItem.objects.filter(pk=item.pk).update(estado="resolved")
        with self.assertRaises(ValidationError):
            SourceWatchReviewItem.objects.filter(pk=item.pk).delete()

    def test_resolving_never_mutates_downstream_analytics_objects(self):
        from datetime import date
        from decimal import Decimal

        from apps.analytics.models import MaterialOperacional, Organizacion, UsuarioOrganizacion
        from apps.analytics.services.factor_governance import transition_factor_version
        from apps.analytics.services.material_candidates import (
            build_material_candidate, promote_material_candidate, review_material_candidate,
        )
        from apps.analytics.services.material_factor_mapping import approve_material_mapping, propose_material_mapping
        from apps.analytics.test_material_candidates import material_fixture

        org = Organizacion.objects.create(nombre="Review downstream org")
        UsuarioOrganizacion.objects.create(user=self.admin, organizacion=org, rol=UsuarioOrganizacion.Rol.ADMIN)
        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        review_material_candidate(candidate.pk, self.admin, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.admin)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo="MAT-REVIEW", nombre="M", categoria="materiales", unidad_base="kg",
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.admin)
        mapping = approve_material_mapping(mapping.pk, org, self.admin)
        mapping_estado_before = mapping.estado
        factor_id_before = factor.pk

        item, _ = open_review_item(self.run, _impact(
            domain="okobaudat", affected_objects=[{"type": "MaterialFactorMapping", "id": mapping.pk}],
        ))
        resolve_review_item(item.pk, self.admin)

        mapping.refresh_from_db()
        self.assertEqual(mapping.estado, mapping_estado_before)
        self.assertEqual(factor.pk, factor_id_before)


class ReviewQueueConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="review-conc-source", nombre="Review conc", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        self.run = sync_environmental_source(self.source)
        self.admin = User.objects.create_superuser(
            "review-conc-admin", "review-conc-admin@example.com", "password"
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

    def test_concurrent_duplicate_open_leaves_one_row(self):
        results, errors = self.concurrent([
            lambda: open_review_item(self.run, _impact())[0].pk,
            lambda: open_review_item(self.run, _impact())[0].pk,
        ])
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(SourceWatchReviewItem.objects.count(), 1)

    def test_concurrent_resolve_leaves_one_terminal_state(self):
        item, _ = open_review_item(self.run, _impact())
        results, errors = self.concurrent([
            lambda: resolve_review_item(item.pk, self.admin).estado,
            lambda: acknowledge_review_item(item.pk, self.admin).estado,
        ])
        item.refresh_from_db()
        # Whichever action wins the race, the final state converges to
        # RESOLVED: either resolve wins outright, or acknowledge wins first
        # and the subsequent resolve (now valid from ACKNOWLEDGED) succeeds.
        self.assertEqual(item.estado, SourceWatchReviewItem.Estado.RESOLVED)
