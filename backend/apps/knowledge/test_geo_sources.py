from unittest.mock import patch
from threading import Event,Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections,connection
from django.test import TestCase,TransactionTestCase
from rest_framework.test import APIClient

from .bootstrap import ensure_environmental_source_registry
from .connectors.base import ConnectorBatch,ConnectorRecord
from .connectors.ide_mma import IdeMmaCatalogConnector,parse_catalog_index,parse_dataset_detail,parse_downloads,parse_interoperability,validate_ide_url
from .connectors.simbio import SIMBIO_LAYER_MANIFEST,SimbioArcgisConnector,validate_simbio_url
from .geo_sync import sync_ide_mma_geo_catalog,sync_simbio_geo_catalog
from .geo_facts import normalize_simbio_layer
from .models import EnvironmentalSource,ExternalSnapshot,IdeMmaDatasetFact,IdeMmaDownloadResourceFact,SimbioGeoLayerFact
from .services import source_freshness

CATALOG="""<a href='/sinia/catalog/21/Zonas'>Zonas saturadas latentes</a>"""
DETAIL="""<div class='grid'><div class='col-span-1'>Identificador de Archivo:</div><div>{abc-123}</div><div class='col-span-1'>Título del recurso:</div><div>Zonas saturadas latentes</div><div class='col-span-1'>Resumen del recurso:</div><div>Número de Entidades: 28 | Tamaño en MB: 1,67 | Tipo de Geometría: Poligonal</div><div class='col-span-1'>Nombre de la Organización:</div><div>MMA</div><div class='col-span-1'>Estado:</div><div>Completado</div><div class='col-span-1'>Fecha de Recurso:</div><div>2025-12-25</div><div class='col-span-1'>Colección de palabras claves:</div><div>aire, zona</div><div class='col-span-1'>Categoría temática:</div><div>Medio ambiente</div><div class='col-span-1'>Longitud Oeste:</div><div>-75,5</div><div class='col-span-1'>Longitud Este:</div><div>-66.0</div><div class='col-span-1'>Latitud Sur:</div><div>-56</div><div class='col-span-1'>Latitud Norte:</div><div>-17.5</div><div class='col-span-1'>Campo futuro:</div><div>preservado</div></div>"""
DOWNLOADS="""<h2>Medio ambiente</h2><article>Zonas - 1.2 MB <a href='/centro-de-descargas/32'>Descargar</a></article>"""
INTEROP_EMPTY="""<h1>Servicios Disponibles</h1><p>No hay servicios disponibles en este momento</p>"""
INTEROP_FUTURE="""<a href='https://ide.mma.gob.cl/servicios-de-interoperabilidad/wfs'>Servicio WFS oficial</a>"""

def service_payload(code):
    layers=[{"id":layer_id,"name":name,"type":"Feature Layer","geometryType":"esriGeometryPolygon"} for service,layer_id,name in SIMBIO_LAYER_MANIFEST if service==code]
    return {"name":code,"layers":layers,"spatialReference":{"wkid":32719},"maxRecordCount":2000,"supportedQueryFormats":"JSON","capabilities":"Query,Create,Update,Delete,Uploads,Editing","serviceItemId":f"item-{code}"}

def layer_payload(code,layer_id,changed=False):
    name=next(name for service,item_id,name in SIMBIO_LAYER_MANIFEST if service==code and item_id==layer_id)
    fields=[{"name":"OBJECTID","alias":"OBJECTID","type":"esriFieldTypeOID","nullable":False},{"name":"NOMBRE","alias":"Nombre","type":"esriFieldTypeString","nullable":True,"domain":{"type":"codedValue","codedValues":[]}}]
    if changed:fields.append({"name":"NUEVO","alias":"Nuevo","type":"esriFieldTypeString","nullable":True})
    return {"id":layer_id,"name":name,"type":"Feature Layer","geometryType":"esriGeometryPolygon","extent":{"spatialReference":{"wkid":32719}},"displayField":"NOMBRE","objectIdField":"OBJECTID","maxRecordCount":2000,"supportedQueryFormats":"PBF, JSON","advancedQueryCapabilities":{"supportsPagination":True,"supportsQueryWithDistance":True},"capabilities":"Query","fields":fields}

def arcgis_fetch(changed=False):
    def fetch(url):
        parts=url.rstrip("/").split("/");code=parts[-2] if parts[-1]=="FeatureServer" else parts[-3]
        return service_payload(code) if parts[-1]=="FeatureServer" else layer_payload(code,int(parts[-1]),changed)
    return fetch

class GeoSourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_environmental_source_registry();cls.simbio=EnvironmentalSource.objects.get(codigo="simbio");cls.ide=EnvironmentalSource.objects.get(codigo="ide-mma");cls.user=get_user_model().objects.create_user("geo-reader")

    def test_bootstrap_managed_sources_and_stewardship(self):
        self.assertEqual((self.simbio.connector_key,self.simbio.tipo_acceso),("simbio_arcgis","ARCGIS_REST"));self.assertEqual((self.ide.connector_key,self.ide.tipo_acceso),("ide_mma_catalog","DOCUMENT_INDEX"));self.assertEqual(self.simbio.licencia_nombre,"")
        self.assertEqual(self.simbio.sync_state.metadata["biodiversity_official_data_responsibility"],"SBAP");self.assertFalse(self.ide.sync_state.metadata["authoritative_for_compliance"])
        self.ide.connector_key="custom";self.ide.base_url="https://ide.mma.gob.cl/custom";self.ide.save();ensure_environmental_source_registry();self.ide.refresh_from_db();self.assertEqual(self.ide.connector_key,"custom")
        self.simbio.connector_key="pending-simbio";self.simbio.tipo_acceso="DOCUMENT_INDEX";self.simbio.base_url="https://simbio.mma.gob.cl/manual";self.simbio.save();ensure_environmental_source_registry();self.simbio.refresh_from_db();self.assertEqual((self.simbio.connector_key,self.simbio.tipo_acceso,self.simbio.base_url),("pending-simbio","DOCUMENT_INDEX","https://simbio.mma.gob.cl/manual"))

    def test_simbio_manifest_sync_dedupe_change_api_and_immutability(self):
        self.assertEqual(len(SIMBIO_LAYER_MANIFEST),8)
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):first=sync_simbio_geo_catalog()
        self.assertEqual((first.created,SimbioGeoLayerFact.objects.count()),(8,8));fact=SimbioGeoLayerFact.objects.get(service_code="SIMBIO_AP",layer_id=0)
        self.assertEqual((fact.layer_name,fact.geometry_type,fact.spatial_reference_wkid),("Áreas Protegidas","esriGeometryPolygon",32719));self.assertTrue(fact.supports_distance_query);self.assertTrue(any("domain" in field for field in fact.fields_schema))
        count=ExternalSnapshot.objects.filter(source=self.simbio).count()
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):second=sync_simbio_geo_catalog()
        self.assertEqual((second.modified,ExternalSnapshot.objects.filter(source=self.simbio).count()),(0,count))
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch(True)):third=sync_simbio_geo_catalog()
        self.assertEqual(third.modified,8);self.assertEqual(ExternalSnapshot.objects.filter(source=self.simbio).count(),count+8)
        fact.layer_name="Falso"
        with self.assertRaises(ValidationError):fact.save()
        for operation in (lambda:SimbioGeoLayerFact.objects.update(layer_name="Falso"),lambda:SimbioGeoLayerFact.objects.all().delete(),lambda:SimbioGeoLayerFact.objects.bulk_create([])):
            with self.assertRaises(ValidationError):operation()
        from .geo_facts import build_simbio_layer_fact_payload
        values=build_simbio_layer_fact_payload(fact.snapshot);values["layer_name"]="Adulterada"
        with self.assertRaises(ValidationError):SimbioGeoLayerFact.objects.create(snapshot=fact.snapshot,**values)
        client=APIClient();client.force_authenticate(self.user);response=client.get("/api/knowledge/geo/simbio/layers/?service_code=SIMBIO_AP")
        self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],4);self.assertEqual(response.data["results"][0]["provider"],"SIMBIO/MMA")

    def test_simbio_contract_and_security_are_fail_closed(self):
        bad=service_payload("SIMBIO_AP");bad["layers"][0]["name"]="Parecida"
        connector=SimbioArcgisConnector(self.simbio)
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",return_value=bad),self.assertRaises(ValueError):connector.fetch(self.simbio.sync_state)
        layer=layer_payload("SIMBIO_AP",0);reordered=dict(layer);reordered["fields"]=list(reversed(layer["fields"]));service=service_payload("SIMBIO_AP");url="https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/SIMBIO_AP/FeatureServer"
        self.assertEqual(normalize_simbio_layer("SIMBIO_AP","Áreas Protegidas",service,layer,url,url+"/0"),normalize_simbio_layer("SIMBIO_AP","Áreas Protegidas",service,reordered,url,url+"/0"))
        for url in ("http://arcgis.mma.gob.cl/server/rest/services/SIMBIO/X","https://localhost/server/rest/services/SIMBIO/X","file:///tmp/x","https://arcgis.mma.gob.cl/other","https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/X/FeatureServer/0/applyEdits"):
            with self.assertRaises(ValueError):validate_simbio_url(url)

    def test_ide_parsers_sync_capability_and_api(self):
        index=parse_catalog_index(CATALOG);self.assertEqual(index[0]["index_key"],"21");payload=parse_dataset_detail(DETAIL,index[0]);self.assertEqual((payload["dataset_key"],payload["feature_count"],payload["bbox_west"]),("{abc-123}",28,"-75,5"));self.assertEqual(payload["upstream_fields"]["Campo futuro"],"preservado")
        self.assertEqual(parse_downloads(DOWNLOADS)[0]["declared_size_raw"],"1.2 MB");self.assertEqual(parse_interoperability(INTEROP_EMPTY),[]);self.assertEqual(len(parse_interoperability(INTEROP_FUTURE)),1)
        responses=[(CATALOG,"a"*64,"https://ide.mma.gob.cl/sinia/catalog"),(DETAIL,"b"*64,index[0]["metadata_url"]),(DOWNLOADS,"c"*64,"https://ide.mma.gob.cl/centro-de-descargas"),(INTEROP_EMPTY,"d"*64,"https://ide.mma.gob.cl/servicios-de-interoperabilidad")]
        with patch("apps.knowledge.connectors.ide_mma.fetch_html",side_effect=responses):run=sync_ide_mma_geo_catalog()
        self.assertEqual((run.created,IdeMmaDatasetFact.objects.count(),IdeMmaDownloadResourceFact.objects.count()),(2,1,1));state=self.ide.sync_state;state.refresh_from_db();self.assertFalse(state.metadata["interoperability_available"]);self.assertTrue(state.metadata["external_capability_limited"])
        dataset=IdeMmaDatasetFact.objects.get();download=IdeMmaDownloadResourceFact.objects.get();dataset.title="Falso"
        with self.assertRaises(ValidationError):dataset.save()
        for model in (IdeMmaDatasetFact,IdeMmaDownloadResourceFact):
            with self.assertRaises(ValidationError):model.objects.update(title="Falso")
            with self.assertRaises(ValidationError):model.objects.all().delete()
            with self.assertRaises(ValidationError):model.objects.bulk_create([])
        from .geo_facts import build_ide_dataset_fact_payload,build_ide_download_fact_payload
        values=build_ide_dataset_fact_payload(dataset.snapshot);values["status_raw"]="Adulterado"
        with self.assertRaises(ValidationError):IdeMmaDatasetFact.objects.create(snapshot=dataset.snapshot,**values)
        values=build_ide_download_fact_payload(download.snapshot);values["title"]="Adulterado"
        with self.assertRaises(ValidationError):IdeMmaDownloadResourceFact.objects.create(snapshot=download.snapshot,**values)
        client=APIClient();client.force_authenticate(self.user);self.assertEqual(client.get("/api/knowledge/geo/ide/datasets/?keyword=aire").data["count"],1);self.assertEqual(client.get("/api/knowledge/geo/ide/downloads/").data["count"],1)
        for url in ("http://ide.mma.gob.cl/sinia/catalog","https://localhost/sinia/catalog","https://ide.mma.gob.cl/oculto"):
            with self.assertRaises(ValueError):validate_ide_url(url)

    def test_atomic_first_failure_preserves_snapshot_and_retry(self):
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()),patch("apps.knowledge.geo_sync._materialize_simbio",side_effect=ValueError("fact invalido")):failed=sync_simbio_geo_catalog()
        self.assertEqual(failed.estado,"parcial");self.assertEqual(self.simbio.records.count(),0);self.assertEqual(SimbioGeoLayerFact.objects.count(),0);self.assertEqual(source_freshness(self.simbio),"parcial_sin_version_publicada");snapshots=ExternalSnapshot.objects.filter(source=self.simbio).count()
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):sync_simbio_geo_catalog()
        self.assertEqual(ExternalSnapshot.objects.filter(source=self.simbio).count(),snapshots);self.assertEqual(SimbioGeoLayerFact.objects.count(),8)

    def test_existing_publication_is_fully_restored_after_partial(self):
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):sync_simbio_geo_catalog()
        record=self.simbio.records.get(external_id="simbio:SIMBIO_AP:0");fields=("current_snapshot_id","kind","canonical_key","title","source_url","published_at","upstream_updated_at","estado","metadata","last_seen_at");before={field:getattr(record,field) for field in fields}
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch(True)),patch("apps.knowledge.geo_sync._materialize_simbio",side_effect=ValueError("normalizacion rota")):failed=sync_simbio_geo_catalog()
        record.refresh_from_db();self.assertEqual(failed.estado,"parcial");self.assertEqual({field:getattr(record,field) for field in fields},before);self.assertEqual(ExternalSnapshot.objects.filter(source=self.simbio,external_id=record.external_id).count(),2);self.assertEqual(SimbioGeoLayerFact.objects.filter(snapshot__external_id=record.external_id).count(),1);self.assertEqual(source_freshness(self.simbio),"parcial_con_ultima_version_disponible")


class GeoPostgresConcurrencyTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor!="postgresql":return super()._fixture_teardown()
        tables=connection.introspection.table_names()
        if tables:
            with connection.cursor() as cursor:cursor.execute("TRUNCATE "+", ".join(connection.ops.quote_name(table) for table in tables)+" RESTART IDENTITY CASCADE")
    def test_concurrent_simbio_sync_is_serialized(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        ensure_environmental_source_registry();source=EnvironmentalSource.objects.get(codigo="simbio");entered=Event();release=Event();results=[];errors=[]
        records=[]
        for service,layer_id,name in SIMBIO_LAYER_MANIFEST:
            payload=normalize_simbio_layer(service,name,service_payload(service),layer_payload(service,layer_id),f"https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/{service}/FeatureServer",f"https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/{service}/FeatureServer/{layer_id}")
            key=f"simbio:{service}:{layer_id}";records.append(ConnectorRecord(external_id=key,canonical_key=key,kind="simbio_geo_layer",title=name,source_url=payload["layer_url"],payload=payload))
        def fetch(connector,state):entered.set();release.wait(10);return ConnectorBatch(records=records,authoritative_full_snapshot=True)
        def execute():
            close_old_connections()
            try:results.append(sync_simbio_geo_catalog())
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        with patch.object(SimbioArcgisConnector,"fetch",fetch):
            first=Thread(target=execute);first.start();self.assertTrue(entered.wait(10));second=Thread(target=execute);second.start();second.join(10);release.set();first.join(20)
        self.assertEqual((len(results),len(errors)),(1,1));self.assertIn("sincronizando",str(errors[0]));self.assertEqual(SimbioGeoLayerFact.objects.count(),8)
