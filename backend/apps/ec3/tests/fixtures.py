"""Synthetic contract fixtures, NOT EPDs retrieved from EC3. No real product claims."""
import json
from unittest.mock import Mock


def steel_payload(version=1, mean=1800):
    return {
        "id": "ec3test1", "doctype": "OpenEPD", "openepd_version": "0.1", "version": version,
        "private": False, "product_name": "SYNTHETIC structural steel — offline test only",
        "declaration_url": "https://example.org/synthetic-epd", "program_operator_doc_id": "SYNTHETIC-001",
        "program_operator_version": str(version), "date_of_issue": "2020-01-01T00:00:00Z",
        "valid_until": "2035-01-01T00:00:00Z", "declared_unit": {"qty": 1000, "unit": "kg"},
        "manufacturer": {"web_domain": "manufacturer.example.org", "name": "Synthetic manufacturer"},
        "program_operator": {"web_domain": "operator.example.org"},
        "third_party_verifier": {"web_domain": "verifier.example.org"},
        "pcr": {"id": "https://example.org/pcr", "name": "Synthetic PCR"},
        "compliance": [{"short_name": "EN 15804+A2", "link": "https://example.org/standard"}],
        "applicable_in": ["CL"], "ec3": {"category": "StructuralSteel", "product_specific": True},
        "impacts": {"EF 3.0": {"gwp": {"A1A2A3": {"mean": mean, "unit": "kgCO2e", "rsd": 0.1}}}},
        "lca_discussion": "DO NOT PERSIST OR CACHE THIS FULL TEXT",
    }


def response(payload=None, status=200, headers=None, raw=None):
    result = Mock()
    result.status_code = status
    result.headers = {"Content-Type": "application/json", **(headers or {})}
    result.iter_content.return_value = [raw if raw is not None else json.dumps(payload).encode()]
    return result


def search_payload():
    return {"payload": [steel_payload()], "meta": {"paging": {"total_count": 2, "total_pages": 2, "page_size": 1}}}


CONTEXT = {field: "Human reviewer: synthetic offline technical evidence only" for field in (
    "technical_basis", "geographic_basis", "temporal_basis", "standard_basis", "verification_basis", "note")}

SETTINGS = {"EC3_ENABLED": True, "EC3_API_TOKEN": "synthetic-token-not-a-credential",
            "EC3_STORAGE_ALLOWED": True, "EC3_RIGHTS_REFERENCE": "SYNTHETIC TEST RIGHTS ONLY",
            "EC3_RIGHTS_VALID_UNTIL": "2035-01-01", "EC3_CACHE_TTL_SECONDS": 300,
            "EC3_EVIDENCE_MAX_AGE_HOURS": 168}
