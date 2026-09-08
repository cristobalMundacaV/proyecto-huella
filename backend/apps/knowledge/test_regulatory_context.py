from unittest.mock import patch
from threading import Event, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from .bootstrap import ensure_environmental_source_registry
from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.http import validate_sea_url, validate_snifa_url
from .connectors.sea import parse_sea_project, parse_sea_search_results
from .connectors.snifa import SnifaPublicConnector, parse_snifa_dataset_catalog, parse_snifa_reference
from .models import EnvironmentalSource, ExternalRecord, ExternalSnapshot, SeaProjectFact, SeaProjectSubscription, SeaRcaReferenceFact, SnifaOpenDatasetFact, SnifaReferenceSubscription, SnifaRegulatoryReferenceFact
from .regulatory_facts import build_sea_project_fact_payload, build_sea_rca_fact_payload, build_snifa_dataset_fact_payload, build_snifa_reference_fact_payload
from .sea_sync import sync_sea_regulatory_context
from .services import source_freshness
from .snifa_sync import sync_snifa_regulatory_context

CATALOG="""<html><a href='https://drive.google.com/folder/unit'><section><h4>Unidades Fiscalizables e Instrumentos</h4><p>Catastro oficial.</p></section></a><a href='https://drive.google.com/folder/inspection'><section><h4>Fiscalizaciones</h4><p>Fiscalizaciones historicas.</p></section></a></html>"""
SNIFA="""<table><tr><th>Expediente</th><td>D-001-2026</td></tr><tr><th>Unidad Fiscalizable</th><td>Planta Demo</td></tr><tr><th>Titular</th><td>Empresa Demo</td></tr><tr><th>Región</th><td>Biobío</td></tr><tr><th>Comuna</th><td>Los Ángeles</td></tr><tr><th>Estado</th><td>En curso</td></tr><tr><th>Etiqueta futura</th><td>Texto preservado</td></tr></table><a href='/General/Descargar/1'>RCA N° 12/2011</a>"""
SEA="""<table><tr><th>Folio</th><td>2026-8-1</td></tr><tr><th>Nombre del Proyecto</th><td>Parque Demo</td></tr><tr><th>Titular</th><td>Titular Demo</td></tr><tr><th>Región</th><td>Biobío</td></tr><tr><th>Comuna</th><td>Los Ángeles; Mulchén</td></tr><tr><th>Tipo de Presentación</th><td>DIA</td></tr><tr><th>Estado</th><td>Aprobado</td></tr><tr><th>Sector Productivo</th><td>Energía</td></tr><tr><th>Fecha de Presentación</th><td>01/02/2026</td></tr></table><a data-document-id='rca-1' data-date='03/04/2026' data-result='Favorable' href='/expediente/documentos/rca-1'>RCA N° 10/2026</a><a data-document-id='rca-2' href='/expediente/documentos/rca-2'>Resolución de Calificación Ambiental N° 11/2026</a>"""
SEARCH="""<table><tbody><tr data-project-key='EXP-123'><td data-label='Folio'>2026-8-1</td><td data-label='Nombre'><a href='/expediente/ficha/fichaPrincipal.php?id=123'>Parque Demo</a></td><td data-label='Titular'>Titular Demo</td><td data-label='Región'>Biobío</td><td data-label='Tipo'>DIA</td><td data-label='Estado'>Aprobado</td></tr></tbody></table>"""


class RegulatoryParserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_environmental_source_registry();cls.snifa=EnvironmentalSource.objects.get(codigo="snifa");cls.sea=EnvironmentalSource.objects.get(codigo="sea-seia")
        cls.snifa_sub=SnifaReferenceSubscription.objects.create(source=cls.snifa,reference_type="sanctioning",external_key="D-001-2026",source_url="https://snifa.sma.gob.cl/Sancionatorio/Ficha/1",label="Expediente demo")
        cls.sea_sub=SeaProjectSubscription.objects.create(source=cls.sea,project_key="EXP-123",project_url="https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?id=123",label="Parque Demo")

    def test_bootstrap_managed_defaults_and_custom_preserved(self):
        self.assertEqual((self.snifa.connector_key,self.snifa.tipo_acceso),("snifa_public","DOCUMENT_INDEX"));self.assertEqual((self.sea.connector_key,self.sea.tipo_acceso),("sea_seia_public","DOCUMENT_INDEX"));self.assertEqual(self.snifa.licencia_nombre,"")
        self.snifa.connector_key="custom_snifa";self.snifa.base_url="https://snifa.sma.gob.cl/UnidadFiscalizable";self.snifa.save();ensure_environmental_source_registry();self.snifa.refresh_from_db();self.assertEqual(self.snifa.connector_key,"custom_snifa")

    def test_snifa_catalog_reference_and_explicit_rca(self):
        items=parse_snifa_dataset_catalog(CATALOG);self.assertEqual([item["dataset_code"] for item in items],["fiscalizaciones","unidades-fiscalizables-e-instrumentos"])
        payload=parse_snifa_reference(SNIFA,self.snifa_sub);self.assertEqual((payload["expediente"],payload["region"]),("D-001-2026","Biobío"));self.assertEqual(payload["instrument_references"][0]["number_raw"],"12/2011");self.assertEqual(payload["upstream_fields"]["Etiqueta futura"],"Texto preservado")
        with self.assertRaises(ValueError):parse_snifa_reference("<html>cambio</html>",self.snifa_sub)
        for reference_type in ("unit","inspection","sanctioning","final_sanction"):
            subscription=SnifaReferenceSubscription(source=self.snifa,reference_type=reference_type,external_key=f"KEY-{reference_type}",source_url=f"https://snifa.sma.gob.cl/Fiscalizacion/{reference_type}",label=reference_type)
            self.assertEqual(parse_snifa_reference(SNIFA,subscription)["reference_type"],reference_type)
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):batch=SnifaPublicConnector(self.snifa).fetch(self.snifa.sync_state)
        self.assertFalse(batch.authoritative_full_snapshot)

    def test_sea_search_project_and_rcas_without_download(self):
        found=parse_sea_search_results(SEARCH);self.assertEqual((found[0]["project_key"],found[0]["folio"]),("EXP-123","2026-8-1"))
        payload=parse_sea_project(SEA,self.sea_sub);self.assertEqual((payload["presentation_type_raw"],payload["status_raw"]),("DIA","Aprobado"));self.assertEqual(payload["communes"],["Los Ángeles","Mulchén"]);self.assertEqual(len(payload["rca_references"]),2)
        with self.assertRaises(ValueError):parse_sea_project("<html>roto</html>",self.sea_sub)

    def test_sea_connector_declares_public_discovery_limitation(self):
        from .connectors.sea import SeaSeiaPublicConnector
        with patch("apps.knowledge.connectors.sea.fetch_html",return_value=(SEA,"a"*64,self.sea_sub.project_url)):
            batch=SeaSeiaPublicConnector(self.sea).fetch(self.sea.sync_state)
        self.assertTrue(batch.metadata["external_capability_limited"])
        self.assertEqual(batch.metadata["discovery_capability"],"server_rendered_public_results_only")

    def test_url_allowlists_reject_ssrf(self):
        validate_snifa_url("https://snifa.sma.gob.cl/Fiscalizacion/Ficha/1");validate_sea_url("https://seia.sea.gob.cl/expediente/ficha/1")
        for url in ("http://snifa.sma.gob.cl/Fiscalizacion/1","https://localhost/Fiscalizacion/1","file:///tmp/a","https://127.0.0.1/expediente/1","https://evil.example/expediente/1"):
            with self.assertRaises(ValueError):(validate_snifa_url if "Fiscalizacion" in url else validate_sea_url)(url)


class RegulatorySyncApiTests(TestCase):
    def setUp(self):
        ensure_environmental_source_registry();self.snifa=EnvironmentalSource.objects.get(codigo="snifa");self.sea=EnvironmentalSource.objects.get(codigo="sea-seia");self.user=get_user_model().objects.create_user("reader");self.admin=get_user_model().objects.create_superuser("root","root@example.cl","x")
        self.snifa_sub=SnifaReferenceSubscription.objects.create(source=self.snifa,reference_type="sanctioning",external_key="D-001-2026",source_url="https://snifa.sma.gob.cl/Sancionatorio/Ficha/1",label="Expediente demo")
        self.sea_sub=SeaProjectSubscription.objects.create(source=self.sea,project_key="EXP-123",project_url="https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?id=123",label="Parque Demo")

    def test_snifa_sync_dedupe_semantic_change_and_partial_scope(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):first=sync_snifa_regulatory_context()
        self.assertEqual((first.created,SnifaOpenDatasetFact.objects.count(),SnifaRegulatoryReferenceFact.objects.count()),(3,2,1))
        cosmetic="\n  "+CATALOG+"  "; reference_cosmetic=SNIFA.replace("<table>","<table>\n")
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(cosmetic,"c"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(reference_cosmetic,"d"*64,self.snifa_sub.source_url)]):second=sync_snifa_regulatory_context()
        self.assertEqual((second.created,second.modified,ExternalSnapshot.objects.filter(source=self.snifa).count()),(0,0,3))
        changed=SNIFA.replace("En curso","Finalizado")
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(changed,"e"*64,self.snifa_sub.source_url)]):third=sync_snifa_regulatory_context()
        self.assertEqual(third.modified,1);self.assertEqual(SnifaRegulatoryReferenceFact.objects.count(),2)

    def test_snifa_materialization_rollback_preserves_old_current(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):sync_snifa_regulatory_context()
        old=self.snifa.records.get(external_id="sanctioning:D-001-2026").current_snapshot_id;changed=SNIFA.replace("En curso","Finalizado")
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(changed,"c"*64,self.snifa_sub.source_url)]),patch("apps.knowledge.snifa_sync._materialize",side_effect=ValueError("normalizacion rota")):run=sync_snifa_regulatory_context()
        self.assertEqual(run.estado,"parcial");self.assertEqual(self.snifa.records.get(external_id="sanctioning:D-001-2026").current_snapshot_id,old);self.assertEqual(SnifaRegulatoryReferenceFact.objects.count(),1)
        client=APIClient();client.force_authenticate(self.user);response=client.get("/api/knowledge/snifa/references/")
        self.assertEqual(response.data["count"],1);self.assertEqual(response.data["results"][0]["status_raw"],"En curso")

    def test_sea_sync_materializes_project_and_rca_and_rollback(self):
        with patch("apps.knowledge.connectors.sea.fetch_html",return_value=(SEA,"a"*64,self.sea_sub.project_url)):first=sync_sea_regulatory_context()
        fact=SeaProjectFact.objects.get();old=fact.snapshot_id;self.assertEqual((first.created,fact.presentation_type_raw,SeaRcaReferenceFact.objects.count()),(1,"DIA",2))
        changed=SEA.replace("Aprobado","En calificación")
        with patch("apps.knowledge.connectors.sea.fetch_html",return_value=(changed,"b"*64,self.sea_sub.project_url)),patch("apps.knowledge.sea_sync._materialize",side_effect=ValueError("parser roto")):failed=sync_sea_regulatory_context()
        self.assertEqual(failed.estado,"parcial");self.assertEqual(self.sea.records.get().current_snapshot_id,old);self.assertEqual(SeaProjectFact.objects.count(),1);self.assertEqual(self.sea.sync_state.metadata["materialization_status"],"partial")

    def test_api_provenance_auth_governance_and_strict_fields(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):sync_snifa_regulatory_context()
        client=APIClient();self.assertIn(client.get("/api/knowledge/snifa/references/").status_code,(401,403));client.force_authenticate(self.user);response=client.get("/api/knowledge/snifa/references/?region=Biobío");self.assertEqual(response.status_code,200);self.assertEqual(response.data["results"][0]["source_code"],"snifa");self.assertEqual(client.get("/api/knowledge/snifa/subscriptions/").status_code,403)
        client.force_authenticate(self.admin);self.assertEqual(client.get("/api/knowledge/snifa/subscriptions/").status_code,200);self.assertEqual(client.post("/api/knowledge/sea/subscriptions/",{"project_key":"X","project_url":"https://seia.sea.gob.cl/expediente/ficha/2","label":"X","raw_payload":{}},format="json").status_code,400)

    def test_facts_are_immutable(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):sync_snifa_regulatory_context()
        with patch("apps.knowledge.connectors.sea.fetch_html",return_value=(SEA,"a"*64,self.sea_sub.project_url)):sync_sea_regulatory_context()
        fact=SeaProjectFact.objects.get();fact.name="otro"
        with self.assertRaises(ValidationError):fact.save()
        for model in (SnifaOpenDatasetFact, SnifaRegulatoryReferenceFact, SeaProjectFact, SeaRcaReferenceFact):
            with self.assertRaises(ValidationError):model.objects.update(title="adulterado")
            with self.assertRaises(ValidationError):model.objects.all().delete()
            with self.assertRaises(ValidationError):model.objects.bulk_create([])

    def test_fact_contract_rejects_direct_semantic_tampering(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):sync_snifa_regulatory_context()
        with patch("apps.knowledge.connectors.sea.fetch_html",return_value=(SEA,"a"*64,self.sea_sub.project_url)):sync_sea_regulatory_context()
        dataset_snapshot=SnifaOpenDatasetFact.objects.first().snapshot; values=build_snifa_dataset_fact_payload(dataset_snapshot);values["title"]="Inventado"
        with self.assertRaises(ValidationError):SnifaOpenDatasetFact.objects.create(snapshot=dataset_snapshot,**values)
        reference_snapshot=SnifaRegulatoryReferenceFact.objects.get().snapshot;values=build_snifa_reference_fact_payload(reference_snapshot);values["status_raw"]="Inventado"
        with self.assertRaises(ValidationError):SnifaRegulatoryReferenceFact.objects.create(snapshot=reference_snapshot,**values)
        project=SeaProjectFact.objects.get();values=build_sea_project_fact_payload(project.snapshot);values["holder_name"]="Inventado"
        with self.assertRaises(ValidationError):SeaProjectFact.objects.create(snapshot=project.snapshot,**values)
        rca=project.rca_references.first();values=build_sea_rca_fact_payload(project,{"document_key":rca.document_key});values["document_url"]="https://seia.sea.gob.cl/expediente/documentos/inventado"
        with self.assertRaises(ValidationError):SeaRcaReferenceFact.objects.create(project_fact=project,**values)
        values=build_sea_rca_fact_payload(project,{"document_key":rca.document_key});values["document_key"]="inventado"
        with self.assertRaises(ValidationError):SeaRcaReferenceFact.objects.create(project_fact=project,**values)

    def test_first_partial_is_not_published_and_retry_reuses_snapshots(self):
        responses=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=responses),patch("apps.knowledge.snifa_sync._materialize",side_effect=ValueError("normalizacion rota")):
            failed=sync_snifa_regulatory_context()
        snapshot_count=ExternalSnapshot.objects.filter(source=self.snifa).count()
        self.assertGreater(snapshot_count,0);self.assertEqual(failed.estado,"parcial");self.assertEqual(self.snifa.records.count(),0);self.assertEqual(SnifaOpenDatasetFact.objects.count()+SnifaRegulatoryReferenceFact.objects.count(),0);self.assertEqual(source_freshness(self.snifa),"parcial_sin_version_publicada")
        client=APIClient();client.force_authenticate(self.user);self.assertEqual(client.get("/api/knowledge/snifa/references/").data["count"],0)
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=responses):successful=sync_snifa_regulatory_context()
        self.assertIn(successful.estado,("actualizada","sin_cambios"));self.assertEqual(ExternalSnapshot.objects.filter(source=self.snifa).count(),snapshot_count);self.assertEqual(self.snifa.records.count(),3);self.assertEqual(SnifaOpenDatasetFact.objects.count()+SnifaRegulatoryReferenceFact.objects.count(),3)

    def test_partial_restores_complete_existing_publication(self):
        with patch("apps.knowledge.connectors.snifa.fetch_html",side_effect=[(CATALOG,"a"*64,"https://snifa.sma.gob.cl/DatosAbiertos"),(SNIFA,"b"*64,self.snifa_sub.source_url)]):sync_snifa_regulatory_context()
        record=self.snifa.records.get(external_id="sanctioning:D-001-2026")
        fields=("current_snapshot_id","kind","canonical_key","title","source_url","published_at","upstream_updated_at","estado","metadata","last_seen_at")
        before={field:getattr(record,field) for field in fields};payload=dict(record.current_snapshot.raw_payload);payload["status_raw"]="Finalizado"
        changed=ConnectorRecord(external_id=record.external_id,kind="snifa_regulatory_reference",canonical_key="CAMBIADA",title="Titulo cambiado",source_url="https://snifa.sma.gob.cl/Sancionatorio/Ficha/2",payload=payload,metadata={"cambiada":True})
        with patch.object(SnifaPublicConnector,"fetch",return_value=ConnectorBatch(records=[changed],authoritative_full_snapshot=False)),patch("apps.knowledge.snifa_sync._materialize",side_effect=ValueError("normalizacion rota")):
            failed=sync_snifa_regulatory_context()
        record.refresh_from_db();self.assertEqual(failed.estado,"parcial");self.assertEqual({field:getattr(record,field) for field in fields},before);self.assertEqual(ExternalSnapshot.objects.filter(source=self.snifa,external_id=record.external_id).count(),2);self.assertEqual(SnifaRegulatoryReferenceFact.objects.filter(snapshot__external_id=record.external_id).count(),1);self.assertEqual(source_freshness(self.snifa),"parcial_con_ultima_version_disponible")


class RegulatoryPostgresConcurrencyTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor!="postgresql":return super()._fixture_teardown()
        tables=connection.introspection.table_names()
        if tables:
            with connection.cursor() as cursor:cursor.execute("TRUNCATE "+", ".join(connection.ops.quote_name(table) for table in tables)+" RESTART IDENTITY CASCADE")

    def test_snifa_sync_is_serialized_and_state_consistent(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        ensure_environmental_source_registry();entered=Event();release=Event();results=[];errors=[]
        record=ConnectorRecord(external_id="dataset:test",kind="snifa_open_dataset",canonical_key="test",title="Test",source_url="https://snifa.sma.gob.cl/DatosAbiertos",payload={"dataset_code":"test","title":"Test","description":"","publisher":"Superintendencia del Medio Ambiente","source_url":"https://snifa.sma.gob.cl/DatosAbiertos"})
        def fetch(connector,state):entered.set();release.wait(10);return ConnectorBatch(records=[record],authoritative_full_snapshot=False)
        def execute():
            close_old_connections()
            try:results.append(sync_snifa_regulatory_context())
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        with patch.object(SnifaPublicConnector,"fetch",fetch):
            first=Thread(target=execute);first.start();self.assertTrue(entered.wait(10));second=Thread(target=execute);second.start();second.join(10);release.set();first.join(20)
        self.assertEqual((len(results),len(errors)),(1,1));self.assertIn("sincronizando",str(errors[0]));self.assertEqual(SnifaOpenDatasetFact.objects.count(),1);self.assertIn(results[0].estado,("actualizada","sin_cambios"))
