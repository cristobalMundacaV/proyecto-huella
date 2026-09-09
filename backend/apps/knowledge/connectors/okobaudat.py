import ipaddress
import re
from urllib.parse import urljoin, urlparse

import requests
from defusedxml import ElementTree
from django.conf import settings

from ..bootstrap import OKOBAUDAT_TERMS
from ..downloads import KNOWLEDGE_USER_AGENT
from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector

ROOT="https://www.oekobaudat.de/OEKOBAU.DAT/resource/"
A1="b00f9ec0-7874-11e3-981f-0800200c9a66"
A2="c0016b33-8cf7-415c-ac6e-deba0d21440d"
NS={"s":"http://www.ilcd-network.org/ILCD/ServiceAPI","p":"http://www.ilcd-network.org/ILCD/ServiceAPI/Process","p2":"http://www.ilcd-network.org/ILCD/ServiceAPI/v2/Process"}
XML_LANG="{http://www.w3.org/XML/1998/namespace}lang"
XLINK="{http://www.w3.org/1999/xlink}href"

def validate_okobaudat_url(url):
    parsed=urlparse(str(url));host=(parsed.hostname or "").lower()
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise ValueError("Host Oekobaudat no permitido.")
    if parsed.scheme!="https" or host not in {"www.oekobaudat.de","oekobaudat.de"} or parsed.username or parsed.password or not parsed.path.startswith("/OEKOBAU.DAT/resource/"):
        raise ValueError("URL Oekobaudat no permitida.")
    return str(url)

def fetch_okobaudat_xml(url):
    current=validate_okobaudat_url(url);maximum=getattr(settings,"KNOWLEDGE_OKOBAUDAT_MAX_BYTES",12*1024*1024)
    for _ in range(4):
        response=None
        for attempt in range(3):
            try:response=requests.get(current,headers={"Accept":"application/xml","User-Agent":KNOWLEDGE_USER_AGENT},timeout=(10,60),allow_redirects=False,stream=True);break
            except requests.RequestException as exc:
                if attempt==2:raise ValueError("Oekobaudat no disponible despues de reintentos.") from exc
        if response.is_redirect:
            target=urljoin(current,response.headers.get("Location",""));validate_okobaudat_url(target)
            if urlparse(current).hostname=="www.oekobaudat.de" and urlparse(target).hostname!="www.oekobaudat.de":raise ValueError("Redireccion Oekobaudat no canonica.")
            current=target;response.close();continue
        response.raise_for_status();validate_okobaudat_url(response.url)
        if "xml" not in (response.headers.get("Content-Type") or "").lower():response.close();raise ValueError("Content-Type Oekobaudat no soportado.")
        response.raw.decode_content=True;body=response.raw.read(maximum+1);response.close()
        if len(body)>maximum:raise ValueError("Respuesta Oekobaudat excede el limite.")
        try:root=ElementTree.fromstring(body)
        except Exception as exc:raise ValueError("XML Oekobaudat invalido.") from exc
        return root,current
    raise ValueError("Demasiadas redirecciones Oekobaudat.")

def _text(node,path,default=""):
    found=node.find(path,NS);return " ".join((found.text or "").split()) if found is not None else default

def parse_datastocks(root):
    result=[]
    for item in root.findall("s:dataStock",NS):
        uuid=_text(item,"s:uuid");short=_text(item,"s:shortName")
        if not uuid or not short:raise ValueError("Datastock Oekobaudat sin identidad.")
        names={node.get(XML_LANG,"und"):" ".join((node.text or "").split()) for node in item.findall("s:name",NS) if (node.text or "").strip()}
        descriptions={node.get(XML_LANG,"und"):" ".join((node.text or "").split()) for node in item.findall("s:description",NS) if (node.text or "").strip()}
        result.append({"datastock_uuid":uuid.lower(),"short_name":short,"display_name":names.get("en") or names.get("de") or next(iter(names.values()),short),"description":descriptions.get("en") or descriptions.get("de") or next(iter(descriptions.values()),""),"release_label":short,"version_label":"","source_url":f"{ROOT}datastocks/{uuid}/","upstream_metadata":{"root":item.get("{http://www.ilcd-network.org/ILCD/ServiceAPI}root")=="true","names":names,"descriptions":descriptions}})
    if not result:raise ValueError("Catalogo de datastocks Oekobaudat vacio.")
    return sorted(result,key=lambda row:row["datastock_uuid"])

def select_release(stocks):
    excluded=[];candidates=[]
    pattern=re.compile(r"^OBD_(\d{4})_([IVX]+)$",re.I);roman={"I":1,"II":2,"III":3,"IV":4}
    for stock in stocks:
        short=stock["short_name"];match=pattern.match(short)
        if not match:excluded.append({"uuid":stock["datastock_uuid"],"name":short,"reason":"not_primary_release"});continue
        candidates.append(((int(match.group(1)),roman.get(match.group(2).upper(),0)),stock))
    if not candidates:raise ValueError("No existe release primario Oekobaudat seleccionable.")
    best=max(key for key,_ in candidates);winners=[stock for key,stock in candidates if key==best]
    if len(winners)!=1:raise ValueError("Release Oekobaudat ambiguo.")
    return winners[0],excluded,len(candidates)

def parse_process_page(root,datastock_uuid):
    rows=[]
    for item in root.findall("p:process",NS):
        uuid=_text(item,"s:uuid").lower();version=_text(item,"s:dataSetVersion")
        if not uuid or not version:raise ValueError("Proceso Oekobaudat sin UUID/version.")
        languages={}
        for node in item.findall("s:name",NS):languages.setdefault(node.get(XML_LANG,"und"),[]).append(" ".join((node.text or "").split()))
        display=next((languages[key][0] for key in ("es","en","de") if languages.get(key)),next((values[0] for values in languages.values() if values),""))
        classifications=[]
        for tree in item.findall("s:classification",NS):
            classifications.append({"name":tree.get("name",""),"path":[{"level":int(node.get("level","0")),"id":node.get("classId",""),"label":" ".join((node.text or "").split())} for node in tree.findall("s:class",NS)]})
        compliance=[]
        for system in item.findall("p:complianceSystem",NS):
            ref=system.find("s:reference",NS);compliance.append({"name":system.get("name",""),"source_uuid":(ref.get("refObjectId","").lower() if ref is not None else "")})
        standard="EN 15804+A1" if any(c["source_uuid"]==A1 for c in compliance) else "EN 15804+A2" if any(c["source_uuid"]==A2 for c in compliance) else "unknown"
        standard_uuid=A1 if standard.endswith("A1") else A2 if standard.endswith("A2") else ""
        owner=item.find("p:ownership",NS);href=item.get(XLINK,"")
        if href:validate_okobaudat_url(href)
        rows.append({"datastock_uuid":datastock_uuid,"process_uuid":uuid,"dataset_version":version,"name":display,"base_name":display,"location_raw":_text(item,"p:location"),"dataset_type_raw":_text(item,"p:type"),"owner_raw":owner.get("refObjectId","") if owner is not None else "","classification":classifications,"languages":languages,"compliance_standard_raw":standard,"compliance_source_uuid":standard_uuid,"permanent_uri":href,"source_url":href or f"{ROOT}processes/{uuid}?version={version}","process_metadata":{"subtype":_text(item,"s:other/{http://www.iai.kit.edu/EPD/2013}subType"),"reference_year":_text(item,"p:time/p:referenceYear"),"valid_until":_text(item,"p:time/p:validUntil"),"compliance_systems":compliance}})
    attrs=lambda name:int(root.get(f"{{{NS['s']}}}{name}","0"))
    return rows,attrs("totalSize"),attrs("startIndex"),attrs("pageSize")

class OekobaudatSoda4LcaConnector(EnvironmentalConnector):
    page_size=200
    def fetch(self,sync_state):
        root,_=fetch_okobaudat_xml(f"{ROOT}datastocks/");stocks=parse_datastocks(root);selected,excluded,candidate_count=select_release(stocks);records=[]
        for stock in stocks:records.append(ConnectorRecord(external_id=f"okobaudat:datastock:{stock['datastock_uuid']}",canonical_key=stock["datastock_uuid"],kind="okobaudat_datastock",title=stock["display_name"],source_url=stock["source_url"],payload=stock,content_type="application/xml"))
        start=0;seen=set();process_count=0
        while True:
            page_url=f"{ROOT}datastocks/{selected['datastock_uuid']}/processes?startIndex={start}&pageSize={self.page_size}"
            page,_=fetch_okobaudat_xml(page_url);rows,total,page_start,page_size=parse_process_page(page,selected["datastock_uuid"])
            if page_start!=start or page_size<=0:raise ValueError("Paginacion Oekobaudat incompatible.")
            for row in rows:
                identity=(row["process_uuid"],row["dataset_version"])
                if identity in seen:continue
                seen.add(identity);process_count+=1;records.append(ConnectorRecord(external_id=f"okobaudat:process:{identity[0]}:{identity[1]}",canonical_key=f"{identity[0]}:{identity[1]}",kind="okobaudat_process",title=row["name"],source_url=row["source_url"],payload=row,content_type="application/xml"))
            start+=page_size
            if start>=total:break
            if not rows:raise ValueError("Paginacion Oekobaudat truncada.")
        metadata={**OKOBAUDAT_TERMS,"selected_datastock_uuid":selected["datastock_uuid"],"selected_datastock_name":selected["short_name"],"selection_policy_version":"okobaudat-release-selection-1","candidate_count":candidate_count,"excluded_datastocks":excluded,"datastocks_received":len(stocks),"processes_received":process_count}
        return ConnectorBatch(records=records,authoritative_full_snapshot=True,upstream_version=selected["short_name"],metadata=metadata)
