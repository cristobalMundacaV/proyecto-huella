import hashlib
import os
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler,Request,build_opener

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .connectors.retc import RETC_USER_AGENT, _datetime
from .models import ExternalFileArtifact, ExternalRecord, EnvironmentalSource, RetcHazardousWasteFact
from .tabular import RetcHazardousWasteParser


ALLOWED_RETC_HOSTS={"datosretc.mma.gob.cl"}
DOWNLOAD_TIMEOUT_SECONDS=60
DEFAULT_MAX_RESOURCE_BYTES=100*1024*1024


@dataclass(frozen=True)
class ResourceSyncResult:
    estado:str
    dataset:str
    resource_id:str
    resource_name:str
    year:int
    format:str
    byte_size:int
    sha256:str
    rows_read:int
    rows_imported:int
    rejected:list
    artifact:ExternalFileArtifact


def _validate_retc_url(url):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in ALLOWED_RETC_HOSTS or parsed.username or parsed.password:
        raise ValueError("URL de recurso RETC no permitida.")


class RetcRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        _validate_retc_url(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def _open_url(request,timeout):
    return build_opener(RetcRedirectHandler()).open(request,timeout=timeout)


def _resolve_resource(parent_record,year,format_name="XLSX"):
    payload=parent_record.current_snapshot.raw_payload or {}
    matches=[]
    for resource in payload.get("resources") or []:
        name=str(resource.get("name") or "")
        url=str(resource.get("url") or "")
        if str(resource.get("format") or "").upper()==format_name and str(year) in f"{name} {url}": matches.append(resource)
    if len(matches)!=1: raise ValueError(f"No existe un recurso {format_name} {year} inequívoco en el catálogo sincronizado.")
    resource=matches[0]
    if not resource.get("id") or not resource.get("url"): raise ValueError("El recurso carece de ID o URL oficial.")
    return resource


def _download(resource):
    url=resource["url"]
    _validate_retc_url(url)
    maximum=getattr(settings,"KNOWLEDGE_MAX_RESOURCE_BYTES",DEFAULT_MAX_RESOURCE_BYTES)
    expected=resource.get("size")
    if expected is not None and int(expected)>maximum: raise ValueError("El recurso excede el tamaño máximo permitido.")
    request=Request(url,headers={"Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","User-Agent":RETC_USER_AGENT})
    temp=tempfile.NamedTemporaryFile(prefix="carbonozero-knowledge-",suffix=".xlsx",delete=False)
    digest=hashlib.sha256();size=0
    try:
        with temp, _open_url(request,timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            _validate_retc_url(response.geturl())
            declared=response.headers.get("Content-Length")
            if declared and int(declared)>maximum: raise ValueError("El recurso excede el tamaño máximo permitido.")
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>maximum: raise ValueError("El recurso excede el tamaño máximo permitido.")
                digest.update(chunk);temp.write(chunk)
        return temp.name,size,digest.hexdigest()
    except Exception:
        temp.close()
        if os.path.exists(temp.name): os.unlink(temp.name)
        raise


def sync_retc_hazardous_waste(year):
    source=EnvironmentalSource.objects.get(codigo="retc")
    parent=ExternalRecord.objects.select_related("current_snapshot").get(source=source,canonical_key="generacion-de-residuos-peligrosos",estado=ExternalRecord.Status.ACTIVE)
    resource=_resolve_resource(parent,year)
    path=None
    try:
        path,byte_size,digest=_download(resource)
        existing=ExternalFileArtifact.objects.filter(source=source,external_resource_id=resource["id"],content_sha256=digest).first()
        if existing:
            if not existing.is_current:
                with transaction.atomic():
                    ExternalRecord.objects.select_for_update().get(pk=parent.pk)
                    ExternalFileArtifact.objects.filter(source=source,external_resource_id=resource["id"],is_current=True).update(is_current=False)
                    ExternalFileArtifact.objects.filter(pk=existing.pk).update(is_current=True)
                existing.refresh_from_db()
            return ResourceSyncResult("sin_cambios",parent.title,resource["id"],resource.get("name") or "",year,"XLSX",byte_size,digest,0,0,[],existing)
        parsed=RetcHazardousWasteParser().parse(path,year=year)
        now=timezone.now()
        with transaction.atomic():
            ExternalRecord.objects.select_for_update().get(pk=parent.pk)
            previous=ExternalFileArtifact.objects.filter(source=source,external_resource_id=resource["id"])
            version=previous.count()+1
            previous.filter(is_current=True).update(is_current=False)
            artifact=ExternalFileArtifact.objects.create(source=source,parent_record=parent,external_resource_id=resource["id"],name=resource.get("name") or "",source_url=resource["url"],format="XLSX",content_type=resource.get("mimetype") or "",expected_size=resource.get("size"),byte_size=byte_size,upstream_created_at=_datetime(resource.get("created")),upstream_modified_at=_datetime(resource.get("last_modified")),retrieved_at=now,content_sha256=digest,estado=ExternalFileArtifact.Status.IMPORTED,metadata={"year":year,"sheets":parsed.sheets,"headers":parsed.headers,"rows_read":parsed.rows_read,"rows_imported":len(parsed.rows),"rows_rejected":len(parsed.rejected),"rejections":parsed.rejected},is_current=True,version=version)
            RetcHazardousWasteFact.objects.bulk_create([RetcHazardousWasteFact(artifact=artifact,external_resource_id=resource["id"],**row) for row in parsed.rows],batch_size=1000)
        return ResourceSyncResult("importado",parent.title,resource["id"],resource.get("name") or "",year,"XLSX",byte_size,digest,parsed.rows_read,len(parsed.rows),parsed.rejected,artifact)
    finally:
        if path and os.path.exists(path): os.unlink(path)
