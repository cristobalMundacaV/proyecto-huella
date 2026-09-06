from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .bcn_sync import sync_bcn_legal_norms
from .connectors.bcn import BcnLeyChileSparqlConnector
from .connectors.base import ConnectorBatch, ConnectorRecord
from .models import (
    BcnLegalNormFact,
    BcnLegalNormSubscription,
    EnvironmentalSource,
    ExternalSnapshot,
    SourceState,
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


def normalized_payload(uri, number, title):
    return {
        "norm_uri": uri,
        "identifier": "",
        "number": number,
        "title": title,
        "norm_type_uri": "http://datos.bcn.cl/recurso/cl/norma/tipo#ley",
        "norm_type_name": "Ley",
        "issuer_uri": "",
        "issuer_name": "",
        "publish_date": "1994-03-09",
        "promulgation_date": "1994-03-01",
        "latest_version_uri": uri + "/es@2024-01-01",
        "latest_version_date": "2024-01-01",
        "scope_tags": [],
        "versions": [
            {
                "version_uri": uri + "/es@2024-01-01",
                "version_date": "2024-01-01",
                "is_latest": True,
                "xml_document_url": "",
                "html_document_url": "",
            }
        ],
        "relations": [],
    }


def connector_record(uri, number, title):
    return ConnectorRecord(
        external_id=uri,
        kind="bcn_legal_norm",
        source_url=uri,
        canonical_key=f"LEY:{number}",
        title=title,
        payload=normalized_payload(uri, number, title),
    )


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

    @patch.object(BcnLeyChileSparqlConnector, "_query")
    def test_failed_materialization_preserves_observation_but_restores_valid_current(
        self, query
    ):
        changed = [{**ROOT_ROWS[0], "title": {"value": "CAMBIO NO MATERIALIZABLE"}}]
        query.side_effect = [
            ROOT_ROWS,
            VERSIONS,
            RELATIONS,
            changed,
            VERSIONS,
            RELATIONS,
            changed,
            VERSIONS,
            RELATIONS,
        ]
        sync_bcn_legal_norms()
        old_fact = BcnLegalNormFact.objects.get()
        old_snapshot_id = old_fact.snapshot_id
        with patch.object(
            BcnLegalNormFact.objects,
            "create",
            side_effect=ValueError("payload normalizado corrupto"),
        ):
            failed = sync_bcn_legal_norms()
        record = self.source.records.get()
        self.source.sync_state.refresh_from_db()
        self.assertEqual(
            (ExternalSnapshot.objects.count(), BcnLegalNormFact.objects.count()), (2, 1)
        )
        self.assertEqual(record.current_snapshot_id, old_snapshot_id)
        self.assertEqual(
            (failed.estado, self.source.sync_state.estado), ("parcial", "parcial")
        )
        self.assertEqual(
            self.source.sync_state.metadata["materialization_status"], "partial"
        )
        user = get_user_model().objects.create_user("current-reader", password="x")
        client = APIClient()
        client.force_authenticate(user)
        self.assertEqual(
            client.get("/api/knowledge/bcn/norms/").data["results"][0]["title"],
            ROOT_ROWS[0]["title"]["value"],
        )
        repaired = sync_bcn_legal_norms()
        record.refresh_from_db()
        old_fact.refresh_from_db()
        self.assertNotEqual(record.current_snapshot_id, old_snapshot_id)
        self.assertEqual(
            (repaired.estado, BcnLegalNormFact.objects.count()), ("sin_cambios", 2)
        )
        self.assertEqual(old_fact.title, ROOT_ROWS[0]["title"]["value"])

    @patch.object(
        BcnLeyChileSparqlConnector,
        "_query",
        side_effect=[ROOT_ROWS, VERSIONS, RELATIONS],
    )
    def test_first_materialization_failure_is_not_exposed_as_current_knowledge(
        self, query
    ):
        with patch.object(
            BcnLegalNormFact.objects, "create", side_effect=ValueError("fallo inicial")
        ):
            run = sync_bcn_legal_norms()
        self.assertEqual(
            (
                run.estado,
                ExternalSnapshot.objects.count(),
                BcnLegalNormFact.objects.count(),
            ),
            ("parcial", 1, 0),
        )
        user = get_user_model().objects.create_user("empty-reader", password="x")
        client = APIClient()
        client.force_authenticate(user)
        self.assertEqual(client.get("/api/knowledge/bcn/norms/").data["count"], 0)

    @patch.object(BcnLeyChileSparqlConnector, "fetch")
    def test_multi_norm_materialization_failure_restores_entire_previous_corpus(
        self, fetch
    ):
        other = ROOT.replace("19300", "20417")
        fetch.return_value = ConnectorBatch(
            records=[
                connector_record(ROOT, "19300", "Norma uno"),
                connector_record(other, "20417", "Norma dos"),
            ]
        )
        sync_bcn_legal_norms()
        previous = dict(
            self.source.records.values_list("external_id", "current_snapshot_id")
        )
        fetch.return_value = ConnectorBatch(
            records=[
                connector_record(ROOT, "19300", "Norma uno cambiada"),
                connector_record(other, "20417", "Norma dos cambiada"),
            ]
        )
        real_create = BcnLegalNormFact.objects.create
        calls = {"count": 0}

        def fail_second(**kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise ValueError("segunda norma inválida")
            return real_create(**kwargs)

        with patch.object(BcnLegalNormFact.objects, "create", side_effect=fail_second):
            run = sync_bcn_legal_norms()
        self.assertEqual(run.estado, "parcial")
        self.assertEqual(
            dict(self.source.records.values_list("external_id", "current_snapshot_id")),
            previous,
        )
        self.assertEqual(
            (ExternalSnapshot.objects.count(), BcnLegalNormFact.objects.count()), (4, 2)
        )

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
        self.assertEqual(
            client.get("/api/knowledge/bcn/norms/1/text/").status_code, 403
        )
        self.assertEqual(
            client.get("/api/knowledge/bcn/norms/1/articles/").status_code, 403
        )
        self.assertEqual(client.get("/api/knowledge/bcn/articles/1/").status_code, 403)
        user = get_user_model().objects.create_user("legal-reader", password="x")
        client.force_authenticate(user)
        self.assertEqual(client.get("/api/knowledge/bcn/norms/").status_code, 200)
