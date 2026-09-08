import re
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector
from .http import fetch_html, validate_sea_url

SEA_SEARCH_URL = "https://seia.sea.gob.cl/busqueda/buscarProyectoResumen.php"


def _text(value): return " ".join(value.get_text(" ", strip=True).split()) if value else ""


def _date(value):
    value = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(value[:10], fmt).date().isoformat()
        except ValueError: pass
    return ""


def _project_key(url, row):
    for attr in ("data-project-key", "data-expediente-id", "data-id"):
        if row.get(attr): return str(row[attr]).strip()
    parsed = urlparse(url); query = parse_qs(parsed.query)
    for key in ("id_expediente", "modo", "id", "folio"):
        if query.get(key) and query[key][0].strip(): return query[key][0].strip()
    return ""


def parse_sea_search_results(html, base_url=SEA_SEARCH_URL):
    soup = BeautifulSoup(html, "html.parser"); results = []
    for row in soup.select("tr[data-project-key], tr[data-expediente-id], tr[data-id], table tbody tr"):
        link = row.find("a", href=True)
        cells = [_text(cell) for cell in row.find_all("td")]
        if not link or not cells: continue
        url = urljoin(base_url, link["href"]); key = _project_key(url, row)
        if not key: continue
        values = {str(cell.get("data-label", "")).strip().lower(): _text(cell) for cell in row.find_all("td") if cell.get("data-label")}
        results.append({"project_key": key, "folio": values.get("folio", ""), "name": values.get("nombre", _text(link)), "holder_name": values.get("titular", ""), "region": values.get("region", ""), "presentation_type": values.get("tipo", values.get("tipo de presentacion", "")), "status": values.get("estado", ""), "project_url": url})
    unique = {item["project_key"]: item for item in results}
    return [unique[key] for key in unique]


def discover_sea_projects(**filters):
    allowed = {"project_name": "nombre", "holder_name": "titular", "folio": "folio", "region": "selectRegion[]", "commune": "selectComuna[]", "presentation_type": "tipoPresentacion", "status": "projectStatus[]", "sector": "sectores_economicos[]"}
    unknown = set(filters) - set(allowed)
    if unknown: raise ValueError("Filtros SEA no permitidos.")
    payload = {allowed[key]: value for key, value in filters.items() if value not in (None, "")}
    payload.setdefault("tipoPresentacion", "Ambos")
    html, _, final_url = fetch_html(SEA_SEARCH_URL, validate_sea_url, urlencode(payload, doseq=True).encode())
    return parse_sea_search_results(html, final_url)


SEA_LABELS = {
    "folio": "folio", "nombre del proyecto": "name", "nombre": "name", "titular": "holder_name", "region": "region", "comuna": "communes_raw",
    "tipo de presentacion": "presentation_type_raw", "estado": "status_raw", "sector productivo": "sector_raw", "tipologia": "project_type_raw",
    "razon de ingreso": "admission_reason_raw", "fecha de presentacion": "submission_date_raw", "fecha de calificacion": "qualification_date_raw",
}


def _normalized_label(value):
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().rstrip(":").split())


def parse_sea_project(html, subscription):
    soup = BeautifulSoup(html, "html.parser"); values = {}
    for row in soup.select("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            key = SEA_LABELS.get(_normalized_label(_text(cells[0])))
            if key: values[key] = _text(cells[1])
    for term in soup.select("dt"):
        sibling = term.find_next_sibling("dd"); key = SEA_LABELS.get(_normalized_label(_text(term)))
        if sibling and key: values[key] = _text(sibling)
    if not values.get("name"):
        raise ValueError(f"SEA {subscription.project_key}: estructura esencial ausente.")
    rcas = []
    for anchor in soup.find_all("a", href=True):
        title = _text(anchor)
        if not re.search(r"\bRCA\b|Resoluci[oó]n de Calificaci[oó]n Ambiental", title, re.I): continue
        url = urljoin(subscription.project_url, anchor["href"])
        match = re.search(r"(?:RCA|Resoluci[oó]n)\s*(?:N[°ºo.]?\s*)?([^,;]+)", title, re.I)
        document_key = str(anchor.get("data-document-id") or parse_qs(urlparse(url).query).get("id", [""])[0]).strip()
        if not document_key: document_key = url
        rcas.append({"document_key": document_key, "rca_number_raw": match.group(1).strip() if match else "", "title": title, "document_date": _date(anchor.get("data-date")), "qualification_result_raw": anchor.get("data-result", ""), "document_url": url, "metadata": {}})
    communes = [item.strip() for item in re.split(r"[,;]", values.pop("communes_raw", "")) if item.strip()]
    return {"project_key": subscription.project_key, "folio": values.get("folio", ""), "name": values["name"], "holder_name": values.get("holder_name", ""), "region": values.get("region", ""), "communes": communes, "presentation_type_raw": values.get("presentation_type_raw", ""), "status_raw": values.get("status_raw", ""), "sector_raw": values.get("sector_raw", ""), "project_type_raw": values.get("project_type_raw", ""), "admission_reason_raw": values.get("admission_reason_raw", ""), "submission_date": _date(values.get("submission_date_raw")), "qualification_date": _date(values.get("qualification_date_raw")), "project_url": subscription.project_url, "expediente_url": subscription.project_url, "rca_references": sorted(rcas, key=lambda item: item["document_key"])}


class SeaSeiaPublicConnector(EnvironmentalConnector):
    def fetch(self, sync_state):
        records = []
        for subscription in self.source.sea_project_subscriptions.filter(active=True).order_by("project_key"):
            html, digest, final_url = fetch_html(subscription.project_url, validate_sea_url)
            payload = parse_sea_project(html, subscription); payload["project_url"] = final_url; payload["expediente_url"] = final_url
            records.append(ConnectorRecord(external_id=f"project:{subscription.project_key}", canonical_key=subscription.project_key, kind="sea_project", title=payload["name"], source_url=final_url, payload=payload, metadata={"upstream_page_sha256": digest, "subscription_id": subscription.id}))
        return ConnectorBatch(records=records, authoritative_full_snapshot=False, metadata={"subscription_count": len(records)})
