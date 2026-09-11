"""Strict ILCD/EPD detail contract, verified against official A1 and A2 XML.

Only explicit A1-A3 amounts are published. No module sums or unit conversions.
External XML URIs are evidence, never network destinations.
"""
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse
from uuid import UUID

import requests
from defusedxml import ElementTree
from django.conf import settings

from ..downloads import KNOWLEDGE_USER_AGENT
from .okobaudat import A1, A2, ROOT, XML_LANG

NS = {"p": "http://lca.jrc.it/ILCD/Process", "c": "http://lca.jrc.it/ILCD/Common",
      "e": "http://www.iai.kit.edu/EPD/2013", "f": "http://lca.jrc.it/ILCD/Flow",
      "fp": "http://lca.jrc.it/ILCD/FlowProperty", "u": "http://lca.jrc.it/ILCD/UnitGroup"}
KINDS = {"processes": ("p", "processDataSet"), "flows": ("f", "flowDataSet"),
         "flowproperties": ("fp", "flowPropertyDataSet"), "unitgroups": ("u", "unitGroupDataSet")}
VERSION = re.compile(r"\d{2}\.\d{2}\.\d{3}\Z")
# These identities and labels were observed in the official fixtures, not inferred.
GWP = {"77e416eb-a363-4258-a04e-171d843a6460": ("EN 15804+A1", "GWP"),
       "6a37f984-a4b3-458a-a20a-64418c145fa2": ("EN 15804+A2", "GWP-total"),
       "5f635281-343e-44fb-83df-1971b155e6b6": ("EN 15804+A2", "GWP-fossil"),
       "2356e1ab-0185-4db5-86e5-16de51c7485c": ("EN 15804+A2", "GWP-biogenic"),
       "4331bbdb-978a-490d-8707-eeb047f01a55": ("EN 15804+A2", "GWP-luluc")}


class DetailError(ValueError):
    """Only fixed, non-sensitive messages cross the service boundary."""


class UpstreamDeferred(DetailError):
    """Stop this batch; availability/rate limiting affects all identities."""


def dataset_url(kind, uuid, version=""):
    if kind not in KINDS or (version and not VERSION.fullmatch(version)):
        raise DetailError("Contrato de referencia incompatible.")
    try:
        uuid = str(UUID(str(uuid)))
    except (ValueError, TypeError, AttributeError):
        raise DetailError("Identidad de referencia invalida.") from None
    params = {"format": "XML"}
    if version:
        params["version"] = version
    return f"{ROOT}{kind}/{uuid}?{urlencode(params)}"


def validate_detail_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc != "www.oekobaudat.de"
            or parsed.fragment or not re.fullmatch(
                r"/OEKOBAU\.DAT/resource/(processes|flows|flowproperties|unitgroups)/[0-9a-f-]{36}", parsed.path)):
        raise DetailError("URL de detalle no permitida.")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    params = dict(pairs)
    if (len(pairs) != len(params) or set(params) - {"format", "version"} or params.get("format") != "XML"
            or ("version" in params and not VERSION.fullmatch(params["version"]))):
        raise DetailError("Parametros de detalle no permitidos.")
    try:
        UUID(parsed.path.rsplit("/", 1)[-1])
    except ValueError:
        raise DetailError("Identidad de detalle no permitida.") from None
    return url


def fetch_detail_bytes(url):
    validate_detail_url(url)
    maximum = getattr(settings, "KNOWLEDGE_OKOBAUDAT_MAX_BYTES", 12 * 1024 * 1024)
    for attempt in range(3):
        try:
            with requests.get(url, headers={"Accept": "application/xml", "User-Agent": KNOWLEDGE_USER_AGENT},
                              timeout=(10, 60), stream=True, allow_redirects=False) as response:
                # No redirect is necessary for the verified canonical XML endpoints.
                if 300 <= response.status_code < 400:
                    raise DetailError("Redireccion de detalle rechazada.")
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        header = response.headers.get("Retry-After", "")
                        delay = 2 ** attempt
                        if header.isdigit():
                            delay = int(header)
                        elif header:
                            try:
                                delay = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                            except (ValueError, TypeError, OverflowError):
                                pass
                        if delay > 30:
                            raise UpstreamDeferred("Upstream solicita reintentar mas tarde.")
                        time.sleep(max(1, delay))
                        continue
                    raise UpstreamDeferred("Upstream no disponible; lote pendiente de reintento.")
                if response.status_code != 200:
                    raise DetailError("Detalle upstream no disponible.")
                validate_detail_url(response.url)
                mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if mime not in {"application/xml", "text/xml"}:
                    raise DetailError("Content-Type de detalle incompatible.")
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > maximum:
                        raise DetailError("Detalle excede el limite de bytes.")
                return bytes(body)
        except requests.RequestException:
            if attempt == 2:
                raise DetailError("Conexion de detalle no disponible.") from None
            time.sleep(2 ** attempt)
    raise DetailError("Detalle upstream no disponible.")


def one(node, path):
    items = node.findall(path, NS)
    if len(items) != 1:
        raise DetailError("Referencia ausente o ambigua.")
    return items[0]


def text(node, path):
    value = (one(node, path).text or "").strip()
    if not value:
        raise DetailError("Valor requerido ausente.")
    return value


def number(value):
    try:
        result = Decimal(value)
        if not result.is_finite() or len(result.as_tuple().digits) > 60 or abs(result.adjusted()) > 100:
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError, TypeError):
        raise DetailError("Valor numerico incompatible.") from None


def document(body, kind, uuid, version=""):
    try:
        root = ElementTree.fromstring(body, forbid_dtd=True)
    except Exception:
        raise DetailError("XML de detalle invalido o inseguro.") from None
    prefix, tag = KINDS[kind]
    if root.tag != f"{{{NS[prefix]}}}{tag}" or root.get("version") != "1.1":
        raise DetailError("Formato ILCD incompatible.")
    actual_uuid = text(root, ".//c:UUID")
    actual_version = text(root, f"{prefix}:administrativeInformation/{prefix}:publicationAndOwnership/c:dataSetVersion")
    if actual_uuid.lower() != str(uuid).lower() or not VERSION.fullmatch(actual_version) or (version and actual_version != version):
        raise DetailError("UUID o version del detalle no corresponde.")
    return root


def reference(node):
    uuid, version = node.get("refObjectId", ""), node.get("version", "")
    dataset_url("flows", uuid, version)  # validates identifiers, never follows uri
    uri_ids = re.findall(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", node.get("uri", ""))
    if any(value.lower() != uuid.lower() for value in uri_ids):
        raise DetailError("Identidades de referencia contradictorias.")
    return uuid.lower(), version


def description(node):
    rows = node.findall("c:shortDescription", NS)
    for lang in ("en", "de", None):
        values = {(row.text or "").strip() for row in rows if lang is None or row.get(XML_LANG) == lang}
        values.discard("")
        if len(values) > 1:
            raise DetailError("Descripcion upstream contradictoria.")
        if values:
            return values.pop()
    raise DetailError("Descripcion upstream ausente.")


def parse_profile(body, uuid, version, resolve):
    """resolve(kind, uuid, version) supplies immutable observed XML dependencies."""
    root = document(body, "processes", uuid, version)
    systems = {n.get("refObjectId", "").lower() for n in root.findall(
        "p:modellingAndValidation/p:complianceDeclarations/p:compliance/c:referenceToComplianceSystem", NS)}
    standards = {label for ident, label in ((A1, "EN 15804+A1"), (A2, "EN 15804+A2")) if ident in systems}
    if len(standards) > 1:
        raise DetailError("Estandares contradictorios.")
    standard = next(iter(standards), "unknown")
    quantitative = one(root, "p:processInformation/p:quantitativeReference")
    if quantitative.get("type") not in (None, "Reference flow(s)"):
        raise DetailError("Tipo de referencia no soportado.")
    internal = text(quantitative, "p:referenceToReferenceFlow")
    exchanges = root.findall("p:exchanges/p:exchange", NS)
    matches = [n for n in exchanges if n.get("dataSetInternalID") == internal]
    if len(matches) != 1:
        raise DetailError("Flujo de referencia ambiguo.")
    exchange = matches[0]
    amounts = exchange.findall("p:resultingAmount", NS)
    amount = number(text(exchange, "p:resultingAmount" if amounts else "p:meanAmount"))
    flow_id, flow_version = reference(one(exchange, "p:referenceToFlowDataSet"))
    flow = document(resolve("flows", flow_id, flow_version), "flows", flow_id, flow_version)
    property_id = text(flow, "f:flowInformation/f:quantitativeReference/f:referenceToReferenceFlowProperty")
    properties = [n for n in flow.findall("f:flowProperties/f:flowProperty", NS) if n.get("dataSetInternalID") == property_id]
    if len(properties) != 1:
        raise DetailError("Propiedad de referencia ambigua.")
    prop = properties[0]
    factor = number(text(prop, "f:meanValue"))
    prop_id, prop_version = reference(one(prop, "f:referenceToFlowPropertyDataSet"))
    prop_root = document(resolve("flowproperties", prop_id, prop_version), "flowproperties", prop_id, prop_version)
    unit_id, unit_version = reference(one(prop_root, "fp:flowPropertiesInformation/fp:quantitativeReference/fp:referenceToReferenceUnitGroup"))
    unit_root = document(resolve("unitgroups", unit_id, unit_version), "unitgroups", unit_id, unit_version)
    unit_internal = text(unit_root, "u:unitGroupInformation/u:quantitativeReference/u:referenceToReferenceUnit")
    units = [n for n in unit_root.findall("u:units/u:unit", NS) if n.get("dataSetInternalID") == unit_internal]
    if len(units) != 1 or number(text(units[0], "u:meanValue")) != 1:
        raise DetailError("Unidad de referencia incompatible.")
    unit = text(units[0], "u:name")
    if amount <= 0 or factor <= 0:
        raise DetailError("Cantidad declarada no positiva.")
    indicators = []
    seen = set()
    for node in exchanges + root.findall("p:LCIAResults/p:LCIAResult", NS):
        values = node.findall("c:other/e:amount", NS)
        for value in values:
            module = value.get(f"{{{NS['e']}}}module", "")
            if not re.fullmatch(r"(?:[ABC][1-7]|D)(?:-(?:[ABC][1-7]|D))?", module):
                raise DetailError("Modulo ambiental ausente o ambiguo.")
        selected = [n for n in values if n.get(f"{{{NS['e']}}}module") == "A1-A3"]
        if not selected:
            continue
        if len(selected) != 1 or selected[0].get(f"{{{NS['e']}}}scenario"):
            raise DetailError("Modulo A1-A3 ambiguo.")
        kind = "flow" if node.tag == f"{{{NS['p']}}}exchange" else "lcia_method"
        ref = one(node, "p:referenceToFlowDataSet" if kind == "flow" else "p:referenceToLCIAMethodDataSet")
        ident, ref_version = reference(ref)
        name = description(ref)
        code = ""
        if ident in GWP:
            expected, code = GWP[ident]
            if standard != expected or f"({code})" not in name:
                raise DetailError("Indicador GWP incompatible con estandar o identidad.")
        else:
            # Preserve unknown indicators under their upstream UUID, with no semantic inference.
            code = ident
        unit_ref = one(node, "c:other/e:referenceToUnitGroupDataSet")
        indicator_unit_id, indicator_unit_version = reference(unit_ref)
        indicator_unit = description(unit_ref)
        key = (kind, ident)
        if key in seen:
            raise DetailError("Indicador A1-A3 duplicado.")
        seen.add(key)
        indicators.append({"upstream_uuid": ident, "upstream_version": ref_version, "indicator_kind": kind,
                           "name": name, "code": code, "module": "A1-A3", "value": str(number(selected[0].text)),
                           "unit": indicator_unit, "unit_uuid": indicator_unit_id, "unit_version": indicator_unit_version})
    if not indicators:
        raise DetailError("Detalle sin indicadores A1-A3 explicitos.")
    with localcontext() as context:
        context.prec = 120
        declared_amount = str(amount * factor)
    return {"standard": standard, "declared_amount": declared_amount, "declared_unit": unit,
            "reference_metadata": {"exchange_id": internal, "exchange_amount": str(amount), "flow_property_amount": str(factor),
                                   "flow_uuid": flow_id, "flow_property_uuid": prop_id, "unit_group_uuid": unit_id},
            "indicators": sorted(indicators, key=lambda n: (n["indicator_kind"], n["upstream_uuid"]))}
