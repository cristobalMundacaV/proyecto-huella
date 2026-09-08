import re
from urllib.parse import urljoin,urlparse

from bs4 import BeautifulSoup

from .base import ConnectorBatch,ConnectorRecord,EnvironmentalConnector
from .http import fetch_html,validate_public_url

IDE_HOSTS={"ide.mma.gob.cl"};IDE_PATHS=("/sinia/catalog","/centro-de-descargas","/servicios-de-interoperabilidad")
CATALOG_URL="https://ide.mma.gob.cl/sinia/catalog";DOWNLOADS_URL="https://ide.mma.gob.cl/centro-de-descargas";INTEROP_URL="https://ide.mma.gob.cl/servicios-de-interoperabilidad"

def validate_ide_url(url):return validate_public_url(url,IDE_HOSTS,IDE_PATHS)
def _text(node):return " ".join(node.get_text(" ",strip=True).split()) if node else ""
def _slug(value):return re.sub(r"[^a-z0-9]+","-",value.lower()).strip("-")

def parse_catalog_index(html,page_url=CATALOG_URL):
    soup=BeautifulSoup(html,"html.parser");found={}
    for anchor in soup.select("a[href]"):
        url=urljoin(page_url,anchor["href"]);match=re.search(r"/sinia/catalog/(\d+)(?:/|$)",url)
        if match and _text(anchor):found[match.group(1)]={"index_key":match.group(1),"title":_text(anchor),"metadata_url":url}
    return [found[key] for key in sorted(found,key=int)]

LABEL_MAP={"Identificador de Archivo":"dataset_key","Título del recurso":"title","Resumen del recurso":"summary","Nombre de la Organización":"organization_name","Rol":"role_raw","Rol de la organización":"role_raw","Estado":"status_raw","Tipo de Recurso":"resource_type_raw","Idioma de los Metadatos":"language_raw","Idioma del recurso":"language_raw","Estándar de Metadatos":"metadata_standard","Nombre del Estándar":"metadata_standard","Fecha de Metadatos":"metadata_date","Fecha del metadato":"metadata_date","Fecha de Recurso":"resource_date","Tipo de Geometría":"geometry_type_raw","Número de Entidades":"feature_count","Tamaño en MB":"size_raw","Colección de palabras claves":"keywords","Categoría temática":"categories","Clasificación":"categories","Longitud Oeste":"bbox_west","Longitud Este":"bbox_east","Latitud Sur":"bbox_south","Latitud Norte":"bbox_north","Coordenadas Oeste":"bbox_west","Coordenadas Este":"bbox_east","Coordenadas Sur":"bbox_south","Coordenadas Norte":"bbox_north"}
def parse_dataset_detail(html,index_item):
    soup=BeautifulSoup(html,"html.parser");values={};unknown={}
    for label_node in soup.select("div.col-span-1"):
        value_node=label_node.find_next_sibling("div");label=_text(label_node).rstrip(":");value=_text(value_node)
        if not value:continue
        key=LABEL_MAP.get(label)
        if key:values[key]=value
        else:unknown[label]=value
    key=values.get("dataset_key") or index_item["index_key"]
    if not key or not values.get("title",index_item.get("title")):raise ValueError("Metadata IDE incompleta.")
    summary=values.get("summary","")
    def summary_match(label):
        found=re.search(label+r"\s*:\s*([^|]+)",summary,re.I);return found.group(1).strip() if found else ""
    feature_raw=values.get("feature_count") or summary_match("N.mero de Entidades")
    try:feature_count=int(re.sub(r"\D","",feature_raw)) if feature_raw else None
    except ValueError:feature_count=None
    return {"dataset_key":key,"title":values.get("title",index_item["title"]),"summary":summary,"metadata_standard":values.get("metadata_standard",""),"metadata_date":values.get("metadata_date"),"resource_date":values.get("resource_date"),"organization_name":values.get("organization_name",""),"role_raw":values.get("role_raw",""),"status_raw":values.get("status_raw",""),"resource_type_raw":values.get("resource_type_raw",""),"language_raw":values.get("language_raw",""),"geometry_type_raw":values.get("geometry_type_raw") or summary_match("Tipo de Geometr.a"),"feature_count":feature_count,"size_raw":values.get("size_raw") or summary_match("Tama.o en MB"),"keywords":[item.strip() for item in values.get("keywords","").split(",") if item.strip()],"categories":[item.strip() for item in values.get("categories","").split(",") if item.strip()],"bbox_west":values.get("bbox_west"),"bbox_east":values.get("bbox_east"),"bbox_south":values.get("bbox_south"),"bbox_north":values.get("bbox_north"),"metadata_url":index_item["metadata_url"],"upstream_fields":unknown}

def parse_downloads(html,page_url=DOWNLOADS_URL):
    soup=BeautifulSoup(html,"html.parser");found={}
    for anchor in soup.select("a[href]"):
        url=urljoin(page_url,anchor["href"]);match=re.search(r"/centro-de-descargas/(\d+)(?:/|$)",url)
        if not match:continue
        container=anchor.find_parent(["article","li","div"]);text=_text(container)
        size_match=re.search(r"(\d+(?:[.,]\d+)?\s*(?:KB|MB|GB))",text,re.I);title=text
        if size_match:title=text[:size_match.start()].strip(" -")
        if not title or title.lower()=="descargar":
            previous=anchor.find_previous(string=re.compile(r"\S"));title=" ".join(str(previous or "").split()).split(" - ")[0]
        heading=anchor.find_previous(["h2","h3","h4"]);category=_text(heading)
        found[match.group(1)]={"resource_key":match.group(1),"title":title,"category_raw":category,"declared_size_raw":size_match.group(1) if size_match else "","download_url":url}
    return [found[key] for key in sorted(found,key=int)]

def parse_interoperability(html,page_url=INTEROP_URL):
    soup=BeautifulSoup(html,"html.parser");services=[]
    for anchor in soup.select("a[href]"):
        text=_text(anchor);url=urljoin(page_url,anchor["href"])
        if re.search(r"\b(?:WMS|WFS)\b",text+" "+url,re.I):services.append({"title":text,"url":url})
    unique={item["url"]:item for item in services}
    return [unique[key] for key in sorted(unique)]

class IdeMmaCatalogConnector(EnvironmentalConnector):
    def fetch(self,sync_state):
        catalog_html,_,catalog_url=fetch_html(CATALOG_URL,validate_ide_url);records=[]
        for item in parse_catalog_index(catalog_html,catalog_url):
            html,_,final_url=fetch_html(item["metadata_url"],validate_ide_url);item["metadata_url"]=final_url;payload=parse_dataset_detail(html,item)
            key=str(payload["dataset_key"]);records.append(ConnectorRecord(external_id=f"ide:dataset:{key}",canonical_key=key,kind="ide_mma_dataset",title=payload["title"],source_url=final_url,payload=payload))
        downloads_html,_,downloads_url=fetch_html(DOWNLOADS_URL,validate_ide_url)
        for payload in parse_downloads(downloads_html,downloads_url):
            key=str(payload["resource_key"]);records.append(ConnectorRecord(external_id=f"ide:download:{key}",canonical_key=key,kind="ide_mma_download_resource",title=payload["title"],source_url=payload["download_url"],payload=payload))
        interop_html,_,_=fetch_html(INTEROP_URL,validate_ide_url);services=parse_interoperability(interop_html)
        metadata={"interoperability_available":bool(services),"external_capability_limited":not bool(services),"available_service_count":len(services),"available_services":services,"usage_context":"referential","information_update_context":"constant_update","authoritative_for_compliance":False}
        return ConnectorBatch(records=records,authoritative_full_snapshot=True,metadata=metadata)
