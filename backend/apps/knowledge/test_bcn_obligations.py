import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .bcn_obligations import extract_bcn_legal_obligation_candidates, extract_obligation_candidates
from .models import BcnLegalArticleFact, BcnLegalNormFact, BcnLegalNormVersionFact, BcnLegalObligationCandidate, BcnLegalObligationExtractionRun, BcnLegalTextParse, BcnLegalTextSourceDocument, EnvironmentalSource, ExternalFileArtifact, ExternalRecord, ExternalSnapshot, SyncRun


def article(text):
    return SimpleNamespace(text_plain=text, text_hash=hashlib.sha256(text.encode()).hexdigest())


class ObligationRuleTests(SimpleTestCase):
    def test_strong_modalities_and_exact_provenance(self):
        text = "Los titulares DEBERÁN informar; se prohíbe descargar. Nadie no podrá alterar y la autoridad deberá fiscalizar."
        candidates = extract_obligation_candidates(article(text))
        self.assertEqual([item["modality_hint"] for item in candidates], ["obligation", "prohibition", "prohibition", "obligation"])
        for item in candidates:
            self.assertEqual(text[item["source_start"]:item["source_end"]], item["source_quote"])
            self.assertEqual(text[item["trigger_start"]:item["trigger_end"]], item["trigger_text"])
            self.assertEqual(hashlib.sha256(item["source_quote"].encode()).hexdigest(), item["source_quote_hash"])

    def test_permission_and_trigger_free_text_produce_no_candidate(self):
        self.assertEqual(extract_obligation_candidates(article("La autoridad podrá solicitar antecedentes.")), [])
        self.assertEqual(extract_obligation_candidates(article("Artículo único sobre definiciones ambientales.")), [])

    def test_same_clause_is_deduplicated_but_distinct_clauses_are_not(self):
        same = extract_obligation_candidates(article("El titular deberá informar y debe conservar el registro."))
        separate = extract_obligation_candidates(article("El titular deberá informar; además debe conservar el registro."))
        self.assertEqual((len(same), len(separate)), (1, 2))

    def test_singular_plural_accents_case_and_prohibitions(self):
        text = "DEBERÁ actuar. Deberán responder. SE PROHÍBE emitir. No podrá descargar. No deberán ocultar."
        candidates = extract_obligation_candidates(article(text))
        self.assertEqual(len(candidates), 5)
        self.assertEqual([c["modality_hint"] for c in candidates].count("obligation"), 2)
        self.assertEqual([c["modality_hint"] for c in candidates].count("prohibition"), 3)


class ObligationCandidatePersistenceTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.get(codigo="bcn-leychile")
        self.source.legal_norm_subscriptions.exclude(number="19300").update(active=False)
        now = timezone.now()
        run = SyncRun.objects.create(source=self.source, trigger="manual", started_at=now)
        snapshot = ExternalSnapshot.objects.create(source=self.source, sync_run=run, external_id="norm:19300", record_kind="bcn_legal_norm", retrieved_at=now, content_hash="a" * 64)
        self.record = ExternalRecord.objects.create(source=self.source, external_id="norm:19300", kind="bcn_legal_norm", canonical_key="LEY:19300", current_snapshot=snapshot, first_seen_at=now, last_seen_at=now)
        self.fact = BcnLegalNormFact.objects.create(snapshot=snapshot, norm_uri="https://datos.bcn.cl/norm/19300", number="19300", title="Ley ambiental", norm_type_uri="https://datos.bcn.cl/type/ley", norm_type_name="Ley", latest_version_uri="https://datos.bcn.cl/version/19300/latest")
        BcnLegalNormVersionFact.objects.create(norm_fact=self.fact, version_uri=self.fact.latest_version_uri, is_latest=True)
        self.artifact = ExternalFileArtifact.objects.create(source=self.source, parent_record=self.record, external_resource_id="bcn-legal-text:test", name="BCN XML", source_url="https://www.leychile.cl/test.xml", format="XML", content_type="text/xml", byte_size=10, retrieved_at=now, content_sha256="b" * 64, metadata={"version_uri":self.fact.latest_version_uri,"norm_number":"19300"}, is_current=True, version=1)
        document = BcnLegalTextSourceDocument.objects.create(artifact=self.artifact, raw_bytes=b"<Norma/>", detected_encoding="UTF-8", byte_size=8)
        self.parse = BcnLegalTextParse.objects.create(source_document=document, parser_version="1", status="success", parsed_at=now, article_count=3)
        self.articles = [self._article("1", "Los titulares deberán informar."), self._article("1 bis", "La autoridad podrá revisar."), self._article("Único", "Se prohíbe descargar.")]

    def _article(self, number, text, parse=None):
        return BcnLegalArticleFact.objects.create(parse=parse or self.parse, article_key=f"key:{number}", article_number=number, article_label=f"Artículo {number}", order_index=(parse or self.parse).articles.count()+1, source_path=f"/{number}", text_plain=text, text_hash=hashlib.sha256(text.encode()).hexdigest(), raw_fragment="<article/>")

    def test_zero_candidate_idempotency_versioning_and_api(self):
        first = extract_bcn_legal_obligation_candidates(); second = extract_bcn_legal_obligation_candidates()
        self.assertEqual((first.processed, first.candidates, first.articles_with_candidates), (3, 2, 2))
        self.assertEqual((second.unchanged, BcnLegalObligationExtractionRun.objects.count(), BcnLegalObligationCandidate.objects.count()), (3, 3, 2))
        zero = self.articles[1].obligation_extraction_runs.get()
        self.assertEqual((zero.status, zero.candidate_count), ("success", 0))
        with patch("apps.knowledge.bcn_obligations.BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION", "rules-2"):
            rules2 = extract_bcn_legal_obligation_candidates()
        self.assertEqual((rules2.processed, BcnLegalObligationExtractionRun.objects.count()), (3, 6))

        client = APIClient()
        self.assertIn(client.get("/api/knowledge/bcn/obligation-candidates/").status_code, (401, 403))
        user = get_user_model().objects.create_user("reader", password="x");client.force_authenticate(user)
        response = client.get("/api/knowledge/bcn/obligation-candidates/?norm_number=19300&article_number=1&modality=obligation&trigger=deber")
        self.assertEqual((response.status_code, response.data["count"]), (200, 1))
        data = response.data["results"][0]
        self.assertEqual((data["norm_number"], data["article_number"], data["extractor_version"]), ("19300", "1", "rules-1"))
        self.assertNotIn("raw_fragment", data);self.assertNotIn("raw_bytes", data)
        self.assertEqual(client.get(f"/api/knowledge/bcn/obligation-candidates/{data['id']}/").status_code, 200)
        page = client.get("/api/knowledge/bcn/obligation-candidates/?page_size=1").data
        self.assertEqual((page["count"], len(page["results"])), (2, 1))

    def test_error_is_immutable_and_next_extractor_version_can_process(self):
        with patch("apps.knowledge.bcn_obligations.extract_obligation_candidates", side_effect=ValueError("regla defectuosa")):
            first = extract_bcn_legal_obligation_candidates(); second = extract_bcn_legal_obligation_candidates()
        self.assertEqual((first.failed, second.failed, BcnLegalObligationExtractionRun.objects.count()), (3, 3, 3))
        with patch("apps.knowledge.bcn_obligations.BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION", "rules-2"):
            repaired = extract_bcn_legal_obligation_candidates()
        self.assertEqual((repaired.processed, BcnLegalObligationExtractionRun.objects.count()), (3, 6))

    def test_parser_current_is_dynamic_and_old_articles_fail_closed(self):
        user = get_user_model().objects.create_user("parser-reader", password="x");client=APIClient();client.force_authenticate(user)
        with patch("apps.knowledge.bcn_text.BCN_LEGAL_XML_PARSER_VERSION", "2"):
            self.assertEqual(client.get(f"/api/knowledge/bcn/norms/{self.fact.id}/articles/").status_code, 404)
            self.assertEqual(client.get(f"/api/knowledge/bcn/articles/{self.articles[0].id}/").status_code, 404)
            parse2 = BcnLegalTextParse.objects.create(source_document=self.parse.source_document, parser_version="2", status="success", parsed_at=timezone.now(), article_count=1)
            current = self._article("2", "Queda obligado a informar.", parse=parse2)
            response = client.get(f"/api/knowledge/bcn/norms/{self.fact.id}/articles/")
            self.assertEqual((response.status_code, response.data["results"][0]["id"]), (200, current.id))

    def test_inactive_subscription_and_superseded_artifact_are_excluded(self):
        extract_bcn_legal_obligation_candidates()
        user = get_user_model().objects.create_user("history-reader", password="x");client=APIClient();client.force_authenticate(user)
        self.assertEqual(client.get("/api/knowledge/bcn/obligation-candidates/").data["count"], 2)
        subscription = self.source.legal_norm_subscriptions.get(number="19300")
        subscription.active=False;subscription.save(update_fields=["active"])
        self.assertEqual(extract_bcn_legal_obligation_candidates().articles, 0)
        self.assertEqual(client.get("/api/knowledge/bcn/obligation-candidates/").data["count"], 0)

    def test_artifact_a_b_a_restores_existing_candidates_without_duplication(self):
        extract_bcn_legal_obligation_candidates()
        runs_a = BcnLegalObligationExtractionRun.objects.count()
        self.artifact.is_current=False;self.artifact.save(update_fields=["is_current"])
        artifact_b = ExternalFileArtifact.objects.create(source=self.source, parent_record=self.record, external_resource_id=self.artifact.external_resource_id, name="BCN XML B", source_url="https://www.leychile.cl/test-b.xml", format="XML", content_type="text/xml", byte_size=10, retrieved_at=timezone.now(), content_sha256="c" * 64, metadata={"version_uri":self.fact.latest_version_uri,"norm_number":"19300"}, is_current=True, version=2)
        document_b = BcnLegalTextSourceDocument.objects.create(artifact=artifact_b, raw_bytes=b"<Norma/>", detected_encoding="UTF-8", byte_size=8)
        parse_b = BcnLegalTextParse.objects.create(source_document=document_b, parser_version="1", status="success", parsed_at=timezone.now(), article_count=1)
        self._article("B", "Queda prohibido descargar.", parse=parse_b)
        extract_bcn_legal_obligation_candidates()
        total_after_b = BcnLegalObligationExtractionRun.objects.count()
        artifact_b.is_current=False;artifact_b.save(update_fields=["is_current"])
        self.artifact.is_current=True;self.artifact.save(update_fields=["is_current"])
        restored = extract_bcn_legal_obligation_candidates()
        self.assertEqual((restored.unchanged, BcnLegalObligationExtractionRun.objects.count()), (3, total_after_b))
        self.assertGreater(total_after_b, runs_a)
        user=get_user_model().objects.create_user("aba-reader",password="x");client=APIClient();client.force_authenticate(user)
        quotes=[item["source_quote"] for item in client.get("/api/knowledge/bcn/obligation-candidates/").data["results"]]
        self.assertNotIn("Queda prohibido descargar", " ".join(quotes))
