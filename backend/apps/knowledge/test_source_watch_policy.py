"""SOURCE-WATCH-01A — Source Registry & Watch Policy Audit tests."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from .connectors.registry import CONNECTOR_REGISTRY
from .models import EnvironmentalSource
from .watch_policy import CONNECTOR_CAPABILITIES, connector_capabilities, describe_watch_policy


class WatchPolicyTests(TestCase):
    def _source(self, **overrides):
        kwargs = dict(
            codigo="watch-test", nombre="Watch Test", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=24,
        )
        kwargs.update(overrides)
        return EnvironmentalSource(**kwargs)

    def test_every_registered_connector_has_known_capabilities(self):
        for connector_key in CONNECTOR_REGISTRY:
            self.assertIsNotNone(connector_capabilities(connector_key))
        for connector_key in CONNECTOR_CAPABILITIES:
            self.assertIn(connector_key, CONNECTOR_REGISTRY)

    def test_unregistered_connector_returns_none_capabilities(self):
        self.assertIsNone(connector_capabilities("not-a-real-connector"))

    def test_describe_watch_policy_active_source(self):
        source = EnvironmentalSource.objects.create(
            codigo="watch-active", nombre="Activo", organismo="Tests",
            connector_key="retc_ckan", tipo_acceso="CKAN", nivel_autoridad="test",
            stale_after_hours=48, cadencia_horas=24,
        )
        policy = describe_watch_policy(source)
        self.assertTrue(policy["safe_to_auto_watch"])
        self.assertTrue(policy["capabilities"]["authoritative_full_snapshot"])
        self.assertFalse(policy["capabilities"]["supports_cursor"])

    def test_inactive_source_is_never_safe_to_auto_watch(self):
        source = EnvironmentalSource.objects.create(
            codigo="watch-inactive", nombre="Inactivo", organismo="Tests",
            connector_key="retc_ckan", tipo_acceso="CKAN", nivel_autoridad="test",
            activa=False,
        )
        policy = describe_watch_policy(source)
        self.assertFalse(policy["safe_to_auto_watch"])

    def test_source_with_poll_disabled_is_not_safe_to_auto_watch(self):
        source = EnvironmentalSource.objects.create(
            codigo="watch-nopoll", nombre="Sin poll", organismo="Tests",
            connector_key="retc_ckan", tipo_acceso="CKAN", nivel_autoridad="test",
            permite_poll_automatico=False,
        )
        policy = describe_watch_policy(source)
        self.assertFalse(policy["safe_to_auto_watch"])

    def test_unregistered_connector_fails_closed_never_auto_watched(self):
        source = self._source(connector_key="unknown-connector")
        policy = describe_watch_policy(source)
        self.assertFalse(policy["connector_registered"])
        self.assertFalse(policy["safe_to_auto_watch"])

    def test_clean_rejects_unregistered_connector(self):
        source = self._source(connector_key="unknown-connector")
        with self.assertRaises(ValidationError):
            source.clean()

    def test_clean_rejects_zero_stale_after_hours(self):
        source = self._source(stale_after_hours=0)
        with self.assertRaises(ValidationError):
            source.clean()

    def test_clean_rejects_negative_cadencia_horas(self):
        source = self._source(cadencia_horas=0)
        with self.assertRaises(ValidationError):
            source.clean()

    def test_clean_accepts_valid_policy(self):
        source = self._source(cadencia_horas=12)
        source.clean()  # must not raise

    def test_existing_registered_sources_regression_unaffected(self):
        # Creating a source the same way pre-existing tests already do
        # (without the two new fields) must still work with sane defaults.
        source = EnvironmentalSource.objects.create(
            codigo="watch-legacy-shape", nombre="Legacy", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        self.assertIsNone(source.cadencia_horas)
        self.assertTrue(source.permite_poll_automatico)
