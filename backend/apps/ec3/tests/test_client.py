import json
from unittest.mock import Mock

import requests
from django.core.exceptions import ValidationError
from django.test import TestCase, SimpleTestCase, override_settings

from apps.ec3.client import Ec3Client, UpstreamError, retry_after
from apps.ec3.models import ResponseCache
from apps.ec3.rate_limit import RateLimited
from apps.ec3.schemas import external_id, normalize, project_epd
from .fixtures import SETTINGS, response, search_payload, steel_payload


@override_settings(**SETTINGS)
class ClientTests(TestCase):
    def setUp(self):
        self.session, self.limiter, self.sleep = Mock(), Mock(), Mock()
        self.client = Ec3Client(session=self.session, limiter=self.limiter, sleep=self.sleep)

    def test_real_documented_search_contract_and_pagination(self):
        self.session.get.return_value = response(search_payload())
        result = self.client.search('!EC3 search("StructuralSteel") !pragma oMF("1.0/1")', page_size=1)
        self.assertEqual(result["data"]["next_page"], 2)
        call = self.session.get.call_args
        self.assertEqual(call.args[0], "https://openepd.buildingtransparency.org/api/v2/epds/search")
        self.assertEqual(call.kwargs["params"]["page_number"], 1)
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer synthetic-token-not-a-credential")
        self.assertFalse(call.kwargs["allow_redirects"])
        self.assertEqual(call.kwargs["timeout"], (5, 20))
        self.assertEqual(self.limiter.acquire.call_args.args, (1,))

    def test_detail_checksum_minimal_cache_and_refresh(self):
        self.session.get.return_value = response(steel_payload())
        result = self.client.detail("ec3test1")
        cached = self.client.detail("ec3test1")
        self.assertEqual(len(result["payload_checksum"]), 64)
        self.assertTrue(cached["cache_hit"])
        self.assertEqual(result["retrieved_at"], cached["retrieved_at"])
        self.assertNotIn("lca_discussion", result["data"])
        self.assertNotIn("DO NOT PERSIST", json.dumps(ResponseCache.objects.first().value))
        self.assertNotIn("synthetic-token", json.dumps(ResponseCache.objects.first().value))
        self.assertEqual(self.session.get.call_count, 1)
        self.client.detail("ec3test1", refresh=True)
        self.assertEqual(self.session.get.call_count, 2)

    @override_settings(EC3_STORAGE_ALLOWED=False)
    def test_no_cache_without_rights(self):
        self.session.get.return_value = response(steel_payload())
        self.client.detail("ec3test1")
        self.client.detail("ec3test1")
        self.assertEqual(self.session.get.call_count, 2)
        self.assertFalse(ResponseCache.objects.exists())

    @override_settings(EC3_RIGHTS_VALID_UNTIL="2020-01-01")
    def test_expired_rights_disable_cache(self):
        self.test_no_cache_without_rights()

    def test_retries_5xx_and_timeouts_consume_tokens(self):
        self.session.get.side_effect = [response(status=503), requests.Timeout("SECRET"), response(steel_payload())]
        self.client.detail("ec3test1")
        self.assertEqual(self.limiter.acquire.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_429_long_retry_after_defers_shared_budget(self):
        self.session.get.return_value = response(status=429, headers={"Retry-After": "120"})
        with self.assertRaises(RateLimited) as error:
            self.client.detail("ec3test1")
        self.assertEqual(error.exception.retry_after, 120)
        self.limiter.defer.assert_called_once_with(120)
        self.sleep.assert_not_called()

    def test_429_short_retry_then_success(self):
        self.session.get.side_effect = [response(status=429, headers={"Retry-After": "1"}), response(steel_payload())]
        self.client.detail("ec3test1")
        self.assertEqual(self.limiter.acquire.call_count, 2)
        self.sleep.assert_called_once_with(1)

    def test_errors_never_include_upstream_body_or_credentials(self):
        for status in (301, 400, 401, 403, 404):
            with self.subTest(status=status):
                self.session.get.return_value = response({"detail": "SECRET"}, status=status)
                with self.assertRaises(UpstreamError) as error:
                    self.client.detail("ec3test1", refresh=True)
                self.assertNotIn("SECRET", str(error.exception))
        self.assertEqual(self.session.get.call_count, 5)

    def test_timeout_exhaustion_safe(self):
        self.session.get.side_effect = requests.Timeout("SECRET")
        with self.assertRaisesRegex(UpstreamError, "ec3_network_timeout"):
            self.client.detail("ec3test1")
        self.assertEqual(self.session.get.call_count, 3)

    def test_malformed_mismatched_and_private_responses(self):
        payloads = [[], {**steel_payload(), "id": "ec3test2"}, {**steel_payload(), "private": True},
                    {**steel_payload(), "version": True}, {**steel_payload(), "declared_unit": {"qty": True, "unit": "kg"}}]
        for payload in payloads:
            with self.subTest(payload=type(payload)):
                self.session.get.return_value = response(payload)
                with self.assertRaisesRegex(UpstreamError, "ec3_schema_invalid"):
                    self.client.detail("ec3test1", refresh=True)

    def test_invalid_json_content_type_and_oversize(self):
        for mocked, code in [(response(raw=b'{"id": NaN}'), "ec3_schema_invalid"),
                             (response(raw=b'{}', headers={"Content-Type": "text/html"}), "ec3_invalid_content_type"),
                             (response(raw=b'x' * (2 * 1024 * 1024 + 1)), "ec3_response_too_large")]:
            self.session.get.return_value = mocked
            with self.assertRaisesRegex(UpstreamError, code):
                self.client.detail("ec3test1")
            mocked.close.assert_called_once()

    def test_disabled_and_missing_credentials_do_not_call_network(self):
        for setting in ({"EC3_ENABLED": False}, {"EC3_API_TOKEN": ""}):
            with self.settings(**setting), self.assertRaises(ValidationError):
                self.client.detail("ec3test1")
        self.session.get.assert_not_called()

    def test_no_ssrf_or_unbounded_pages(self):
        for epd_id in ("https://evil.example/x", "../epds", "ec3test1?token=x", "ec3test1/x"):
            with self.assertRaises(ValidationError):
                self.client.detail(epd_id)
        with self.assertRaises(ValidationError):
            self.client.search("x", page_size=250)
        self.session.get.assert_not_called()


class SchemaTests(SimpleTestCase):
    def test_normalization_uses_only_explicit_gwp_scope_and_lcia(self):
        evidence = project_epd(steel_payload(), detail=True)
        normalized = normalize(evidence, "EF 3.0")
        self.assertTrue(normalized["compatible"])
        self.assertEqual(normalized["version_value"], "1.8000000000")
        self.assertFalse(normalize(evidence, "Unknown LCIA")["compatible"])
        evidence["impacts"]["EF 3.0"]["gwp"].pop("A1A2A3")
        self.assertFalse(normalize(evidence, "EF 3.0")["compatible"])

    def test_zero_negative_and_unknown_units_are_not_guessed(self):
        evidence = project_epd(steel_payload(), detail=True)
        for qty in ("0", "-1"):
            evidence["declared_unit"]["qty"] = qty
            self.assertFalse(normalize(evidence, "EF 3.0")["compatible"])
        evidence["declared_unit"] = {"qty": "1", "unit": "unknown"}
        self.assertFalse(normalize(evidence, "EF 3.0")["compatible"])

    def test_id_and_retry_after(self):
        self.assertEqual(external_id("EC3-TEST1"), "ec3test1")
        self.assertEqual(retry_after("bad", 60), 60)
        self.assertEqual(retry_after("NaN", 60), 60)
