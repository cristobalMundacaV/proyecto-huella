from dataclasses import dataclass
from email.utils import parsedate_to_datetime

from django.db import transaction
from django.utils import timezone

from .connectors.huellachile import HUELLACHILE_DISCOVERY_URL,HUELLACHILE_HOSTS
from .downloads import download_external_file,remove_download
from .models import EnvironmentalSource,ExternalFileArtifact,ExternalRecord,HuellaChileEmissionFactorFact
from .services import sync_environmental_source
from .tabular import HuellaChileEmissionFactorParser


@dataclass(frozen=True)
class HuellaChileSyncResult:
    estado:str;dataset:str;logical_resource_id:str;year:int;edition:str;discovered_url:str;filename:str;filename_version:str;byte_size:int;sha256:str;rows_read:int;factors_imported:int;rejected:list;references:list;artifact:ExternalFileArtifact


def sync_huellachile_factors(year=2025,edition="completa"):
    source=EnvironmentalSource.objects.get(codigo="huellachile")
    discovery_run=sync_environmental_source(source)
    if discovery_run.estado=="error": raise ValueError(f"Falló el discovery HuellaChile: {discovery_run.message}")
    identity=f"huellachile:factores-emision:organizaciones-eventos:{year}:{edition}"
    parent=ExternalRecord.objects.select_related("current_snapshot").get(source=source,external_id=identity,estado=ExternalRecord.Status.ACTIVE)
    publication=parent.current_snapshot.raw_payload or {};url=publication.get("url");logical_resource_id=publication.get("logical_resource_id")
    if not url or not logical_resource_id: raise ValueError("La publicación HuellaChile descubierta no contiene un recurso válido.")
    download=None
    try:
        download=download_external_file(url,HUELLACHILE_HOSTS,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",{"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","application/octet-stream"},suffix=".xlsx")
        existing=ExternalFileArtifact.objects.filter(source=source,external_resource_id=logical_resource_id,content_sha256=download.sha256).first()
        if existing:
            if not existing.is_current:
                with transaction.atomic():
                    ExternalRecord.objects.select_for_update().get(pk=parent.pk)
                    ExternalFileArtifact.objects.filter(source=source,external_resource_id=logical_resource_id,is_current=True).update(is_current=False)
                    ExternalFileArtifact.objects.filter(pk=existing.pk).update(is_current=True)
                existing.refresh_from_db()
            return HuellaChileSyncResult("sin_cambios",parent.title,logical_resource_id,year,edition,url,publication.get("filename") or "",publication.get("filename_version") or "",download.byte_size,download.sha256,0,0,[],existing.metadata.get("references",[]),existing)
        parsed,workbook_metadata=HuellaChileEmissionFactorParser().parse(download.path,year=year)
        now=timezone.now();upstream_modified=parsedate_to_datetime(download.last_modified) if download.last_modified else None
        with transaction.atomic():
            ExternalRecord.objects.select_for_update().get(pk=parent.pk)
            previous=ExternalFileArtifact.objects.filter(source=source,external_resource_id=logical_resource_id);version=previous.count()+1;previous.filter(is_current=True).update(is_current=False)
            metadata={"publisher":"Programa HuellaChile / Ministerio del Medio Ambiente","source_page":HUELLACHILE_DISCOVERY_URL,"logical_resource_id":logical_resource_id,"year":year,"edition":edition,"filename":publication.get("filename"),"filename_version":publication.get("filename_version"),"rows_read":parsed.rows_read,"factors_imported":len(parsed.rows),"rows_rejected":len(parsed.rejected),"rejections":parsed.rejected,"etag":download.etag,"last_modified":download.last_modified,**workbook_metadata}
            artifact=ExternalFileArtifact.objects.create(source=source,parent_record=parent,external_resource_id=logical_resource_id,name=parent.title,source_url=url,format="XLSX",content_type=download.content_type,expected_size=None,byte_size=download.byte_size,upstream_modified_at=upstream_modified,retrieved_at=now,content_sha256=download.sha256,estado=ExternalFileArtifact.Status.IMPORTED,metadata=metadata,is_current=True,version=version)
            HuellaChileEmissionFactorFact.objects.bulk_create([HuellaChileEmissionFactorFact(artifact=artifact,**row) for row in parsed.rows],batch_size=1000)
        return HuellaChileSyncResult("importado",parent.title,logical_resource_id,year,edition,url,publication.get("filename") or "",publication.get("filename_version") or "",download.byte_size,download.sha256,parsed.rows_read,len(parsed.rows),parsed.rejected,workbook_metadata["references"],artifact)
    finally: remove_download(download)
