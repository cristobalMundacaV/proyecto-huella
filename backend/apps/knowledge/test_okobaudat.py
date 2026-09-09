from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test import TransactionTestCase
from django.db import close_old_connections,connection
from threading import Event,Thread
from rest_framework.test import APIClient
from defusedxml import ElementTree

from .bootstrap import OKOBAUDAT_MANAGED_DEFAULTS,ensure_environmental_source_registry
from .connectors.base import ConnectorBatch,ConnectorRecord
from .connectors.okobaudat import A1,A2,OekobaudatSoda4LcaConnector,parse_datastocks,parse_process_page,select_release,validate_okobaudat_url
from .models import EnvironmentalSource,ExternalRecord,ExternalSnapshot,OekobaudatDataStockFact,OekobaudatProcessFact
from .okobaudat_sync import sync_okobaudat_material_catalog

STOCKS=b'''<?xml version="1.0"?><s:dataStockList xmlns:s="http://www.ilcd-network.org/ILCD/ServiceAPI"><s:dataStock><s:uuid>11111111-1111-1111-1111-111111111111</s:uuid><s:shortName>OBD_2024_I</s:shortName><s:name xml:lang="de">Alt</s:name></s:dataStock><s:dataStock><s:uuid>22222222-2222-2222-2222-222222222222</s:uuid><s:shortName>OBD_2024_II</s:shortName><s:name xml:lang="en">Current</s:name></s:dataStock><s:dataStock><s:uuid>33333333-3333-3333-3333-333333333333</s:uuid><s:shortName>OBD_2024_II_eLCA</s:shortName><s:name xml:lang="de">Derivative</s:name></s:dataStock><s:dataStock><s:uuid>44444444-4444-4444-4444-444444444444</s:uuid><s:shortName>Projekt_EPDs</s:shortName></s:dataStock></s:dataStockList>'''
def processes(start=0,total=2,uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",version="00.01.000",compliance=A2):
    return f'''<s:dataSetList xmlns:s="http://www.ilcd-network.org/ILCD/ServiceAPI" xmlns:p="http://www.ilcd-network.org/ILCD/ServiceAPI/Process" xmlns:p2="http://www.ilcd-network.org/ILCD/ServiceAPI/v2/Process" xmlns:xlink="http://www.w3.org/1999/xlink" s:totalSize="{total}" s:startIndex="{start}" s:pageSize="1"><p:process xlink:href="https://www.oekobaudat.de/OEKOBAU.DAT/resource/processes/{uuid}?version={version}"><s:uuid>{uuid}</s:uuid><s:dataSetVersion>{version}</s:dataSetVersion><s:name xml:lang="de">Zement DE</s:name><s:name xml:lang="en">Cement EN</s:name><s:classification name="OEKOBAU.DAT"><s:class level="0" classId="1">Mineral</s:class></s:classification><p:type>EPD</p:type><p:location>DE</p:location><p:complianceSystem name="EN"><s:reference refObjectId="{compliance}"/></p:complianceSystem><p:ownership refObjectId="owner-1"/></p:process></s:dataSetList>'''.encode()

class OekobaudatContractTests(TestCase):
    def setUp(self):ensure_environmental_source_registry();self.source=EnvironmentalSource.objects.get(codigo="okobaudat")
    def test_bootstrap_and_local_configuration_preserved(self):
        self.assertEqual((self.source.connector_key,self.source.base_url,self.source.organismo),("okobaudat_soda4lca",OKOBAUDAT_MANAGED_DEFAULTS["base_url"],"BMWSB / BBSR"));self.assertTrue(self.source.sync_state.metadata["not_designed_for_product_lca"])
        self.source.base_url="https://www.oekobaudat.de/OEKOBAU.DAT/resource/custom";self.source.save();ensure_environmental_source_registry();self.source.refresh_from_db();self.assertTrue(self.source.base_url.endswith("/custom"))
    def test_datastocks_selection_exclusions_and_ambiguity(self):
        stocks=parse_datastocks(ElementTree.fromstring(STOCKS));selected,excluded,count=select_release(stocks);self.assertEqual((selected["short_name"],count),("OBD_2024_II",2));self.assertEqual(len(excluded),2)
        duplicate={**selected,"datastock_uuid":"55555555-5555-5555-5555-555555555555"}
        with self.assertRaises(ValueError):select_release(stocks+[duplicate])
    def test_process_contract_multilingual_classification_and_compliance(self):
        rows,total,start,size=parse_process_page(ElementTree.fromstring(processes(total=1)),"22222222-2222-2222-2222-222222222222");row=rows[0]
        self.assertEqual((total,start,size,row["dataset_version"],row["name"]),(1,0,1,"00.01.000","Cement EN"));self.assertEqual(row["languages"]["de"],["Zement DE"]);self.assertEqual(row["classification"][0]["path"][0]["id"],"1");self.assertEqual((row["compliance_standard_raw"],row["compliance_source_uuid"]),("EN 15804+A2",A2))
        unknown=parse_process_page(ElementTree.fromstring(processes(total=1,compliance="other")),"22222222-2222-2222-2222-222222222222")[0][0];self.assertEqual(unknown["compliance_standard_raw"],"unknown")
        a1=parse_process_page(ElementTree.fromstring(processes(total=1,compliance=A1)),"22222222-2222-2222-2222-222222222222")[0][0];self.assertEqual((a1["compliance_standard_raw"],a1["compliance_source_uuid"]),("EN 15804+A1",A1))
    def test_pagination_deduplication_and_order_independent_sync(self):
        pages=[(ElementTree.fromstring(STOCKS),"stocks"),(ElementTree.fromstring(processes(0,2)),"p0"),(ElementTree.fromstring(processes(1,2)),"p1")]
        with patch("apps.knowledge.connectors.okobaudat.fetch_okobaudat_xml",side_effect=pages):run=sync_okobaudat_material_catalog()
        self.assertEqual((run.estado,OekobaudatDataStockFact.objects.count(),OekobaudatProcessFact.objects.count()),("actualizada",4,1));state=self.source.sync_state;state.refresh_from_db();self.assertEqual(state.metadata["selected_datastock_name"],"OBD_2024_II")
        count=ExternalSnapshot.objects.filter(source=self.source).count()
        pages=[(ElementTree.fromstring(STOCKS),"stocks"),(ElementTree.fromstring(processes(0,2)),"p0"),(ElementTree.fromstring(processes(1,2)),"p1")]
        with patch("apps.knowledge.connectors.okobaudat.fetch_okobaudat_xml",side_effect=pages):second=sync_okobaudat_material_catalog()
        self.assertEqual((second.modified,ExternalSnapshot.objects.filter(source=self.source).count()),(0,count))
    def test_security(self):
        self.assertTrue(validate_okobaudat_url("https://www.oekobaudat.de/OEKOBAU.DAT/resource/datastocks/"))
        for url in ("http://www.oekobaudat.de/OEKOBAU.DAT/resource/","https://localhost/OEKOBAU.DAT/resource/","https://127.0.0.1/OEKOBAU.DAT/resource/","file:///tmp/x","ftp://www.oekobaudat.de/OEKOBAU.DAT/resource/","https://user:pass@www.oekobaudat.de/OEKOBAU.DAT/resource/","https://example.com/OEKOBAU.DAT/resource/","https://www.oekobaudat.de/other"):
            with self.assertRaises(ValueError):validate_okobaudat_url(url)

class OekobaudatPublicationTests(TestCase):
    def setUp(self):ensure_environmental_source_registry();self.source=EnvironmentalSource.objects.get(codigo="okobaudat");self.user=get_user_model().objects.create_user("ok-reader")
    def records(self,name="Cement EN"):
        stock=parse_datastocks(ElementTree.fromstring(STOCKS))[1];process=parse_process_page(ElementTree.fromstring(processes(total=1)),stock["datastock_uuid"])[0][0];process["name"]=name
        return [ConnectorRecord(external_id=f"okobaudat:datastock:{stock['datastock_uuid']}",canonical_key=stock["datastock_uuid"],kind="okobaudat_datastock",title=stock["display_name"],source_url=stock["source_url"],payload=stock),ConnectorRecord(external_id=f"okobaudat:process:{process['process_uuid']}:{process['dataset_version']}",canonical_key=f"{process['process_uuid']}:{process['dataset_version']}",kind="okobaudat_process",title=name,source_url=process["source_url"],payload=process)]
    def test_first_materialization_failure_keeps_snapshots_but_publishes_nothing(self):
        batch=ConnectorBatch(records=self.records(),authoritative_full_snapshot=True,metadata={"selected_datastock_uuid":"22222222-2222-2222-2222-222222222222"})
        with patch.object(OekobaudatSoda4LcaConnector,"fetch",return_value=batch),patch("apps.knowledge.okobaudat_sync._materialize",side_effect=ValueError("malformed process")):run=sync_okobaudat_material_catalog()
        self.assertEqual((run.estado,ExternalSnapshot.objects.filter(source=self.source).count(),ExternalRecord.objects.filter(source=self.source).count(),OekobaudatProcessFact.objects.count()),("parcial",2,0,0))
    def test_atomic_rollback_retry_immutability_and_api(self):
        metadata={"selected_datastock_uuid":"22222222-2222-2222-2222-222222222222","selected_datastock_name":"OBD_2024_II","intended_use":"building_lca","not_designed_for_product_lca":True}
        with patch.object(OekobaudatSoda4LcaConnector,"fetch",return_value=ConnectorBatch(records=self.records(),authoritative_full_snapshot=True,metadata=metadata)):sync_okobaudat_material_catalog()
        process=OekobaudatProcessFact.objects.get();old=process.snapshot_id
        changed=self.records("Changed")
        with patch.object(OekobaudatSoda4LcaConnector,"fetch",return_value=ConnectorBatch(records=changed,authoritative_full_snapshot=True,metadata=metadata)),patch("apps.knowledge.okobaudat_sync._materialize",side_effect=ValueError("bad secret=hidden")):failed=sync_okobaudat_material_catalog()
        self.assertEqual(failed.estado,"parcial");self.assertEqual(ExternalRecord.objects.get(external_id__startswith="okobaudat:process:").current_snapshot_id,old);self.assertEqual(OekobaudatProcessFact.objects.count(),1);snapshot_count=ExternalSnapshot.objects.filter(source=self.source).count()
        with patch.object(OekobaudatSoda4LcaConnector,"fetch",return_value=ConnectorBatch(records=changed,authoritative_full_snapshot=True,metadata=metadata)):retried=sync_okobaudat_material_catalog()
        self.assertNotEqual(ExternalRecord.objects.get(external_id__startswith="okobaudat:process:").current_snapshot_id,old);self.assertEqual(ExternalSnapshot.objects.filter(source=self.source).count(),snapshot_count);self.assertEqual(retried.errors,0)
        process.name="tamper"
        with self.assertRaises(ValidationError):process.save()
        for operation in (lambda:OekobaudatProcessFact.objects.update(name="x"),lambda:OekobaudatProcessFact.objects.all().delete(),lambda:OekobaudatProcessFact.objects.bulk_create([])):
            with self.assertRaises(ValidationError):operation()
        client=APIClient();client.force_authenticate(self.user);response=client.get("/api/knowledge/materials/oekobaudat/processes/?language=en&compliance=EN%2015804%2BA2");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],1);self.assertTrue(response.data["results"][0]["not_designed_for_product_lca"])

class OekobaudatPostgresConcurrencyTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor!="postgresql":return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'");tables=[connection.ops.quote_name(row[0]) for row in cursor.fetchall()]
            if tables:cursor.execute("TRUNCATE "+", ".join(tables)+" RESTART IDENTITY CASCADE")
    def test_concurrent_sync_does_not_duplicate_publication(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        ensure_environmental_source_registry();source=EnvironmentalSource.objects.get(codigo="okobaudat");entered=Event();release=Event();results=[];errors=[]
        stock=parse_datastocks(ElementTree.fromstring(STOCKS))[1];record=ConnectorRecord(external_id=f"okobaudat:datastock:{stock['datastock_uuid']}",canonical_key=stock["datastock_uuid"],kind="okobaudat_datastock",title=stock["display_name"],source_url=stock["source_url"],payload=stock)
        def fetch(connector,state):entered.set();release.wait(10);return ConnectorBatch(records=[record],authoritative_full_snapshot=True,metadata={"selected_datastock_uuid":stock["datastock_uuid"]})
        def execute():
            close_old_connections()
            try:results.append(sync_okobaudat_material_catalog())
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        with patch.object(OekobaudatSoda4LcaConnector,"fetch",fetch):
            first=Thread(target=execute);first.start();self.assertTrue(entered.wait(10));second=Thread(target=execute);second.start();second.join(10);release.set();first.join(20)
        self.assertEqual((len(results),len(errors)),(1,1));self.assertIn("sincronizando",str(errors[0]));self.assertEqual((ExternalRecord.objects.filter(source=source).count(),OekobaudatDataStockFact.objects.count()),(1,1))
