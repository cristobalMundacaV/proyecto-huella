from datetime import date
from datetime import timedelta
from unittest.mock import patch
from threading import Thread
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections,connection
from django.test import TestCase,TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Obra,Organizacion,UsuarioOrganizacion,UsuarioObraAcceso,WorkGeolocationRevision,WorkTerritorialObservationRevision
from apps.knowledge.bootstrap import ensure_environmental_source_registry
from apps.knowledge.geo_sync import sync_simbio_geo_catalog
from apps.knowledge.models import EnvironmentalSource,SimbioGeoLayerFact
from apps.knowledge.test_geo_sources import arcgis_fetch
from .services.geospatial_context import get_work_territorial_observation_freshness,get_work_territorial_readiness,observe_work_territorial_context,set_work_geolocation
from .permissions import Permission,ROLE_PERMISSIONS
from .services.territorial_contract import build_layer_catalog_snapshot,build_results_snapshot,build_territorial_summary,compute_feature_hash
class WorkGeolocationTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_superuser("geo","geo@example.cl","x");self.org=Organizacion.objects.create(nombre="Geo");self.work=Obra.objects.create(organizacion=self.org,nombre="Obra",fecha_inicio=date(2026,1,1))
    def test_location_versioning_hash_validation_and_immutability(self):
        first,created=set_work_geolocation(self.user,self.org,self.work,latitude="-37.4698",longitude="-72.3537",capture_method="gps",accuracy_m="8.5",source_reference="Terreno",note="a");self.assertTrue(created)
        same,created=set_work_geolocation(self.user,self.org,self.work,latitude="-37.469800",longitude="-72.353700",capture_method="gps",accuracy_m="8.500",source_reference="Terreno",note="otra");self.assertFalse(created);self.assertEqual(same.pk,first.pk)
        second,created=set_work_geolocation(self.user,self.org,self.work,latitude="-37.47",longitude="-72.35",capture_method="manual");self.assertEqual(second.revision,2);self.assertFalse(WorkGeolocationRevision.objects.get(pk=first.pk).is_latest)
        second.note="x"
        with self.assertRaises(ValidationError):second.save()
        with self.assertRaises(ValidationError):WorkGeolocationRevision.objects.update(note="x")
        with self.assertRaises(ValidationError):WorkGeolocationRevision.objects.all().delete()
        with self.assertRaises(ValidationError):WorkTerritorialObservationRevision.objects.create(organization=self.org,work=self.work,geolocation_revision=second,revision=1,is_latest=True,source_snapshot={},layer_catalog_snapshot=[],results_snapshot={},summary_snapshot={},basis_hash="x",result_hash="x",observed_by=self.user)
    def test_invalid_coordinates(self):
        for values in ({"latitude":91,"longitude":0,"capture_method":"manual"},{"latitude":0,"longitude":181,"capture_method":"manual"},{"latitude":0,"longitude":0,"capture_method":"manual","accuracy_m":-1}):
            with self.assertRaises(ValidationError):set_work_geolocation(self.user,self.org,self.work,**values)

class TerritorialObservationTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_superuser("territorial","territorial@example.cl","x");self.org=Organizacion.objects.create(nombre="Geo");self.work=Obra.objects.create(organizacion=self.org,nombre="Obra",fecha_inicio=date(2026,1,1));ensure_environmental_source_registry()
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):sync_simbio_geo_catalog()
        self.location,_=set_work_geolocation(self.user,self.org,self.work,latitude="-37.4698",longitude="-72.3537",capture_method="gps")
    def feature_query(self,fact,*args):
        layer=next(x for x in build_layer_catalog_snapshot() if x["fact_id"]==fact.id);attrs={fact.object_id_field:fact.layer_id+1,"NAME":fact.layer_name};item={"object_id":fact.layer_id+1,"display_name":fact.layer_name,"proximity_band":"intersects","attributes":attrs};item["feature_hash"]=compute_feature_hash(layer,item);return [item]
    def test_governed_observation_hashes_refresh_and_freshness(self):
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=self.feature_query):first,changed=observe_work_territorial_context(self.user,self.org,self.work)
        self.assertTrue(changed);self.assertEqual(first.summary_snapshot["layer_count"],8);self.assertEqual(first.summary_snapshot["ecoregion_intersections"],2);self.assertEqual(get_work_territorial_observation_freshness(self.work,first),"fresh")
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=self.feature_query):second,changed=observe_work_territorial_context(self.user,self.org,self.work)
        self.assertFalse(changed);self.assertEqual((second.revision,second.result_hash),(2,first.result_hash));self.assertFalse(type(first).objects.get(pk=first.pk).is_latest)
        with self.assertRaises(ValidationError):type(first).objects.update(result_hash="0"*64)
        with self.assertRaises(ValidationError):type(first).objects.update(is_latest=True)
        with self.assertRaises(ValidationError):type(first).objects.all().delete()
        with self.assertRaises(ValidationError):type(first).objects.bulk_create([])
        self.assertEqual(type(first).objects.filter(pk=first.pk).update(is_latest=False),1)
        set_work_geolocation(self.user,self.org,self.work,latitude="-38",longitude="-72",capture_method="manual");self.assertEqual(get_work_territorial_observation_freshness(self.work,second),"stale_location")
    def test_layer_seven_failure_keeps_previous_latest(self):
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=self.feature_query):first,_=observe_work_territorial_context(self.user,self.org,self.work)
        calls=0
        def fail(fact,*args):
            nonlocal calls;calls+=1
            if calls==7:raise ValueError("upstream roto")
            return self.feature_query(fact)
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=fail),self.assertRaises(ValueError):observe_work_territorial_context(self.user,self.org,self.work)
        self.assertEqual(type(first).objects.count(),1);self.assertTrue(type(first).objects.get().is_latest)
    def test_layer_eight_and_attribute_failures_keep_previous_latest(self):
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=self.feature_query):first,_=observe_work_territorial_context(self.user,self.org,self.work)
        for failure_call in (8, 3):
            calls=0
            def fail(fact,*args):
                nonlocal calls;calls+=1
                if calls==failure_call:raise ValueError("attribute batch upstream secret=hidden")
                return self.feature_query(fact)
            with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=fail),self.assertRaises(ValueError):observe_work_territorial_context(self.user,self.org,self.work)
            self.assertEqual(type(first).objects.count(),1);self.assertTrue(type(first).objects.get().is_latest)
    def test_feature_and_summary_tampering_are_rejected(self):
        catalog=build_layer_catalog_snapshot();layers=[]
        for fact in SimbioGeoLayerFact.objects.order_by("service_code","layer_id"):
            mode="intersects" if fact.service_code=="SIMBIO_ECORREGIONES" else "proximity";layers.append({"service_code":fact.service_code,"layer_id":fact.layer_id,"layer_name":fact.layer_name,"query_mode":mode,"features":self.feature_query(fact)})
        results=build_results_snapshot(catalog,layers);summary=build_territorial_summary(results);self.assertEqual(summary["layer_count"],8)
        bad=results["layers"][0]["features"][0];bad["feature_hash"]="0"*64
        with self.assertRaises(ValidationError):build_results_snapshot(catalog,results["layers"])
    def test_freshness_contract_source_age_and_catalog(self):
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=self.feature_query):item,_=observe_work_territorial_context(self.user,self.org,self.work)
        item.observation_contract_version="old";self.assertEqual(get_work_territorial_observation_freshness(self.work,item),"stale_observation_contract");item.refresh_from_db()
        source=EnvironmentalSource.objects.get(codigo="simbio");state=source.sync_state;state.estado="parcial";state.save();self.assertEqual(get_work_territorial_observation_freshness(self.work,item),"stale_source")
        state.estado="actualizada";state.save();WorkTerritorialObservationRevision._base_manager.filter(pk=item.pk).update(observed_at=timezone.now()-timedelta(hours=source.stale_after_hours+1));item.refresh_from_db();self.assertEqual(get_work_territorial_observation_freshness(self.work,item),"stale_observation_age")
        WorkTerritorialObservationRevision._base_manager.filter(pk=item.pk).update(observed_at=timezone.now());item.refresh_from_db()
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch(True)):sync_simbio_geo_catalog()
        self.assertEqual(get_work_territorial_observation_freshness(self.work,item),"stale_layer_catalog")
    def test_readiness_contract(self):
        self.assertEqual(get_work_territorial_readiness(self.work),"ready")
        WorkGeolocationRevision._base_manager.filter(pk=self.location.pk).update(is_latest=False)
        self.assertEqual(get_work_territorial_readiness(self.work),"no_location")
        WorkGeolocationRevision._base_manager.filter(pk=self.location.pk).update(is_latest=True)
        state=EnvironmentalSource.objects.get(codigo="simbio").sync_state
        successful_at=state.last_successful_sync_at
        for status in ("nunca_sincronizada", "error", "parcial"):
            state.estado=status;state.last_successful_sync_at=None if status=="nunca_sincronizada" else successful_at;state.save(update_fields=["estado","last_successful_sync_at"])
            self.assertEqual(get_work_territorial_readiness(self.work),"simbio_not_ready")
        state.estado="actualizada";state.last_successful_sync_at=successful_at;state.save(update_fields=["estado","last_successful_sync_at"])
        facts=list(SimbioGeoLayerFact.objects.order_by("id")[:2])
        facts[0].snapshot.current_for.update(current_snapshot_id=facts[1].snapshot_id)
        self.assertEqual(get_work_territorial_readiness(self.work),"layer_catalog_incomplete")

class GeoRbacTests(TestCase):
    def setUp(self):
        self.org=Organizacion.objects.create(nombre="Geo RBAC");self.other=Organizacion.objects.create(nombre="Otra");self.work=Obra.objects.create(organizacion=self.org,nombre="Obra",fecha_inicio=date(2026,1,1));self.outside=Obra.objects.create(organizacion=self.org,nombre="Fuera",fecha_inicio=date(2026,1,1))
    def _member(self,role,scope=UsuarioOrganizacion.Alcance.ORGANIZACION):
        user=get_user_model().objects.create_user(f"{role}-{scope}-{get_user_model().objects.count()}",password="x");membership=UsuarioOrganizacion.objects.create(user=user,organizacion=self.org,rol=role,alcance=scope)
        if scope==UsuarioOrganizacion.Alcance.OBRAS:UsuarioObraAcceso.objects.create(usuario_organizacion=membership,obra=self.work)
        return user
    def test_http_and_service_permissions_follow_role_contract(self):
        location_url=f"/api/organizaciones/{self.org.organizacion_id}/obras/{self.work.pk}/geo/ubicacion/";context_url=f"/api/organizaciones/{self.org.organizacion_id}/obras/{self.work.pk}/geo/contexto/"
        payload={"latitude":"-37","longitude":"-72","capture_method":"manual"}
        for role in UsuarioOrganizacion.Rol.values:
            user=self._member(role);client=APIClient();client.force_authenticate(user)
            self.assertEqual(client.get(location_url).status_code,200 if Permission.WORK_VIEW in ROLE_PERMISSIONS[role] else 403)
            self.assertEqual(client.post(location_url,payload,format="json").status_code in (200,201),Permission.WORK_UPDATE in ROLE_PERMISSIONS[role])
            self.assertEqual(client.get(context_url).status_code,200 if {Permission.PROFILE_VIEW,Permission.WORK_VIEW}<=ROLE_PERMISSIONS[role] else 403)
        reader=self._member(UsuarioOrganizacion.Rol.LECTOR,UsuarioOrganizacion.Alcance.OBRAS);client=APIClient();client.force_authenticate(reader)
        outside=f"/api/organizaciones/{self.org.organizacion_id}/obras/{self.outside.pk}/geo/ubicacion/"
        self.assertEqual(client.get(outside).status_code,404)
        stranger=get_user_model().objects.create_user("stranger");client.force_authenticate(stranger);self.assertEqual(client.get(location_url).status_code,404)
        with self.assertRaises(Exception):set_work_geolocation(reader,self.org,self.work,**payload)

class GeoConcurrencyTests(TransactionTestCase):
    def _fixture_teardown(self):
        if connection.vendor!="postgresql":return super()._fixture_teardown()
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables=[connection.ops.quote_name(row[0]) for row in cursor.fetchall()]
            if tables:cursor.execute("TRUNCATE "+", ".join(tables)+" RESTART IDENTITY CASCADE")
    def _base(self):
        user=get_user_model().objects.create_superuser("concurrent","concurrent@example.cl","x");org=Organizacion.objects.create(nombre="Geo concurrency");work=Obra.objects.create(organizacion=org,nombre="Obra",fecha_inicio=date(2026,1,1));return user,org,work
    def _run(self,functions):
        results=[];errors=[]
        def execute(fn):
            close_old_connections()
            try:results.append(fn())
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        threads=[Thread(target=execute,args=(fn,)) for fn in functions]
        for thread in threads:thread.start()
        for thread in threads:thread.join(30)
        return results,errors
    def test_location_concurrency(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        user,org,work=self._base();results,errors=self._run([lambda:set_work_geolocation(user,org,work,latitude=-37,longitude=-72,capture_method="manual"),lambda:set_work_geolocation(user,org,work,latitude=-38,longitude=-73,capture_method="gps")])
        self.assertFalse(errors);self.assertEqual(WorkGeolocationRevision.objects.filter(work=work).count(),2);self.assertEqual(list(WorkGeolocationRevision.objects.filter(work=work).order_by("revision").values_list("revision",flat=True)),[1,2]);self.assertEqual(WorkGeolocationRevision.objects.filter(work=work,is_latest=True).count(),1)
    def test_identical_location_concurrency_is_idempotent(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        user,org,work=self._base();call=lambda:set_work_geolocation(user,org,work,latitude=-37,longitude=-72,capture_method="manual")
        results,errors=self._run([call,call]);self.assertFalse(errors);self.assertEqual(WorkGeolocationRevision.objects.filter(work=work).count(),1);self.assertEqual(sorted(created for _,created in results),[False,True])
    def test_observation_concurrency(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        user,org,work=self._base();ensure_environmental_source_registry()
        with patch("apps.knowledge.connectors.simbio.fetch_arcgis_json",side_effect=arcgis_fetch()):sync_simbio_geo_catalog()
        set_work_geolocation(user,org,work,latitude=-37,longitude=-72,capture_method="manual")
        def empty(*args):return []
        with patch("apps.knowledge.simbio_spatial_query.query_simbio_layer_at_point",side_effect=empty):results,errors=self._run([lambda:observe_work_territorial_context(user,org,work),lambda:observe_work_territorial_context(user,org,work)])
        self.assertFalse(errors);self.assertEqual(WorkTerritorialObservationRevision.objects.filter(work=work).count(),2);self.assertEqual(WorkTerritorialObservationRevision.objects.filter(work=work,is_latest=True).count(),1)
