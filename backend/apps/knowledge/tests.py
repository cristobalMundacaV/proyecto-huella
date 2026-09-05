from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .bootstrap import ensure_environmental_source_registry
from .connectors.base import ConnectorBatch,ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource,ExternalRecord,ExternalSnapshot,SourceState,SyncRun
from .services import MAX_TEXT_CHARS,source_freshness,sync_environmental_source

class KnowledgeHubTests(TestCase):
    def setUp(self):
        self.source=EnvironmentalSource.objects.create(codigo="fake-source",nombre="Fake",organismo="Tests",connector_key="fake",tipo_acceso="REST",nivel_autoridad="test",stale_after_hours=10)
        SourceState.objects.create(source=self.source);FakeEnvironmentalConnector.error=None
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[ConnectorRecord("one","generic",payload={"b":2,"a":1},title="One")])
    def test_bootstrap_idempotente_y_sin_secretos(self):
        ensure_environmental_source_registry();ensure_environmental_source_registry()
        self.assertEqual(EnvironmentalSource.objects.exclude(pk=self.source.pk).count(),8)
        for source in EnvironmentalSource.objects.exclude(pk=self.source.pk):
            self.assertNotIn("token",str(source.__dict__).lower());self.assertTrue(hasattr(source,"sync_state"))
    def test_sync_deduplica_hash_canonico_y_conserva_historia(self):
        first=sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();self.assertEqual(first.created,1);checksum=self.source.sync_state.last_checksum
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[ConnectorRecord("one","generic",payload={"a":1,"b":2},title="One")])
        second=sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();self.assertEqual(second.unchanged,1);self.assertEqual(ExternalSnapshot.objects.count(),1);self.assertEqual(self.source.sync_state.last_checksum,checksum)
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[ConnectorRecord("one","generic",payload={"a":3},title="One changed")])
        third=sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();self.assertEqual(third.modified,1);self.assertEqual(ExternalSnapshot.objects.count(),2);self.assertEqual(ExternalRecord.objects.get().title,"One changed");self.assertNotEqual(self.source.sync_state.last_checksum,checksum)
    def test_checksum_global_no_depende_del_orden_y_error_lo_conserva(self):
        records=[ConnectorRecord("b","generic",payload={"x":2}),ConnectorRecord("a","generic",payload={"x":1})];FakeEnvironmentalConnector.batch=ConnectorBatch(records=records);sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();checksum=self.source.sync_state.last_checksum
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=list(reversed(records)));sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();self.assertEqual(self.source.sync_state.last_checksum,checksum)
        FakeEnvironmentalConnector.error=RuntimeError("fallo");sync_environmental_source(self.source);self.source.sync_state.refresh_from_db();self.assertEqual(self.source.sync_state.last_checksum,checksum)
    def test_metadata_semantica_crea_snapshot_y_reconcilia_envelope_completo(self):
        sync_environmental_source(self.source);record=ExternalRecord.objects.get();first_seen=record.first_seen_at
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[ConnectorRecord("one","law",payload={"a":1,"b":2},title="Nuevo",canonical_key="key-2",source_url="https://example.test/two",metadata={"estado":"nuevo"})]);sync_environmental_source(self.source);record.refresh_from_db()
        self.assertEqual(ExternalSnapshot.objects.count(),2);self.assertEqual(record.kind,"law");self.assertEqual(record.canonical_key,"key-2");self.assertEqual(record.title,"Nuevo");self.assertEqual(record.source_url,"https://example.test/two");self.assertEqual(record.metadata,{"estado":"nuevo"});self.assertEqual(record.first_seen_at,first_seen)
    def test_error_conserva_snapshot_y_audita_sanitizado(self):
        sync_environmental_source(self.source);snapshot=ExternalRecord.objects.get().current_snapshot
        FakeEnvironmentalConnector.error=RuntimeError("Authorization Bearer secret-token")
        run=sync_environmental_source(self.source);self.assertEqual(run.estado,"error");self.assertNotIn("secret-token",run.message);self.assertEqual(ExternalRecord.objects.get().current_snapshot,snapshot)
        self.assertEqual(source_freshness(self.source),"error_con_ultima_version_disponible")
    def test_primer_error_no_afirma_version_disponible(self):
        FakeEnvironmentalConnector.error=RuntimeError("fallo inicial");sync_environmental_source(self.source);self.assertEqual(source_freshness(self.source),"error_sin_version_disponible")
    def test_concurrencia_y_limite(self):
        SourceState.objects.filter(source=self.source).update(estado="sincronizando")
        with self.assertRaises(ValidationError):sync_environmental_source(self.source)
        SourceState.objects.filter(source=self.source).update(estado="nunca_sincronizada")
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[ConnectorRecord("huge","generic",text="x"*(MAX_TEXT_CHARS+1))])
        run=sync_environmental_source(self.source);self.assertEqual(run.estado,"error")
        self.assertFalse(ExternalSnapshot.objects.exists())
    def test_no_autoritativo_no_elimina_ausentes_y_freshness(self):
        sync_environmental_source(self.source);FakeEnvironmentalConnector.batch=ConnectorBatch(records=[],authoritative_full_snapshot=False);sync_environmental_source(self.source)
        self.assertEqual(ExternalRecord.objects.count(),1)
        state=self.source.sync_state;state.refresh_from_db();state.last_successful_sync_at=timezone.now()-timedelta(hours=9);state.estado="actualizada";state.save();self.assertEqual(source_freshness(self.source),"proximo_a_vencer")
        state.last_successful_sync_at=timezone.now()-timedelta(hours=11);state.save();self.assertEqual(source_freshness(self.source),"desactualizado")
    def test_snapshot_autoritativo_marca_ausencia_sin_eliminar_historia(self):
        sync_environmental_source(self.source)
        FakeEnvironmentalConnector.batch=ConnectorBatch(records=[],authoritative_full_snapshot=True)
        run=sync_environmental_source(self.source)
        self.assertEqual(run.disappeared,1);self.assertEqual(ExternalRecord.objects.get().estado,"no_observado");self.assertEqual(ExternalSnapshot.objects.count(),1)
    def test_endpoints_son_autenticados_y_exponen_historial(self):
        sync_environmental_source(self.source);base=ExternalRecord.objects.get();now=timezone.now();ExternalRecord.objects.bulk_create([ExternalRecord(source=self.source,external_id=f"record-{index}",kind="generic",current_snapshot=base.current_snapshot,first_seen_at=now,last_seen_at=now) for index in range(204)]);client=APIClient();self.assertIn(client.get("/api/knowledge/sources/").status_code,(401,403))
        client.force_authenticate(User.objects.create_user("knowledge"));self.assertEqual(client.get("/api/knowledge/sources/").status_code,200);runs=client.get("/api/knowledge/sources/fake-source/sync-runs/").data;self.assertEqual(set(runs),{"count","next","previous","results"});records=client.get("/api/knowledge/sources/fake-source/records/?page_size=999").data;self.assertEqual(records["count"],205);self.assertEqual(len(records["results"]),200);detail=client.get("/api/knowledge/sources/fake-source/records/one/").data;self.assertEqual(set(detail["snapshots"]),{"count","next","previous","results"})
    def test_bootstrap_conserva_configuracion_local_y_corrige_defaults(self):
        ensure_environmental_source_registry();retc=EnvironmentalSource.objects.get(codigo="retc");self.assertEqual(retc.tipo_acceso,"CKAN");retc.tipo_acceso="WMS";retc.nombre="Local";retc.save();ensure_environmental_source_registry();retc.refresh_from_db();self.assertEqual((retc.tipo_acceso,retc.nombre),("WMS","Local"))
    def test_snapshot_y_run_finalizados_son_inmutables(self):
        run=sync_environmental_source(self.source);snapshot=ExternalSnapshot.objects.get();snapshot.raw_text="cambio"
        with self.assertRaises(ValidationError):snapshot.save()
        run.message="cambio"
        with self.assertRaises(ValidationError):run.save()
