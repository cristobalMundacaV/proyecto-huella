from datetime import date
from decimal import Decimal, InvalidOperation


def _date(value):
    try:return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:return None


def _decimal(value):
    try:return Decimal(str(value).replace(",",".")) if value not in (None,"") else None
    except InvalidOperation:return None


def model_payload(instance, expected):
    return {key:getattr(instance,key) for key in expected}


def normalize_arcgis_field(field):
    result={"name":field.get("name", ""),"alias":field.get("alias", ""),"type":field.get("type", ""),"nullable":field.get("nullable")}
    if field.get("domain") is not None:result["domain"]=field["domain"]
    return result


def normalize_simbio_layer(service_code, expected_name, service, layer, service_url, layer_url):
    if layer.get("id") is None or layer.get("name")!=expected_name or layer.get("type")!="Feature Layer":raise ValueError(f"Contrato SIMBIO incompatible para {service_code}:{layer.get('id')}.")
    advanced=layer.get("advancedQueryCapabilities") or {}
    formats=layer.get("supportedQueryFormats") or service.get("supportedQueryFormats") or ""
    payload={
        "service_code":service_code,"service_name":service.get("name") or service_code,"service_url":service_url,
        "layer_id":int(layer["id"]),"layer_name":layer["name"],"layer_url":layer_url,"geometry_type":layer.get("geometryType", ""),
        "spatial_reference_wkid":(layer.get("extent",{}).get("spatialReference",{}).get("latestWkid") or layer.get("extent",{}).get("spatialReference",{}).get("wkid") or service.get("spatialReference",{}).get("latestWkid") or service.get("spatialReference",{}).get("wkid")),
        "display_field":layer.get("displayField", ""),"object_id_field":layer.get("objectIdField", ""),"max_record_count":layer.get("maxRecordCount") or service.get("maxRecordCount"),
        "supports_pagination":bool(advanced.get("supportsPagination")),"supports_distance_query":bool(advanced.get("supportsQueryWithDistance")),
        "query_formats":sorted(item.strip() for item in formats.split(",") if item.strip()),
        "fields_schema":sorted((normalize_arcgis_field(item) for item in layer.get("fields",[])),key=lambda item:item["name"]),
        "service_item_id":service.get("serviceItemId", ""),
        "provider_metadata":{"provider":"SIMBIO/MMA","service_capabilities":sorted(item.strip() for item in service.get("capabilities","").split(",") if item.strip()),"layer_capabilities":sorted(item.strip() for item in layer.get("capabilities","").split(",") if item.strip())},
    }
    return payload


def build_simbio_layer_fact_payload(snapshot):
    payload=snapshot.raw_payload or {}
    if snapshot.source.codigo!="simbio" or snapshot.record_kind!="simbio_geo_layer":raise ValueError("Snapshot SIMBIO incompatible.")
    return {key:payload[key] for key in ("service_code","service_name","service_url","layer_id","layer_name","layer_url","geometry_type","spatial_reference_wkid","display_field","object_id_field","max_record_count","supports_pagination","supports_distance_query","query_formats","fields_schema","service_item_id","provider_metadata")}


def build_ide_dataset_fact_payload(snapshot):
    p=snapshot.raw_payload or {}
    if snapshot.source.codigo!="ide-mma" or snapshot.record_kind!="ide_mma_dataset" or not p.get("dataset_key") or not p.get("title") or not p.get("metadata_url"):raise ValueError("Dataset IDE MMA incompatible.")
    return {"dataset_key":p["dataset_key"],"title":p["title"],"summary":p.get("summary", ""),"metadata_standard":p.get("metadata_standard", ""),"metadata_date":_date(p.get("metadata_date")),"resource_date":_date(p.get("resource_date")),"organization_name":p.get("organization_name", ""),"role_raw":p.get("role_raw", ""),"status_raw":p.get("status_raw", ""),"resource_type_raw":p.get("resource_type_raw", ""),"language_raw":p.get("language_raw", ""),"geometry_type_raw":p.get("geometry_type_raw", ""),"feature_count":p.get("feature_count"),"size_raw":p.get("size_raw", ""),"keywords":p.get("keywords",[]),"categories":p.get("categories",[]),"bbox_west":_decimal(p.get("bbox_west")),"bbox_east":_decimal(p.get("bbox_east")),"bbox_south":_decimal(p.get("bbox_south")),"bbox_north":_decimal(p.get("bbox_north")),"metadata_url":p["metadata_url"]}


def build_ide_download_fact_payload(snapshot):
    p=snapshot.raw_payload or {}
    if snapshot.source.codigo!="ide-mma" or snapshot.record_kind!="ide_mma_download_resource" or not p.get("resource_key") or not p.get("title") or not p.get("download_url"):raise ValueError("Descarga IDE MMA incompatible.")
    return {key:p.get(key,"") for key in ("resource_key","title","category_raw","declared_size_raw","download_url")}
