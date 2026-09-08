from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models,transaction
from django.utils import timezone
from ..models import WorkGeolocationRevision,WorkTerritorialObservationRevision
from ..models.geospatial_context import _observation_creation
from ..permissions import Permission,require_tenant_permission,require_work_access

from .territorial_contract import CONTRACT,build_geolocation_snapshot,build_simbio_source_snapshot,build_layer_catalog_snapshot,build_results_snapshot,build_territorial_summary,canonical_hash,compute_basis_hash,compute_result_hash,current_simbio_facts
def _hash(value):return canonical_hash(value)
def location_payload(latitude,longitude,srid,capture_method,accuracy_m,source_reference):return {"latitude":format(Decimal(str(latitude)).normalize(),"f"),"longitude":format(Decimal(str(longitude)).normalize(),"f"),"srid":srid,"capture_method":capture_method,"accuracy_m":format(Decimal(str(accuracy_m)).normalize(),"f") if accuracy_m is not None else None,"source_reference":source_reference or ""}
@transaction.atomic
def set_work_geolocation(user,organization,work,**data):
    require_tenant_permission(user,organization,Permission.WORK_UPDATE);require_work_access(user,organization,work);work.__class__.objects.select_for_update().get(pk=work.pk)
    allowed={"latitude","longitude","capture_method","accuracy_m","source_reference","note"}
    if set(data)-allowed:raise ValidationError("Campos no permitidos.")
    payload=location_payload(data["latitude"],data["longitude"],4326,data["capture_method"],data.get("accuracy_m"),data.get("source_reference",""));digest=_hash(payload);latest=WorkGeolocationRevision.objects.filter(work=work,is_latest=True).first()
    if latest and latest.coordinate_hash==digest:return latest,False
    if latest:WorkGeolocationRevision.objects.filter(pk=latest.pk).update(is_latest=False)
    item=WorkGeolocationRevision(organization=organization,work=work,revision=(latest.revision+1 if latest else 1),is_latest=True,latitude=data["latitude"],longitude=data["longitude"],srid=4326,capture_method=data["capture_method"],accuracy_m=data.get("accuracy_m"),source_reference=data.get("source_reference",""),note=data.get("note",""),coordinate_hash=digest,created_by=user);item.save();return item,True
def get_work_territorial_readiness(work):
    from apps.knowledge.models import EnvironmentalSource
    from apps.knowledge.services import source_freshness
    if not WorkGeolocationRevision.objects.filter(work=work,is_latest=True).exists():return "no_location"
    source=EnvironmentalSource.objects.get(codigo="simbio")
    if source_freshness(source) not in ("actualizado","proximo_a_vencer"):return "simbio_not_ready"
    try:build_layer_catalog_snapshot()
    except ValidationError:return "layer_catalog_incomplete"
    return "ready"
def observe_work_territorial_context(user,organization,work):
    from apps.knowledge.models import EnvironmentalSource
    from apps.knowledge.simbio_spatial_query import query_simbio_layer_at_point
    require_tenant_permission(user,organization,Permission.PROFILE_MANAGE);require_tenant_permission(user,organization,Permission.WORK_VIEW);require_work_access(user,organization,work)
    if get_work_territorial_readiness(work)!="ready":raise ValidationError("Contexto territorial no disponible.")
    location=WorkGeolocationRevision.objects.get(work=work,is_latest=True);source=EnvironmentalSource.objects.select_related("sync_state").get(codigo="simbio");facts=current_simbio_facts();location_snap=build_geolocation_snapshot(location);source_snap=build_simbio_source_snapshot(source);catalog=build_layer_catalog_snapshot(facts);layers=[]
    for fact in facts:
        mode="intersects" if fact.service_code=="SIMBIO_ECORREGIONES" else "proximity";features=query_simbio_layer_at_point(fact,location.latitude,location.longitude,mode);layers.append({"service_code":fact.service_code,"layer_id":fact.layer_id,"layer_name":fact.layer_name,"query_mode":mode,"features":features})
    results=build_results_snapshot(catalog,layers);summary=build_territorial_summary(results);basis=compute_basis_hash(CONTRACT,location_snap,source_snap,catalog);result_hash=compute_result_hash(basis,results,summary)
    with transaction.atomic():
        work.__class__.objects.select_for_update().get(pk=work.pk)
        if build_geolocation_snapshot(WorkGeolocationRevision.objects.get(work=work,is_latest=True))!=location_snap or build_simbio_source_snapshot()!=source_snap or build_layer_catalog_snapshot()!=catalog:raise ValidationError("La base territorial cambio durante la consulta; reintente.")
        latest=WorkTerritorialObservationRevision.objects.filter(work=work,is_latest=True).first()
        if latest:WorkTerritorialObservationRevision.objects.filter(pk=latest.pk).update(is_latest=False)
        token=_observation_creation.set(True)
        try:item=WorkTerritorialObservationRevision(organization=organization,work=work,geolocation_revision=location,revision=(latest.revision+1 if latest else 1),is_latest=True,geolocation_snapshot=location_snap,source_snapshot=source_snap,layer_catalog_snapshot=catalog,results_snapshot=results,summary_snapshot=summary,basis_hash=basis,result_hash=result_hash,observed_by=user);item.save()
        finally:_observation_creation.reset(token)
    return item,not latest or latest.result_hash!=result_hash
def get_work_territorial_observation_freshness(work,observation=None,now=None):
    from apps.knowledge.models import EnvironmentalSource,SimbioGeoLayerFact
    from apps.knowledge.services import source_freshness
    observation=observation or WorkTerritorialObservationRevision.objects.filter(work=work,is_latest=True).first()
    if not observation:return None
    if observation.geolocation_revision_id!=WorkGeolocationRevision.objects.get(work=work,is_latest=True).id:return "stale_location"
    if observation.observation_contract_version!=CONTRACT:return "stale_observation_contract"
    current={(f.service_code,f.layer_id,f.snapshot_id) for f in SimbioGeoLayerFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="simbio")}
    frozen={(f["service_code"],f["layer_id"],f["snapshot_id"]) for f in observation.layer_catalog_snapshot}
    if current!=frozen:return "stale_layer_catalog"
    source=EnvironmentalSource.objects.get(codigo="simbio")
    if source_freshness(source) not in ("actualizado","proximo_a_vencer"):return "stale_source"
    if (now or timezone.now())-observation.observed_at>timedelta(hours=source.stale_after_hours):return "stale_observation_age"
    return "fresh"
