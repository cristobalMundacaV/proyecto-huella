import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector
from .http import fetch_html, validate_snifa_url

SNIFA_DATASETS_URL = "https://snifa.sma.gob.cl/DatosAbiertos"


def _text(value):
    return " ".join(value.get_text(" ", strip=True).split()) if hasattr(value, "get_text") else " ".join(str(value or "").split())


def _slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def parse_snifa_dataset_catalog(html, page_url=SNIFA_DATASETS_URL):
    soup = BeautifulSoup(html, "html.parser"); found = {}
    for heading in soup.select("h3, h4, h5"):
        title = _text(heading)
        if not title: continue
        anchor = heading.find_parent("a", href=True) or heading.find_previous("a", href=True)
        container = heading.parent
        description_node = container.find("p") if container else None
        if not anchor or not description_node: continue
        url = urljoin(page_url, anchor.get("href"))
        code = _slug(title)
        if code and code not in found:
            found[code] = {"dataset_code": code, "title": title, "description": _text(description_node), "source_url": url, "publisher": "Superintendencia del Medio Ambiente"}
    if not found:
        raise ValueError("Indice SNIFA sin datasets reconocibles.")
    return [found[key] for key in sorted(found)]


LABELS = {
    "expediente": "expediente", "unidad fiscalizable": "unit_name", "titular": "holder_name", "categoria": "category",
    "region": "region", "comuna": "commune", "estado": "status_raw", "fecha": "event_date_raw",
    "monto sancion": "sanction_amount_raw", "estado pago": "payment_status_raw", "id unidad fiscalizable": "unit_external_key",
}


def parse_snifa_reference(html, subscription):
    soup = BeautifulSoup(html, "html.parser"); values = {}; unknown = {}
    for row in soup.select("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label, value = _text(cells[0]).rstrip(":"), _text(cells[1])
            key = LABELS.get(_slug(label).replace("-", " "))
            (values if key else unknown)[key or label] = value
    for term in soup.select("dt"):
        value_node = term.find_next_sibling("dd")
        if value_node:
            label, value = _text(term).rstrip(":"), _text(value_node)
            key = LABELS.get(_slug(label).replace("-", " "))
            (values if key else unknown)[key or label] = value
    if not values:
        raise ValueError(f"SNIFA {subscription.external_key}: estructura requerida ausente.")
    instruments = []
    for anchor in soup.find_all("a", href=True):
        title = _text(anchor)
        match = re.search(r"\bRCA\s*(?:N[°ºo.]?\s*)?([^,;]+)", title, re.I)
        if match:
            instruments.append({"type": "RCA", "number_raw": match.group(1).strip(), "source_url": urljoin(subscription.source_url, anchor["href"]), "title": title})
    return {"reference_type": subscription.reference_type, "external_key": subscription.external_key, **values, "instrument_references": sorted(instruments, key=lambda item: (item["number_raw"], item["source_url"])), "source_url": subscription.source_url, "upstream_fields": unknown}


class SnifaPublicConnector(EnvironmentalConnector):
    def fetch(self, sync_state):
        catalog_html, catalog_sha, catalog_url = fetch_html(SNIFA_DATASETS_URL, validate_snifa_url)
        records = [ConnectorRecord(external_id=f"dataset:{item['dataset_code']}", canonical_key=item["dataset_code"], kind="snifa_open_dataset", title=item["title"], source_url=item["source_url"], payload=item, metadata={"upstream_page_sha256": catalog_sha}) for item in parse_snifa_dataset_catalog(catalog_html, catalog_url)]
        for subscription in self.source.snifa_reference_subscriptions.filter(active=True).order_by("reference_type", "external_key"):
            html, digest, final_url = fetch_html(subscription.source_url, validate_snifa_url)
            payload = parse_snifa_reference(html, subscription); payload["source_url"] = final_url
            records.append(ConnectorRecord(external_id=f"{subscription.reference_type}:{subscription.external_key}", canonical_key=f"{subscription.reference_type}:{subscription.external_key}", kind="snifa_regulatory_reference", title=subscription.label, source_url=final_url, payload=payload, metadata={"upstream_page_sha256": digest, "subscription_id": subscription.id}))
        return ConnectorBatch(records=records, authoritative_full_snapshot=False, metadata={"catalog_url": catalog_url, "subscription_count": self.source.snifa_reference_subscriptions.filter(active=True).count()})
