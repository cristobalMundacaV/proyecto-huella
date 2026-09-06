import hashlib
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from defusedxml.common import DefusedXmlException
from rest_framework.test import APIClient

from .bcn_text import parse_bcn_legal_xml, sync_bcn_legal_texts
from .downloads import DownloadedExternalFile
from .models import BcnLegalArticleFact, BcnLegalNormFact, BcnLegalNormVersionFact, BcnLegalTextParse, EnvironmentalSource, ExternalFileArtifact, ExternalRecord, ExternalSnapshot, SyncRun

NS = "http://www.leychile.cl/esquemas"


def xml(body):
    return f"""<?xml version="1.0" encoding="UTF-8"?><Norma xmlns="{NS}"><EstructurasFuncionales>{body}</EstructurasFuncionales></Norma>""".encode()


def article(identifier, number, text):
    return f"""<EstructuraFuncional tipoParte="Artículo" idParte="{identifier}"><Texto>{text}</Texto><Metadatos><NombreParte presente="si">{number}</NombreParte><TituloParte presente="no">&#160;</TituloParte></Metadatos></EstructuraFuncional>"""


class BcnLegalXmlParserTests(SimpleTestCase):
    def test_real_structure_preserves_order_accents_whitespace_and_bis(self):
        parsed = parse_bcn_legal_xml(
            xml(
                article("10", "1", " Artículo 1°.-  Protección   ambiental ")
                + article("11", "1 bis", "Artículo 1 bis.- Régimen especial")
            )
        )
        self.assertEqual(
            [a["article_key"] for a in parsed], ["idParte:10", "idParte:11"]
        )
        self.assertEqual([a["article_number"] for a in parsed], ["1", "1 bis"])
        self.assertEqual(parsed[0]["text_plain"], "Artículo 1°.- Protección ambiental")
        self.assertEqual(
            [a["source_path"] for a in parsed],
            [
                "/Norma[1]/EstructurasFuncionales[1]/EstructuraFuncional[1]",
                "/Norma[1]/EstructurasFuncionales[1]/EstructuraFuncional[2]",
            ],
        )

    def test_unique_article_and_nested_namespace_structure(self):
        parsed = parse_bcn_legal_xml(
            xml(article("unique", "Único", "Artículo único.- Texto oficial"))
        )
        self.assertEqual((len(parsed), parsed[0]["article_number"]), (1, "Único"))
        self.assertIn("EstructuraFuncional", parsed[0]["raw_fragment"])

    def test_empty_corrupt_and_wrong_root_fail_closed(self):
        for payload in (b"", b"<Norma>", b"<html></html>"):
            with self.assertRaises(Exception):
                parse_bcn_legal_xml(payload)

    def test_doctype_and_external_entity_are_rejected(self):
        payload = b"""<?xml version="1.0"?><!DOCTYPE Norma [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Norma><Texto>&xxe;</Texto></Norma>"""
        with self.assertRaises(DefusedXmlException):
            parse_bcn_legal_xml(payload)

    def test_entity_expansion_is_rejected(self):
        payload = b"""<!DOCTYPE Norma [<!ENTITY a "123"><!ENTITY b "&a;&a;&a;">]><Norma>&b;</Norma>"""
        with self.assertRaises(DefusedXmlException):
            parse_bcn_legal_xml(payload)


class BcnLegalTextPublicationTests(TestCase):
    def setUp(self):
        source = EnvironmentalSource.objects.get(codigo="bcn-leychile")
        source.legal_norm_subscriptions.exclude(number="19300").delete()
        now = timezone.now()
        run = SyncRun.objects.create(source=source, trigger="manual", started_at=now)
        snapshot = ExternalSnapshot.objects.create(source=source, sync_run=run, external_id="norm:19300", record_kind="bcn_legal_norm", retrieved_at=now, content_hash="a" * 64)
        record = ExternalRecord.objects.create(source=source, external_id="norm:19300", kind="bcn_legal_norm", current_snapshot=snapshot, first_seen_at=now, last_seen_at=now)
        self.fact = BcnLegalNormFact.objects.create(snapshot=snapshot, norm_uri="https://datos.bcn.cl/norm/19300", number="19300", title="Ley ambiental", norm_type_uri="https://datos.bcn.cl/type/ley", norm_type_name="Ley", latest_version_uri="https://datos.bcn.cl/version/19300/latest")
        BcnLegalNormVersionFact.objects.create(norm_fact=self.fact, version_uri=self.fact.latest_version_uri, is_latest=True, xml_document_url="http://www.leychile.cl/Consulta/obtxml?idNorma=30667")
        self.record = record

    def _download(self, payload):
        def create(*args, **kwargs):
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
            handle.write(payload)
            handle.close()
            return DownloadedExternalFile(handle.name, len(payload), hashlib.sha256(payload).hexdigest(), "https://www.leychile.cl/Consulta/obtxml?idNorma=30667", "text/xml", "", "")
        return create

    def test_atomic_publication_idempotency_history_and_authenticated_api(self):
        first_xml = xml(article("10", "1", "Articulo 1.- Texto vigente"))
        with patch("apps.knowledge.bcn_text.download_external_file", side_effect=self._download(first_xml)):
            first = sync_bcn_legal_texts()
            second = sync_bcn_legal_texts()
        self.assertEqual((first.imported, second.unchanged), (1, 1))
        first_artifact = ExternalFileArtifact.objects.get(is_current=True)
        first_article = BcnLegalArticleFact.objects.get()
        self.assertEqual(first_artifact.external_resource_id, "bcn-legal-text:" + hashlib.sha256(self.fact.latest_version_uri.encode()).hexdigest())
        self.assertEqual(first_artifact.bcn_legal_source_document.raw_bytes, first_xml)

        second_xml = xml(article("10", "1", "Articulo 1.- Texto modificado"))
        with patch("apps.knowledge.bcn_text.download_external_file", side_effect=self._download(second_xml)):
            changed = sync_bcn_legal_texts()
        first_artifact.refresh_from_db()
        self.assertEqual((changed.imported, ExternalFileArtifact.objects.count(), first_artifact.is_current), (1, 2, False))

        current_id = ExternalFileArtifact.objects.get(is_current=True).id
        with patch("apps.knowledge.bcn_text.download_external_file", side_effect=self._download(b"<Norma>")):
            failed = sync_bcn_legal_texts()
        self.assertEqual(failed.failed, 1)
        self.assertEqual(ExternalFileArtifact.objects.get(is_current=True).id, current_id)
        self.assertEqual(BcnLegalTextParse.objects.filter(status="error").count(), 1)

        user = get_user_model().objects.create_user("legal-reader", password="x")
        client = APIClient(); client.force_authenticate(user)
        self.assertEqual(client.get(f"/api/knowledge/bcn/norms/{self.fact.id}/text/").status_code, 200)
        self.assertEqual(client.get(f"/api/knowledge/bcn/articles/{first_article.id}/").status_code, 404)
        self.assertEqual(client.get(f"/api/knowledge/bcn/norms/{self.fact.id}/articles/").data["count"], 1)
