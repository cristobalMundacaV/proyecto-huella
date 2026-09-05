import glob
import io
import json
import os
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase,override_settings
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from .models import EnvironmentalSource,ExternalFileArtifact,ExternalRecord,ExternalSnapshot,RetcHazardousWasteFact,SourceState,SyncRun
from .resource_sync import sync_retc_hazardous_waste
from .tabular import RetcHazardousWasteParser


class DownloadResponse:
    def __init__(self,content,url="https://datosretc.mma.gob.cl/files/resource.xlsx",headers=None): self.stream=io.BytesIO(content);self.url=url;self.headers=headers or {"Content-Length":str(len(content))}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size=-1): return self.stream.read(size)
    def geturl(self): return self.url


def workbook_bytes(quantity=1000,headers=None):
    workbook=Workbook();sheet=workbook.active;sheet.title="Hoja1";headers=headers or list(RetcHazardousWasteParser.HEADERS);sheet.append(headers)
    row={"año":2024,"id_vu":5,"id_rol_establecimiento":1,"rol_establecimiento":"Transferencia de Residuos (Generador)","rut_razon_social":"94283000-9","razon_social":"Empresa","ciiu6_id":"C259900","ciiu6":"Fabricación","ciiu4_id":"C25990","ciiu4":"Fabricación","rubro":"Industria","rubro_id":10,"codigo_unico_territorial":1201,"comuna":"Arica","provincia":"Arica","region":"Arica y Parinacota","latitud":-18473556298281,"longitud":-7031735947686,"cantidad_kilos":quantity,"cantidad_toneladas":quantity/1000,"id_contaminantes":"I.8,","contaminantes":"Aceites minerales","id_peligrosidad":"2,","peligrosidad":"TOXICO CRONICO","id_lista_a":"A3020","lista_a":"Aceites minerales de desecho","id_estado_materia":2,"estado_materia":"líquido"}
    sheet.append([row.get(header) for header in headers]);output=io.BytesIO();workbook.save(output);return output.getvalue()


class ExternalResourceSyncTests(TestCase):
    def setUp(self):
        self.source=EnvironmentalSource.objects.get(codigo="retc")
        self.source.connector_key="retc_ckan";self.source.licencia_nombre="Creative Commons Attribution";self.source.licencia_url="http://www.opendefinition.org/licenses/cc-by";self.source.save()
        SourceState.objects.filter(source=self.source).update(last_successful_sync_at=timezone.now(),estado="actualizada")
        run=SyncRun.objects.create(source=self.source,trigger="manual",started_at=timezone.now(),finished_at=timezone.now(),estado="actualizada")
        resource={"id":"resource-2024","name":"Generación de residuos peligrosos 2024","format":"XLSX","url":"https://datosretc.mma.gob.cl/files/gen-sidrep-2024.xlsx","size":5000,"created":"2025-12-02T17:48:49.328794","last_modified":"2025-12-02T17:48:49.113014","mimetype":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","datastore_active":False}
        snapshot=ExternalSnapshot.objects.create(source=self.source,sync_run=run,external_id="dataset",record_kind="retc_dataset",retrieved_at=timezone.now(),content_hash="a"*64,raw_payload={"resources":[resource]})
        self.parent=ExternalRecord.objects.create(source=self.source,external_id="dataset",kind="retc_dataset",canonical_key="generacion-de-residuos-peligrosos",title="Generación de residuos peligrosos",current_snapshot=snapshot,first_seen_at=timezone.now(),last_seen_at=timezone.now())

    @patch("apps.knowledge.resource_sync._open_url")
    def test_xlsx_valido_raw_trazable_y_misma_sha_idempotente(self,mocked):
        content=workbook_bytes();mocked.side_effect=[DownloadResponse(content),DownloadResponse(content)]
        first=sync_retc_hazardous_waste(2024);second=sync_retc_hazardous_waste(2024);fact=RetcHazardousWasteFact.objects.get()
        self.assertEqual((first.estado,first.rows_imported,second.estado,second.rows_imported),("importado",1,"sin_cambios",0))
        self.assertEqual((ExternalFileArtifact.objects.count(),RetcHazardousWasteFact.objects.count()),(1,1))
        self.assertEqual((fact.region,fact.comuna,str(fact.cantidad_toneladas)),("Arica y Parinacota","Arica","1.000000000"))
        self.assertEqual(fact.raw_row["latitud"],-18473556298281)

    @patch("apps.knowledge.resource_sync._open_url")
    def test_nueva_sha_versiona_y_preserva_facts_anteriores(self,mocked):
        mocked.side_effect=[DownloadResponse(workbook_bytes(1000)),DownloadResponse(workbook_bytes(2000))]
        first=sync_retc_hazardous_waste(2024);second=sync_retc_hazardous_waste(2024)
        first.artifact.refresh_from_db();self.assertFalse(first.artifact.is_current);self.assertTrue(second.artifact.is_current)
        self.assertEqual((ExternalFileArtifact.objects.count(),RetcHazardousWasteFact.objects.count()),(2,2))

    @patch("apps.knowledge.resource_sync._open_url")
    def test_fallo_parseo_no_desactiva_version_anterior(self,mocked):
        mocked.side_effect=[DownloadResponse(workbook_bytes()),DownloadResponse(b"archivo corrupto")]
        first=sync_retc_hazardous_waste(2024)
        with self.assertRaisesRegex(ValueError,"XLSX válido"): sync_retc_hazardous_waste(2024)
        first.artifact.refresh_from_db();self.assertTrue(first.artifact.is_current);self.assertEqual(ExternalFileArtifact.objects.count(),1)

    @patch("apps.knowledge.resource_sync._open_url")
    def test_esquema_inesperado_y_temporal_eliminado(self,mocked):
        mocked.return_value=DownloadResponse(workbook_bytes(headers=["columna_desconocida"]))
        before=set(glob.glob(os.path.join(tempfile.gettempdir(),"carbonozero-knowledge-*")))
        with self.assertRaisesRegex(ValueError,"esquema XLSX"): sync_retc_hazardous_waste(2024)
        after=set(glob.glob(os.path.join(tempfile.gettempdir(),"carbonozero-knowledge-*")))
        self.assertEqual(before,after)

    def test_recurso_incorrecto_falla_antes_de_descargar(self):
        self.parent.current_snapshot.raw_payload={"resources":[]};ExternalSnapshot.objects.filter(pk=self.parent.current_snapshot_id).update(raw_payload={"resources":[]});self.parent.current_snapshot.refresh_from_db()
        with self.assertRaisesRegex(ValueError,"inequívoco"): sync_retc_hazardous_waste(2024)

    @patch("apps.knowledge.resource_sync._open_url")
    def test_redirect_fuera_del_host_es_rechazado(self,mocked):
        mocked.return_value=DownloadResponse(workbook_bytes(),url="https://evil.example.test/resource.xlsx")
        with self.assertRaisesRegex(ValueError,"no permitida"): sync_retc_hazardous_waste(2024)

    @patch("apps.knowledge.resource_sync._open_url",side_effect=TimeoutError("timeout"))
    def test_timeout_no_crea_artifact(self,mocked):
        with self.assertRaises(TimeoutError): sync_retc_hazardous_waste(2024)
        self.assertFalse(ExternalFileArtifact.objects.exists())

    @override_settings(KNOWLEDGE_MAX_RESOURCE_BYTES=100)
    def test_archivo_demasiado_grande_se_rechaza_por_metadata(self):
        with self.assertRaisesRegex(ValueError,"tamaño máximo"): sync_retc_hazardous_waste(2024)

    @patch("apps.knowledge.resource_sync._open_url")
    def test_api_autenticada_filtra_solo_version_current_y_pagina(self,mocked):
        mocked.side_effect=[DownloadResponse(workbook_bytes(1000)),DownloadResponse(workbook_bytes(2000))];sync_retc_hazardous_waste(2024);current=sync_retc_hazardous_waste(2024)
        client=APIClient();self.assertIn(client.get("/api/knowledge/retc/hazardous-waste/").status_code,(401,403));client.force_authenticate(User.objects.create_user("knowledge-resource"))
        data=client.get("/api/knowledge/retc/hazardous-waste/?region=Arica%20y%20Parinacota&page_size=1").data
        self.assertEqual((data["count"],len(data["results"])),(1,1));self.assertEqual(data["results"][0]["artifact"],current.artifact.id)
        metadata=client.get("/api/knowledge/retc/hazardous-waste/metadata/").data;self.assertEqual((metadata["year"],metadata["record_count"]),(2024,1))
