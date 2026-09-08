import hashlib
import json
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.knowledge.connectors.simbio import SIMBIO_LAYER_MANIFEST
from apps.knowledge.models import EnvironmentalSource, SimbioGeoLayerFact
from apps.knowledge.services import source_freshness

CONTRACT = "territorial-observation-1"
QUERY_CONTRACT = {
    "coordinate_srid": 4326,
    "bands_km": [1, 5],
    "spatial_relation": "intersects",
    "geometry_type": "esriGeometryPoint",
    "return_geometry": False,
    "ecoregions_mode": "intersects_only",
}
BANDS = ("intersects", "within_1km", "within_5km")


def canonical_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def decimal_text(value):
    return format(Decimal(str(value)).normalize(), "f")


def build_geolocation_snapshot(location):
    return {
        "geolocation_revision_id": location.id,
        "revision": location.revision,
        "latitude": decimal_text(location.latitude),
        "longitude": decimal_text(location.longitude),
        "srid": location.srid,
        "capture_method": location.capture_method,
        "accuracy_m": decimal_text(location.accuracy_m) if location.accuracy_m is not None else None,
        "source_reference": location.source_reference,
        "coordinate_hash": location.coordinate_hash,
    }


def build_simbio_source_snapshot(source=None):
    source = source or EnvironmentalSource.objects.select_related("sync_state").get(codigo="simbio")
    state = source.sync_state
    return {
        "source_id": source.id,
        "source_code": source.codigo,
        "source_name": source.nombre,
        "connector_key": source.connector_key,
        "access_type": source.tipo_acceso,
        "state": state.estado,
        "source_freshness": source_freshness(source),
        "last_successful_sync_at": state.last_successful_sync_at.isoformat() if state.last_successful_sync_at else None,
        "last_checksum": state.last_checksum,
        "provider": "SIMBIO/MMA",
        "interoperability_provider": state.metadata.get("interoperability_provider", "SIMBIO/MMA"),
        "biodiversity_official_data_responsibility": state.metadata.get("biodiversity_official_data_responsibility", ""),
        "responsibility_effective_date": state.metadata.get("responsibility_effective_date", ""),
        "biodiversity_data_responsibility_note": state.metadata.get("biodiversity_data_responsibility_note", ""),
    }


def current_simbio_facts():
    return list(SimbioGeoLayerFact.objects.filter(
        snapshot__current_for__current_snapshot=models.F("snapshot"), snapshot__source__codigo="simbio"
    ).select_related("snapshot").order_by("service_code", "layer_id"))


def build_layer_catalog_snapshot(facts=None):
    facts = current_simbio_facts() if facts is None else list(facts)
    expected = {(service, layer_id, name) for service, layer_id, name in SIMBIO_LAYER_MANIFEST}
    actual = {(fact.service_code, fact.layer_id, fact.layer_name) for fact in facts}
    if len(facts) != len(expected) or actual != expected:
        raise ValidationError("El catalogo SIMBIO current no contiene exactamente las ocho capas gobernadas.")
    return [{
        "fact_id": fact.id, "snapshot_id": fact.snapshot_id, "content_hash": fact.snapshot.content_hash,
        "service_code": fact.service_code, "layer_id": fact.layer_id, "layer_name": fact.layer_name,
        "layer_url": fact.layer_url, "geometry_type": fact.geometry_type, "display_field": fact.display_field,
        "object_id_field": fact.object_id_field, "supports_distance_query": fact.supports_distance_query,
    } for fact in facts]


def compute_feature_hash(layer, feature):
    return canonical_hash({
        "service_code": layer["service_code"], "layer_id": layer["layer_id"],
        "layer_snapshot_content_hash": layer["content_hash"], "object_id": feature["object_id"],
        "proximity_band": feature["proximity_band"], "attributes": feature["attributes"],
    })


def build_results_snapshot(layer_catalog, raw_layers):
    catalog = {(item["service_code"], item["layer_id"]): item for item in layer_catalog}
    if len(raw_layers) != len(catalog): raise ValidationError("Resultados territoriales incompletos.")
    normalized = []
    seen_layers = set()
    for raw in raw_layers:
        key = (raw.get("service_code"), raw.get("layer_id")); layer = catalog.get(key)
        if not layer or key in seen_layers or raw.get("layer_name") != layer["layer_name"]: raise ValidationError("Resultado de capa incompatible.")
        seen_layers.add(key); mode = "intersects" if key[0] == "SIMBIO_ECORREGIONES" else "proximity"
        if raw.get("query_mode") != mode: raise ValidationError("Modo de consulta territorial incompatible.")
        features = []
        for feature in raw.get("features", []):
            if set(feature) != {"object_id", "display_name", "proximity_band", "attributes", "feature_hash"}: raise ValidationError("Contrato de feature territorial incompatible.")
            band = feature["proximity_band"]
            if band not in BANDS or mode == "intersects" and band != "intersects": raise ValidationError("Banda territorial invalida.")
            attrs = {str(k): v for k, v in sorted(feature["attributes"].items())}
            if any(str(k).lower() in {"geometry", "rings"} for k in attrs): raise ValidationError("No se permite persistir geometria.")
            oid_field = layer["object_id_field"]
            if oid_field and oid_field in attrs and attrs[oid_field] != feature["object_id"]: raise ValidationError("Object ID inconsistente.")
            item = {**feature, "attributes": attrs}
            if item["feature_hash"] != compute_feature_hash(layer, item): raise ValidationError("Feature hash invalido.")
            features.append(item)
        features.sort(key=lambda item: (BANDS.index(item["proximity_band"]), item["object_id"]))
        normalized.append({"service_code": key[0], "layer_id": key[1], "layer_name": layer["layer_name"], "query_mode": mode, "features": features})
    normalized.sort(key=lambda item: (item["service_code"], item["layer_id"]))
    return {"layers": normalized}


def build_territorial_summary(results):
    totals = {band: 0 for band in BANDS}; breakdown = []; eco = 0
    for layer in results["layers"]:
        counts = {band: sum(f["proximity_band"] == band for f in layer["features"]) for band in BANDS}
        for band in BANDS: totals[band] += counts[band]
        if layer["query_mode"] == "intersects": eco += counts["intersects"]
        breakdown.append({"service_code": layer["service_code"], "layer_id": layer["layer_id"], **counts, "total": sum(counts.values())})
    return {"layer_count": len(results["layers"]), "feature_count": sum(totals.values()), "intersects_count": totals["intersects"], "within_1km_count": totals["within_1km"], "within_5km_count": totals["within_5km"], "ecoregion_intersections": eco, "layers": breakdown}


def build_observation_basis_payload(contract, geolocation, source, catalog):
    # The publication timestamp is retained in the frozen source snapshot for
    # provenance, but is deliberately excluded from semantic identity.
    semantic_source = {key: value for key, value in source.items() if key != "last_successful_sync_at"}
    return {"observation_contract_version": contract, "geolocation_snapshot": geolocation, "source_snapshot": semantic_source, "layer_catalog_snapshot": catalog, "query_contract": QUERY_CONTRACT}

def compute_basis_hash(contract, geolocation, source, catalog): return canonical_hash(build_observation_basis_payload(contract, geolocation, source, catalog))
def compute_result_hash(basis_hash, results, summary): return canonical_hash({"basis_hash": basis_hash, "results_snapshot": results, "summary_snapshot": summary})
