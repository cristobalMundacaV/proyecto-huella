import copy
import hashlib
from datetime import timedelta
from io import StringIO
from pathlib import Path
from threading import Event, Thread
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from uuid import UUID

import requests
from defusedxml import ElementTree as ET
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection, DatabaseError, IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .bootstrap import ensure_environmental_source_registry
from .connectors.okobaudat_detail import (DetailError, UpstreamDeferred, NS, dataset_url, document, fetch_detail_bytes,
                                         parse_profile, validate_detail_url)
from .models import (EnvironmentalSource, ExternalSnapshot, SyncRun, OekobaudatProcessFact,
                     OekobaudatEnvironmentalProfileFact as Profile, OekobaudatEnvironmentalIndicatorFact as Indicator)
from .okobaudat_detail_sync import hydrate_details, hydrate_process, snapshot_bytes
from .okobaudat_facts import build_process_fact_payload

FIXTURES = Path(__file__).parent / "fixtures" / "okobaudat_detail"
IDENTITIES = {"a1": ("f63ac879-fa7d-4f91-813e-e816cbdf1927", "00.00.025"),
              "a2": ("c54c16f6-4295-4749-bff0-ba7ed4bc9117", "00.01.000")}
FILES = {"4e1beb5b-f059-4aa9-b12a-4462eb1fa606": "flow_a1.xml",
         "773c4094-cbae-4d73-2a09-47dd71f3b9a0": "flow_a2.xml",
         **{uid: f"detail_{label}.xml" for label, (uid, _) in IDENTITIES.items()}}


def fixture(label):
    return (FIXTURES / f"detail_{label}.xml").read_bytes()


def resolve(kind, uid, version):
    return (FIXTURES / FILES.get(uid, uid + ".xml")).read_bytes()


def fetch(url):
    kind, uid = urlparse(url).path.split("/")[-2:]
    return resolve(kind, uid, "")


def parse(label="a2", body=None, resolver=resolve):
    return parse_profile(body if body is not None else fixture(label), *IDENTITIES[label], resolver)


def mutate(path, *, attr=None, value=None, remove=False, label="a2"):
    root = ET.fromstring(fixture(label))
    node = root.find(path, NS)
    if remove:
        for parent in root.iter():
            if node in list(parent):
                parent.remove(node)
                break
    elif attr:
        node.set(attr, value)
    else:
        node.text = value
    return ET.tostring(root)


class DetailContractTests(SimpleTestCase):
    def test_real_a1_declared_amount_unit_and_gwp(self):
        result = parse("a1")
        self.assertEqual((result["standard"], result["declared_amount"], result["declared_unit"]), ("EN 15804+A1", "1.00", "m3"))
        self.assertEqual(len(result["indicators"]), 25)
        self.assertEqual([n["value"] for n in result["indicators"] if n["code"] == "GWP"], ["-647.4201396839651"])
        self.assertNotIn("GWP-total", [n["code"] for n in result["indicators"]])

    def test_real_a2_reference_scaling_and_separate_gwp(self):
        result = parse()
        self.assertEqual((result["standard"], result["declared_amount"], result["declared_unit"]), ("EN 15804+A2", "1000", "kg"))
        gwp = {n["code"]: n["value"] for n in result["indicators"] if n["code"].startswith("GWP")}
        self.assertEqual(gwp, {"GWP-total": "847.351015163189", "GWP-fossil": "933.522267135669",
                               "GWP-biogenic": "-86.3889351705048", "GWP-luluc": "0.217683198024282"})
        self.assertEqual({n["module"] for n in result["indicators"]}, {"A1-A3"})
        self.assertEqual(len(result["indicators"]), 37)

    def test_unknown_indicator_retains_identity_without_guessing(self):
        uid = "11111111-1111-4111-8111-111111111111"
        body = mutate("p:LCIAResults/p:LCIAResult/p:referenceToLCIAMethodDataSet", attr="refObjectId", value=uid)
        root = ET.fromstring(body)
        root.find("p:LCIAResults/p:LCIAResult/p:referenceToLCIAMethodDataSet", NS).attrib.pop("uri", None)
        body = ET.tostring(root)
        unknown = next(n for n in parse(body=body)["indicators"] if n["upstream_uuid"] == uid)
        self.assertEqual(unknown["code"], uid)

    def test_unknown_unit_is_preserved_without_conversion(self):
        body = mutate("p:LCIAResults/p:LCIAResult/c:other/e:referenceToUnitGroupDataSet/c:shortDescription", value="upstream custom unit")
        self.assertIn("upstream custom unit", [n["unit"] for n in parse(body=body)["indicators"]])

    def test_missing_unit_fails_closed(self):
        body = mutate("p:LCIAResults/p:LCIAResult/c:other/e:referenceToUnitGroupDataSet", remove=True)
        with self.assertRaises(DetailError): parse(body=body)

    def test_missing_declared_unit_fails_closed(self):
        def missing(kind, uid, version):
            body = resolve(kind, uid, version)
            if kind == "unitgroups":
                root = ET.fromstring(body)
                root.find("u:units/u:unit/u:name", NS).text = ""
                return ET.tostring(root)
            return body
        with self.assertRaises(DetailError): parse(resolver=missing)

    def test_uuid_version_format_and_reference_mismatch(self):
        for path, value in [("p:processInformation/p:dataSetInformation/c:UUID", IDENTITIES["a1"][0]),
                            ("p:administrativeInformation/p:publicationAndOwnership/c:dataSetVersion", "99.99.999")]:
            with self.subTest(path=path), self.assertRaises(DetailError): parse(body=mutate(path, value=value))
        with self.assertRaises(DetailError): parse(body=fixture("a2").replace(b'version="1.1"', b'version="2.0"'))
        with self.assertRaises(DetailError): parse(resolver=lambda *args: resolve("flows", FILES.keys().__iter__().__next__(), ""))

    def test_invalid_payload_numbers_and_secure_xml(self):
        for body in [b"bad", b"<html/>", b'<!DOCTYPE x [<!ENTITY a SYSTEM "file:///secret">]><x>&a;</x>']:
            with self.subTest(body=body), self.assertRaises(DetailError): parse(body=body)
        for value in ["NaN", "Infinity", "1e999", "not a number"]:
            with self.subTest(value=value), self.assertRaises(DetailError):
                parse(body=mutate("p:LCIAResults/p:LCIAResult/c:other/e:amount", value=value))

    def test_ambiguous_module_duplicate_and_scenario(self):
        for scenario in [True, False]:
            root = ET.fromstring(fixture("a2")); parent = root.find("p:LCIAResults/p:LCIAResult/c:other", NS)
            amount = parent.find("e:amount", NS)
            if scenario: amount.set(f"{{{NS['e']}}}scenario", "alternative")
            else: parent.append(copy.deepcopy(amount))
            with self.assertRaises(DetailError): parse(body=ET.tostring(root))
        root = ET.fromstring(fixture("a2")); root.find("p:LCIAResults/p:LCIAResult/c:other/e:amount", NS).attrib.clear()
        with self.assertRaises(DetailError): parse(body=ET.tostring(root))

    def test_contradictory_standards_and_gwp_fail(self):
        from .connectors.okobaudat import A1
        body = mutate("p:modellingAndValidation/p:complianceDeclarations/p:compliance/c:referenceToComplianceSystem", attr="refObjectId", value=A1)
        with self.assertRaises(DetailError): parse(body=body)


class DetailSecurityTests(SimpleTestCase):
    def test_allowlist_ssrf_ports_userinfo_and_traversal(self):
        url = dataset_url("processes", *IDENTITIES["a2"])
        self.assertEqual(validate_detail_url(url), url)
        for bad in [url.replace("https:", "http:"), url.replace("www.oekobaudat.de", "127.0.0.1"),
                    url.replace("www.oekobaudat.de", "www.oekobaudat.de:8443"), url.replace("www.oekobaudat.de", "user@www.oekobaudat.de"),
                    url.replace("/processes/", "/../processes/"), "file:///etc/passwd", url + "#fragment",
                    url + "&version=99.99.999", url + "&url=http://127.0.0.1", url.replace("format=XML", "format=JSON")]:
            with self.subTest(url=bad), self.assertRaises(DetailError): validate_detail_url(bad)

    def response(self, status=200, mime="application/xml", body=b"<x/>"):
        response = MagicMock(); response.__enter__.return_value = response
        response.status_code = status; response.headers = {"Content-Type": mime}
        response.url = dataset_url("processes", *IDENTITIES["a2"])
        response.iter_content.return_value = [body]
        return response

    def test_redirects_and_content_type(self):
        for response in [self.response(302), self.response(mime="text/html"), self.response(404)]:
            with patch("apps.knowledge.connectors.okobaudat_detail.requests.get", return_value=response), self.assertRaises(DetailError):
                fetch_detail_bytes(response.url)
            response.__exit__.assert_called_once()

    @override_settings(KNOWLEDGE_OKOBAUDAT_MAX_BYTES=3)
    def test_maximum_decompressed_size(self):
        response = self.response(body=b"1234")
        with patch("apps.knowledge.connectors.okobaudat_detail.requests.get", return_value=response), self.assertRaises(DetailError):
            fetch_detail_bytes(response.url)

    def test_sanitized_network_errors_and_retries(self):
        with patch("apps.knowledge.connectors.okobaudat_detail.requests.get", side_effect=requests.ConnectionError("secret=password")) as get, patch("apps.knowledge.connectors.okobaudat_detail.time.sleep"):
            with self.assertRaises(DetailError) as error: fetch_detail_bytes(dataset_url("processes", *IDENTITIES["a2"]))
            self.assertNotIn("secret", str(error.exception)); self.assertEqual(get.call_count, 3)

    def test_rate_limit_retry_after(self):
        first = self.response(429); first.headers["Retry-After"] = "4"
        second = self.response()
        with patch("apps.knowledge.connectors.okobaudat_detail.requests.get", side_effect=[first, second]), patch("apps.knowledge.connectors.okobaudat_detail.time.sleep") as sleep:
            self.assertEqual(fetch_detail_bytes(second.url), b"<x/>"); sleep.assert_called_once_with(4)

    def test_long_retry_after_defers_without_early_retry(self):
        response = self.response(429); response.headers["Retry-After"] = "600"
        with patch("apps.knowledge.connectors.okobaudat_detail.requests.get", return_value=response) as get:
            with self.assertRaises(UpstreamDeferred): fetch_detail_bytes(response.url)
            get.assert_called_once()


def make_process(label="a2", version=None):
    source = EnvironmentalSource.objects.get(codigo="okobaudat")
    uid, original = IDENTITIES[label]; version = version or original
    run = SyncRun.objects.create(source=source, trigger="manual", started_at=timezone.now())
    payload = {"process_uuid": uid, "dataset_version": version, "datastock_uuid": "cc64f7e1-14d8-4a57-b11b-2cf03d200c82",
               "name": "Official fixture " + label, "source_url": dataset_url("processes", uid, version),
               "compliance_standard_raw": "EN 15804+" + label.upper(),
               "classification": [{"name": "fixture"}], "languages": {"en": ["Official fixture"]},
               "process_metadata": {"fixture": label}}
    snapshot = ExternalSnapshot.objects.create(source=source, sync_run=run, external_id=f"catalog:{uid}:{version}", record_kind="okobaudat_process",
        retrieved_at=timezone.now(), content_hash=hashlib.sha256(str(payload).encode()).hexdigest(), raw_payload=payload)
    return OekobaudatProcessFact.objects.create(snapshot=snapshot, **build_process_fact_payload(snapshot)), run


class DetailHydrationTests(TestCase):
    def setUp(self):
        ensure_environmental_source_registry()
        self.process, self.run = make_process()
        self.fetcher = patch("apps.knowledge.okobaudat_detail_sync.fetch_detail_bytes", side_effect=fetch)
        self.mock_fetch = self.fetcher.start(); self.addCleanup(self.fetcher.stop)

    def hydrate(self, **kwargs):
        return hydrate_process(self.process, self.run, delay=0, **kwargs)

    def test_materialization_provenance_and_idempotence(self):
        result = self.hydrate(); self.assertEqual(result["status"], "materialized", result)
        profile = Profile.objects.get(); self.assertEqual(profile.process_id, self.process.pk)
        self.assertEqual(Indicator.objects.count(), 37)
        self.assertEqual(len(profile.provenance["references"]), 3)
        self.assertEqual(snapshot_bytes(profile.snapshot), fixture("a2"))
        self.assertEqual(profile.snapshot.content_hash, hashlib.sha256(fixture("a2")).hexdigest())
        calls = self.mock_fetch.call_count
        self.assertEqual(self.hydrate()["status"], "already_hydrated")
        self.assertEqual(self.hydrate(refetch_reason="upstream investigation")["status"], "already_hydrated")
        self.assertEqual(self.mock_fetch.call_count, calls)

    def test_atomic_failure_keeps_all_observations_and_retry_does_not_download(self):
        create = Indicator.objects.create
        inserted = []
        def fail_after_first(**kwargs):
            if inserted: raise RuntimeError("secret=hidden")
            inserted.append(create(**kwargs))
            return inserted[-1]
        with patch.object(Indicator.objects, "create", side_effect=fail_after_first):
            result = self.hydrate()
        self.assertEqual(result["status"], "failed"); self.assertNotIn("secret", result["error"])
        self.assertEqual((Profile.objects.count(), Indicator.objects.count()), (0, 0))
        self.assertEqual(ExternalSnapshot.objects.filter(record_kind__startswith="okobaudat_").count(), 5)
        self.mock_fetch.reset_mock()
        self.assertEqual(self.hydrate()["status"], "materialized")
        self.mock_fetch.assert_not_called()

    def test_invalid_observation_is_historical_and_governed_refetch(self):
        self.mock_fetch.side_effect = lambda url: b"invalid" if "/processes/" in url else fetch(url)
        self.assertEqual(self.hydrate()["status"], "failed")
        old = ExternalSnapshot.objects.get(record_kind="okobaudat_process_detail")
        self.mock_fetch.side_effect = fetch
        self.assertEqual(self.hydrate()["status"], "failed")
        self.assertEqual(self.hydrate(refetch_reason="corrected upstream invalid XML")["status"], "materialized")
        self.assertEqual(ExternalSnapshot.objects.filter(record_kind="okobaudat_process_detail").count(), 2)
        self.assertEqual(snapshot_bytes(old), b"invalid")

    def test_interruption_resumes_from_observed_process(self):
        calls = 0
        def interrupted(url):
            nonlocal calls
            calls += 1
            if calls == 2: raise KeyboardInterrupt
            return fetch(url)
        self.mock_fetch.side_effect = interrupted
        with self.assertRaises(KeyboardInterrupt): self.hydrate()
        self.assertEqual(Profile.objects.count(), 0)
        self.mock_fetch.side_effect = fetch; self.mock_fetch.reset_mock()
        self.assertEqual(self.hydrate()["status"], "materialized")
        self.assertEqual(self.mock_fetch.call_count, 3)

    def test_new_version_is_independent(self):
        self.assertEqual(self.hydrate()["status"], "materialized")
        process, run = make_process(version="00.01.001")
        # Modify by namespace so fixture prefix changes cannot invalidate the test.
        def new_version(url):
            if "/processes/" not in url: return fetch(url)
            root = ET.fromstring(fetch(url)); root.find("p:administrativeInformation/p:publicationAndOwnership/c:dataSetVersion", NS).text = "00.01.001"
            return ET.tostring(root)
        self.mock_fetch.side_effect = new_version
        result = hydrate_process(process, run, delay=0)
        self.assertEqual(result["status"], "materialized", result)
        self.assertEqual(Profile.objects.count(), 2)

    def test_batch_failure_isolation_and_summary(self):
        make_process("a1")
        self.mock_fetch.side_effect = lambda url: b"bad" if IDENTITIES["a2"][0] in url else fetch(url)
        result = hydrate_details(batch_size=1, delay=0)
        self.assertEqual((result["candidates"], result["failed"], result["materialized"], result["indicators_created"]), (2, 1, 1, 25))
        self.assertEqual(Profile.objects.get().standard, "EN 15804+A1")

    def test_upstream_pause_leaves_remaining_processes_pending(self):
        make_process("a1")
        self.mock_fetch.side_effect = UpstreamDeferred("Upstream solicita reintentar mas tarde.")
        result = hydrate_details(delay=0)
        self.assertEqual((result["failed"], result["skipped"], self.mock_fetch.call_count), (1, 1, 1))

    def test_command_summary_and_limit(self):
        output = StringIO(); call_command("hydrate_okobaudat_process_details", limit=1, batch_size=1, delay=0, stdout=output)
        self.assertIn('"materialized": 1', output.getvalue())
        self.assertEqual(hydrate_details(delay=0)["already_hydrated"], 1)

    def test_repeated_limit_advances_past_already_hydrated(self):
        make_process("a1")
        first = hydrate_details(limit=1, batch_size=1, delay=0)
        second = hydrate_details(limit=1, batch_size=1, delay=0)
        self.assertEqual((first["candidates"], first["materialized"], first["skipped"]), (2, 1, 1))
        self.assertEqual((second["already_hydrated"], second["materialized"], second["skipped"]), (1, 1, 0))

    def test_run_records_interruption_and_resumes(self):
        self.mock_fetch.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt): hydrate_details(delay=0)
        run = SyncRun.objects.latest("id")
        self.assertTrue(run.metadata["interrupted"])
        self.assertIsNotNone(run.finished_at)
        self.mock_fetch.side_effect = fetch
        self.assertEqual(hydrate_details(delay=0)["materialized"], 1)

    def test_immutability_all_orm_paths(self):
        self.hydrate()
        for model in [Profile, Indicator]:
            item = model.objects.first()
            for operation in [lambda: item.save(), lambda: item.delete(), lambda: model.objects.update(standard="unknown"),
                              lambda: model.objects.all().delete(), lambda: model.objects.bulk_create([]),
                              lambda: model.objects.bulk_update([item], ["standard"])]:
                with self.subTest(model=model.__name__), self.assertRaises(ValidationError), transaction.atomic(): operation()
            item.pk = None
            with self.assertRaises(ValidationError): item.save()

    def test_a1_a2_remain_separate(self):
        self.hydrate(); process, run = make_process("a1")
        self.assertEqual(hydrate_process(process, run, delay=0)["status"], "materialized")
        self.assertEqual(set(Profile.objects.values_list("standard", flat=True)), {"EN 15804+A1", "EN 15804+A2"})
        self.assertFalse(Indicator.objects.filter(standard="EN 15804+A1", code="GWP-total").exists())

    def test_api_auth_list_detail_filters_provenance_and_freshness(self):
        self.hydrate(); client = APIClient(); base = "/api/knowledge/materials/oekobaudat/"
        self.assertIn(client.get(base + "profiles/").status_code, [401, 403])
        client.force_authenticate(get_user_model().objects.create_user("detail-reader"))
        data = client.get(base + "profiles/", {"uuid": str(self.process.process_uuid), "version": self.process.dataset_version, "standard": "EN 15804+A2", "indicator": "GWP-total", "module": "A1-A3"})
        self.assertEqual(data.status_code, 200); self.assertEqual(data.data["count"], 1)
        row = data.data["results"][0]
        for key in ["snapshot", "source", "content_hash", "retrieved_at", "source_url", "standard", "dataset_version", "freshness", "provenance"]: self.assertIn(key, row)
        self.assertEqual(row["freshness"], "fresh")
        self.assertTrue(row["source_terms"]["not_designed_for_product_lca"])
        self.assertEqual(client.get(base + f"profiles/{row['id']}/").status_code, 200)
        indicators = client.get(base + "indicators/", {"indicator": "GWP-total"}).data
        self.assertEqual(indicators["count"], 1)
        self.assertEqual(client.get(base + f"indicators/{indicators['results'][0]['id']}/").status_code, 200)
        self.assertEqual(client.get(base + "indicators/", {"module": "A4"}).data["count"], 0)
        self.assertEqual(client.get(base + "profiles/", {"uuid": "bad"}).status_code, 400)
        self.assertEqual(client.post(base + "profiles/", {}).status_code, 405)
        with patch("apps.knowledge.okobaudat_detail_api.timezone.now", return_value=timezone.now() + timedelta(days=365)):
            self.assertEqual(client.get(base + f"profiles/{row['id']}/").data["freshness"], "stale")


class DetailPostgresTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor != "postgresql": return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'django_migrations'")
            tables = [connection.ops.quote_name(row[0]) for row in cursor.fetchall()]
            if tables: cursor.execute("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE")
        # Match Django flush semantics: restore registered reference data for the
        # next TransactionTestCase instead of leaking an empty source registry.
        from django.core.management.sql import emit_post_migrate_signal
        emit_post_migrate_signal(verbosity=0, interactive=False, db=connection.alias)

    def test_two_workers_download_and_materialize_once(self):
        if connection.vendor != "postgresql": self.skipTest("Requires real PostgreSQL")
        ensure_environmental_source_registry(); process, run = make_process()
        entered, release = Event(), Event(); results, errors, urls = [], [], []
        def download(url):
            urls.append(url)
            if "/processes/" in url:
                entered.set(); release.wait(10)
            return fetch(url)
        def worker():
            close_old_connections()
            try: results.append(hydrate_process(OekobaudatProcessFact.objects.get(pk=process.pk), SyncRun.objects.get(pk=run.pk), delay=0))
            except BaseException as exc: errors.append(type(exc).__name__)
            finally: close_old_connections()
        with patch("apps.knowledge.okobaudat_detail_sync.fetch_detail_bytes", side_effect=download):
            first = Thread(target=worker); first.start(); self.assertTrue(entered.wait(10))
            second = Thread(target=worker); second.start(); second.join(10); release.set(); first.join(20)
        self.assertFalse(errors); self.assertEqual(sorted(r["status"] for r in results), ["materialized", "skipped"])
        self.assertEqual((Profile.objects.count(), Indicator.objects.count(), len(urls)), (1, 37, 4))
        for table in [Profile._meta.db_table, Indicator._meta.db_table]:
            for verb in [f"UPDATE {table} SET standard='unknown'", f"DELETE FROM {table}"]:
                with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(verb)
        with self.assertRaises(DatabaseError), transaction.atomic():
            ExternalSnapshot.objects.filter(record_kind="okobaudat_process_detail").update(raw_payload={})
        columns = ", ".join(connection.ops.quote_name(f.column) for f in Profile._meta.fields if not f.primary_key)
        other_snapshot = ExternalSnapshot.objects.filter(record_kind="okobaudat_detail_reference").first().pk
        selected = ", ".join(str(other_snapshot) if f.name == "snapshot" else connection.ops.quote_name(f.column)
                             for f in Profile._meta.fields if not f.primary_key)
        with self.assertRaises(IntegrityError) as error, transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"INSERT INTO {Profile._meta.db_table} ({columns}) SELECT {selected} FROM {Profile._meta.db_table}")
        self.assertEqual(error.exception.__cause__.diag.constraint_name, "knowledge_obd_profile_identity")
        columns = ", ".join(connection.ops.quote_name(f.column) for f in Indicator._meta.fields if not f.primary_key)
        selected = ", ".join("'A4'" if f.name == "module" else connection.ops.quote_name(f.column)
                             for f in Indicator._meta.fields if not f.primary_key)
        with self.assertRaises(IntegrityError) as error, transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"INSERT INTO {Indicator._meta.db_table} ({columns}) SELECT {selected} FROM {Indicator._meta.db_table} LIMIT 1")
        self.assertEqual(error.exception.__cause__.diag.constraint_name, "knowledge_obd_a1a3_only")
