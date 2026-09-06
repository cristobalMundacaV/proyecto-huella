import json
import re
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from ..downloads import KNOWLEDGE_USER_AGENT, validate_external_url
from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector

ENDPOINT = "https://datos.bcn.cl/sparql"
PREFIXES = """PREFIX bcn: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""
TOKEN = re.compile(r"^[A-Z]{2,12}$")
NUMBER = re.compile(r"^[0-9A-Z.-]{1,60}$")
RELATIONS = {
    "modifiesTo": "modifies",
    "isModifiedBy": "is_modified_by",
    "regulates": "regulates",
    "isRegulatedBy": "is_regulated_by",
    "rectifies": "rectifies",
    "isRectifiedBy": "is_rectified_by",
    "recasts": "recasts",
    "isRecastedBy": "is_recasted_by",
}


def _value(binding, key):
    return binding.get(key, {}).get("value", "")


def _date(value):
    return date.fromisoformat(value[:10]) if value else None


class BcnLeyChileSparqlConnector(EnvironmentalConnector):
    def _query(self, query):
        validate_external_url(self.source.base_url, {"datos.bcn.cl"})
        request = Request(
            self.source.base_url,
            data=urlencode(
                {"query": PREFIXES + query, "format": "application/sparql-results+json"}
            ).encode(),
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": KNOWLEDGE_USER_AGENT,
            },
        )
        timeout = getattr(settings, "KNOWLEDGE_SPARQL_TIMEOUT_SECONDS", 30)
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {
                "application/sparql-results+json",
                "application/json",
            }:
                raise ValueError("Formato SPARQL BCN no soportado.")
            payload = json.load(response)
        try:
            return payload["results"]["bindings"]
        except (KeyError, TypeError) as exc:
            raise ValueError("Respuesta SPARQL BCN corrupta.") from exc

    def _norm(self, subscription):
        norm_type = subscription.norm_type.upper()
        number = subscription.number.upper()
        if not TOKEN.fullmatch(norm_type) or not NUMBER.fullmatch(number):
            raise ValueError("Suscripción BCN contiene identidad inválida.")
        type_slug = norm_type.lower()
        roots = self._query(
            f"""SELECT DISTINCT ?norm ?title ?type ?identifier ?issuer ?publish ?promulgation WHERE {{
          ?norm a bcn:RootNorm; bcn:hasNumber ?publishedNumber; bcn:type ?type; dc:title ?title .
          FILTER(str(?publishedNumber) = "{number}")
          FILTER(?type = <http://datos.bcn.cl/recurso/cl/norma/tipo#{type_slug}>)
          OPTIONAL {{?norm dc:identifier ?identifier}} OPTIONAL {{?norm bcn:createdBy ?issuer}}
          OPTIONAL {{?norm bcn:publishDate ?publish}} OPTIONAL {{?norm bcn:promulgationDate ?promulgation}}
        }}"""
        )
        uris = {_value(row, "norm") for row in roots}
        if len(uris) != 1:
            raise ValueError(
                f"BCN {norm_type} {number}: se esperaba una norma raíz única; obtenidas {len(uris)}."
            )
        root = roots[0]
        uri = next(iter(uris))
        versions = self._query(
            f"""SELECT DISTINCT ?version ?versionDate ?latest ?xml ?html WHERE {{
          <{uri}> bcn:hasVersion ?version . OPTIONAL {{?version bcn:versionDate ?versionDate}}
          OPTIONAL {{?version bcn:isLatestVersion ?latest}} OPTIONAL {{?version bcn:hasXmlDocument ?xml}}
          OPTIONAL {{?version bcn:hasHtmlDocument ?html}}
        }} ORDER BY ?version"""
        )
        grouped = {}
        for item in versions:
            uri_key = _value(item, "version")
            current = grouped.setdefault(uri_key, {"latest_values": set()})
            current.update(
                {
                    "version_uri": uri_key,
                    "version_date": _value(item, "versionDate"),
                    "xml_document_url": _value(item, "xml"),
                    "html_document_url": _value(item, "html"),
                }
            )
            if _value(item, "latest"):
                current["latest_values"].add(_value(item, "latest").lower())
        normalized_versions = []
        for item in grouped.values():
            flags = item.pop("latest_values")
            item["is_latest"] = flags in ({"true"}, {"1"})
            normalized_versions.append(item)
        latest = [v for v in normalized_versions if v["is_latest"]]
        if len(latest) != 1:
            raise ValueError(
                f"BCN {norm_type} {number}: se esperaba exactamente una versión latest."
            )
        predicates = ", ".join(f"bcn:{name}" for name in RELATIONS)
        relations = self._query(
            f"""SELECT DISTINCT ?predicate ?target WHERE {{ <{uri}> ?predicate ?target . FILTER(?predicate IN ({predicates})) }} ORDER BY ?predicate ?target"""
        )
        issuer_uri = _value(root, "issuer")
        payload = {
            "norm_uri": uri,
            "identifier": _value(root, "identifier"),
            "number": number,
            "title": _value(root, "title"),
            "norm_type_uri": _value(root, "type"),
            "norm_type_name": norm_type.title(),
            "issuer_uri": issuer_uri,
            "issuer_name": "",
            "publish_date": _value(root, "publish"),
            "promulgation_date": _value(root, "promulgation"),
            "latest_version_uri": latest[0]["version_uri"],
            "latest_version_date": latest[0]["version_date"],
            "scope_tags": subscription.scope_tags,
            "versions": normalized_versions,
            "relations": [
                {
                    "relation_type": RELATIONS[
                        _value(r, "predicate").rsplit("#", 1)[-1]
                    ],
                    "target_uri": _value(r, "target"),
                }
                for r in relations
            ],
        }
        return ConnectorRecord(
            external_id=uri,
            kind="bcn_legal_norm",
            canonical_key=f"{norm_type}:{number}",
            title=payload["title"],
            source_url=uri,
            payload=payload,
            published_at=None,
            metadata={"subscription_id": subscription.id, "starter_corpus": True},
        )

    def fetch(self, sync_state):
        records = [
            self._norm(item)
            for item in self.source.legal_norm_subscriptions.filter(
                active=True
            ).order_by("norm_type", "number")
        ]
        return ConnectorBatch(
            records=records,
            authoritative_full_snapshot=False,
            metadata={"corpus": "starter corpus / no exhaustivo"},
        )
