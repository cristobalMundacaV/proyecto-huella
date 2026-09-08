import ipaddress
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings

from ..downloads import KNOWLEDGE_USER_AGENT
from ..geo_facts import normalize_simbio_layer
from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector

SIMBIO_ROOT="https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/"
SIMBIO_LAYER_MANIFEST=(
    ("SIMBIO_AP",0,"Áreas Protegidas"),("SIMBIO_AP",1,"Otras Designaciones"),("SIMBIO_AP",2,"Sitios Prioritarios"),("SIMBIO_AP",3,"Conservación Privada"),
    ("SIMBIO_HUMEDALES",0,"Inventario Nacional de Humedales"),("SIMBIO_HUMEDALES",1,"Humedales Urbanos Declarados"),
    ("SIMBIO_ECORREGIONES",0,"Ecorregiones Terrestres"),("SIMBIO_ECORREGIONES",2,"Ecorregiones Terrestres 2020"),
)

def validate_simbio_url(url):
    p=urlparse(str(url))
    try:ipaddress.ip_address(p.hostname or "")
    except ValueError:pass
    else:raise ValueError("Host ArcGIS no permitido.")
    if p.scheme!="https" or p.hostname!="arcgis.mma.gob.cl" or p.username or p.password or not p.path.startswith("/server/rest/services/SIMBIO/"):raise ValueError("URL ArcGIS SIMBIO no permitida.")
    lowered=p.path.lower()
    if any(token in lowered for token in ("addfeatures","updatefeatures","deletefeatures","applyedits","calculate","uploads")):raise ValueError("Operacion ArcGIS de escritura no permitida.")
    return str(url)

def fetch_arcgis_json(url,params=None):
    validate_simbio_url(url);maximum=getattr(settings,"KNOWLEDGE_ARCGIS_MAX_BYTES",5*1024*1024);current=url
    for _ in range(4):
        query={"f":"json",**(params or {})};response=requests.get(current,params=query,headers={"Accept":"application/json","User-Agent":KNOWLEDGE_USER_AGENT},timeout=(10,30),allow_redirects=False,stream=True)
        if response.is_redirect:
            current=urljoin(current,response.headers.get("Location",""));validate_simbio_url(current);response.close();continue
        response.raise_for_status();validate_simbio_url(response.url);content_type=(response.headers.get("Content-Type") or "").lower()
        if "json" not in content_type:response.close();raise ValueError("Content-Type ArcGIS no soportado.")
        response.raw.decode_content=True;body=response.raw.read(maximum+1);response.close()
        if len(body)>maximum:raise ValueError("Respuesta ArcGIS excede el limite.")
        data=requests.models.complexjson.loads(body)
        if data.get("error"):raise ValueError("ArcGIS devolvio un error.")
        return data
    raise ValueError("Demasiadas redirecciones ArcGIS.")

class SimbioArcgisConnector(EnvironmentalConnector):
    def fetch(self,sync_state):
        services={};records=[]
        for service_code,layer_id,expected_name in SIMBIO_LAYER_MANIFEST:
            service_url=f"{SIMBIO_ROOT}{service_code}/FeatureServer"
            if service_code not in services:services[service_code]=fetch_arcgis_json(service_url)
            service=services[service_code]
            listed=next((item for item in service.get("layers",[]) if item.get("id")==layer_id),None)
            if not listed or listed.get("name")!=expected_name or listed.get("type")!="Feature Layer":raise ValueError(f"Manifest SIMBIO incompatible para {service_code}:{layer_id}.")
            layer_url=f"{service_url}/{layer_id}";layer=fetch_arcgis_json(layer_url);layer.setdefault("id",layer_id)
            payload=normalize_simbio_layer(service_code,expected_name,service,layer,service_url,layer_url)
            key=f"simbio:{service_code}:{layer_id}";records.append(ConnectorRecord(external_id=key,canonical_key=key,kind="simbio_geo_layer",title=expected_name,source_url=layer_url,payload=payload))
        return ConnectorBatch(records=records,authoritative_full_snapshot=True,metadata={"manifest_layer_count":len(SIMBIO_LAYER_MANIFEST),"provider":"SIMBIO/MMA","read_only":True,"biodiversity_official_data_responsibility":"SBAP","responsibility_effective_date":"2026-02-02","interoperability_provider":"SIMBIO/MMA","biodiversity_data_responsibility_note":"La responsabilidad oficial de datos de biodiversidad corresponde a SBAP desde 2026-02-02; el proveedor de interoperabilidad consumido es SIMBIO/MMA."})
