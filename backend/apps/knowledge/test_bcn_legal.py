from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .bcn_sync import sync_bcn_legal_norms
from .connectors.bcn import BcnLeyChileSparqlConnector
from .models import (
    BcnLegalNormFact,
    BcnLegalNormSubscription,
    EnvironmentalSource,
    ExternalSnapshot,
)

ROOT = "http://datos.bcn.cl/recurso/cl/ley/ministerio/1994-03-09/19300"


def binding(**values):
    return {key: {"value": value} for key, value in values.items()}


ROOT_ROWS = [
    binding(
        norm=ROOT,
        title="APRUEBA LEY SOBRE BASES GENERALES DEL MEDIO AMBIENTE",
        type="http://datos.bcn.cl/recurso/cl/norma/tipo#ley",
        issuer="http://datos.bcn.cl/recurso/cl/organismo/ministerio",
        publish="1994-03-09",
        promulgation="1994-03-01",
    )
]
VERSIONS = [
    binding(version=ROOT + "/es@1994-03-09", versionDate="1994-03-09", latest="0"),
    binding(version=ROOT + "/es@2024-01-01", versionDate="2024-01-01", latest="1"),
]
RELATIONS = [
    binding(
        predicate="http://datos.bcn.cl/ontologies/bcn-norms#isModifiedBy",
        target="http://datos.bcn.cl/recurso/cl/ley/x/20417",
    ),
    binding(
        predicate="http://datos.bcn.cl/ontologies/bcn-norms#isModifiedBy",
        target="http://datos.bcn.cl/recurso/cl/ley/x/20417",
    ),
]


class BcnLegalKnowledgeTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.get(codigo="bcn-leychile")
        BcnLegalNormSubscription.objects.filter(source=self.source).exclude(
            number="19300"
        ).delete()

    @patch.object(BcnLeyChileSparqlConnector, "_query")
    def test_sync_materializes_current_fact_and_is_idempotent(self, query):
        query.side_effect = [
            ROOT_ROWS,
            VERSIONS,
            RELATIONS,
            ROOT_ROWS,
            VERSIONS,
            RELATIONS,
        ]
        first = sync_bcn_legal_norms()
        second = sync_bcn_legal_norms()
        fact = BcnLegalNormFact.objects.get()
        self.assertEqual(
            (first.created, second.unchanged, ExternalSnapshot.objects.count()),
            (1, 1, 1),
        )
        self.assertEqual(
            (
                fact.number,
                fact.versions.count(),
                fact.versions.filter(is_latest=True).count(),
                fact.relations.count(),
            ),
            ("19300", 2, 1, 1),
        )

    @patch.object(BcnLeyChileSparqlConnector, "_query")
    def test_upstream_change_preserves_previous_snapshot_and_fact(self, query):
        changed = [{**ROOT_ROWS[0], "title": {"value": "TÍTULO MODIFICADO"}}]
        query.side_effect = [
            ROOT_ROWS,
            VERSIONS,
            RELATIONS,
            changed,
            VERSIONS,
            RELATIONS,
        ]
        sync_bcn_legal_norms()
        old = BcnLegalNormFact.objects.get()
        sync_bcn_legal_norms()
        old.refresh_from_db()
        self.assertEqual(ExternalSnapshot.objects.count(), 2)
        self.assertEqual(BcnLegalNormFact.objects.count(), 2)
        self.assertNotEqual(
            self.source.records.get().current_snapshot_id, old.snapshot_id
        )

    @patch.object(BcnLeyChileSparqlConnector, "_query", return_value=[])
    def test_missing_or_ambiguous_norm_fails_closed(self, query):
        self.assertEqual(sync_bcn_legal_norms().estado, "error")

    @patch.object(BcnLeyChileSparqlConnector, "_query")
    def test_ambiguous_norm_and_multiple_latest_fail_closed(self, query):
        query.return_value = ROOT_ROWS + [
            {**ROOT_ROWS[0], "norm": {"value": ROOT + "-duplicate"}}
        ]
        self.assertEqual(sync_bcn_legal_norms().estado, "error")
        query.side_effect = [
            ROOT_ROWS,
            VERSIONS
            + [
                binding(
                    version=ROOT + "/es@2025-01-01",
                    versionDate="2025-01-01",
                    latest="1",
                )
            ],
        ]
        self.assertEqual(sync_bcn_legal_norms().estado, "error")

    @patch.object(
        BcnLeyChileSparqlConnector,
        "_query",
        side_effect=TimeoutError("BCN no disponible"),
    )
    def test_endpoint_failure_preserves_previous_current_snapshot(self, query):
        with patch.object(
            BcnLeyChileSparqlConnector,
            "_query",
            side_effect=[ROOT_ROWS, VERSIONS, RELATIONS],
        ):
            sync_bcn_legal_norms()
        current = self.source.records.get().current_snapshot_id
        self.assertEqual(sync_bcn_legal_norms().estado, "error")
        self.assertEqual(self.source.records.get().current_snapshot_id, current)

    def test_managed_bootstrap_and_authenticated_current_api(self):
        self.assertEqual(
            (
                self.source.connector_key,
                self.source.tipo_acceso,
                self.source.stale_after_hours,
            ),
            ("bcn_leychile_sparql", "SPARQL", 48),
        )
        self.assertEqual(
            BcnLegalNormSubscription.objects.filter(source=self.source).count(), 1
        )
        client = APIClient()
        self.assertEqual(client.get("/api/knowledge/bcn/norms/").status_code, 403)
        user = get_user_model().objects.create_user("legal-reader", password="x")
        client.force_authenticate(user)
        self.assertEqual(client.get("/api/knowledge/bcn/norms/").status_code, 200)
