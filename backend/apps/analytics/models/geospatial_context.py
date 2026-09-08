import hashlib,json
from contextvars import ContextVar
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from .platform import Organizacion
from .operational_context import Obra

_observation_creation=ContextVar("territorial_observation_creation",default=False)
class VersionedGeoQuerySet(models.QuerySet):
    def update(self,**kwargs):
        if kwargs=={"is_latest":False}:return super().update(**kwargs)
        raise ValidationError("Use el servicio de versionado geoespacial.")
    def delete(self):raise ValidationError("El historial geoespacial es inmutable.")
    def bulk_create(self,*args,**kwargs):raise ValidationError("Use el servicio de versionado geoespacial.")
class ImmutableGeoModel(models.Model):
    objects=VersionedGeoQuerySet.as_manager()
    class Meta:abstract=True
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("La revision geoespacial es inmutable.")
        self.full_clean();super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError("La revision geoespacial es inmutable.")

class WorkGeolocationRevision(ImmutableGeoModel):
    class CaptureMethod(models.TextChoices):MANUAL="manual","Manual";GPS="gps","GPS";SURVEY="survey","Levantamiento";IMPORT="import","Importación"
    organization=models.ForeignKey(Organizacion,on_delete=models.PROTECT);work=models.ForeignKey(Obra,on_delete=models.PROTECT,related_name="geolocation_revisions");revision=models.PositiveIntegerField();is_latest=models.BooleanField(default=True)
    latitude=models.DecimalField(max_digits=12,decimal_places=8);longitude=models.DecimalField(max_digits=13,decimal_places=8);srid=models.PositiveIntegerField(default=4326);capture_method=models.CharField(max_length=20,choices=CaptureMethod.choices);accuracy_m=models.DecimalField(max_digits=12,decimal_places=3,null=True,blank=True);source_reference=models.CharField(max_length=500,blank=True);note=models.TextField(blank=True);coordinate_hash=models.CharField(max_length=64);created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);created_at=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["work","revision"],name="analytics_geo_location_revision"),models.UniqueConstraint(fields=["work"],condition=models.Q(is_latest=True),name="analytics_geo_one_latest_location")]
    def clean(self):
        if self.organization_id!=self.work.organizacion_id or self.srid!=4326 or not Decimal("-90")<=self.latitude<=Decimal("90") or not Decimal("-180")<=self.longitude<=Decimal("180") or self.accuracy_m is not None and self.accuracy_m<0:raise ValidationError("Ubicacion WGS84 invalida.")
        from ..permissions import Permission,require_tenant_permission,require_work_access
        try:require_tenant_permission(self.created_by,self.organization,Permission.WORK_UPDATE);require_work_access(self.created_by,self.organization,self.work)
        except Exception as exc:raise ValidationError("Creador sin autorizacion sobre la obra.") from exc
        from ..services.geospatial_context import _hash,location_payload
        expected=_hash(location_payload(self.latitude,self.longitude,self.srid,self.capture_method,self.accuracy_m,self.source_reference))
        if self.coordinate_hash!=expected:raise ValidationError("Hash de ubicacion invalido.")
        previous=WorkGeolocationRevision.objects.filter(work_id=self.work_id).order_by("-revision").first()
        if self.revision!=(previous.revision+1 if previous else 1):raise ValidationError("Revision de ubicacion no secuencial.")

class WorkTerritorialObservationRevision(ImmutableGeoModel):
    organization=models.ForeignKey(Organizacion,on_delete=models.PROTECT);work=models.ForeignKey(Obra,on_delete=models.PROTECT,related_name="territorial_observations");geolocation_revision=models.ForeignKey(WorkGeolocationRevision,on_delete=models.PROTECT);revision=models.PositiveIntegerField();is_latest=models.BooleanField(default=True);observation_contract_version=models.CharField(max_length=80,default="territorial-observation-1");geolocation_snapshot=models.JSONField();source_snapshot=models.JSONField();layer_catalog_snapshot=models.JSONField();results_snapshot=models.JSONField();summary_snapshot=models.JSONField();basis_hash=models.CharField(max_length=64);result_hash=models.CharField(max_length=64);observed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);observed_at=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["work","revision"],name="analytics_geo_observation_revision"),models.UniqueConstraint(fields=["work"],condition=models.Q(is_latest=True),name="analytics_geo_one_latest_observation")]
    def save(self,*args,**kwargs):
        if not _observation_creation.get():raise ValidationError("Use observe_work_territorial_context().")
        super().save(*args,**kwargs)
    def clean(self):
        if self.organization_id!=self.work.organizacion_id or self.geolocation_revision.work_id!=self.work_id or not self.geolocation_revision.is_latest:raise ValidationError("Contrato territorial inconsistente.")
        previous=WorkTerritorialObservationRevision.objects.filter(work_id=self.work_id).order_by("-revision").first()
        if self.revision!=(previous.revision+1 if previous else 1):raise ValidationError("Revision territorial no secuencial.")
        from ..services.territorial_contract import build_geolocation_snapshot,build_simbio_source_snapshot,build_layer_catalog_snapshot,build_results_snapshot,build_territorial_summary,compute_basis_hash,compute_result_hash
        location=build_geolocation_snapshot(self.geolocation_revision);source=build_simbio_source_snapshot();catalog=build_layer_catalog_snapshot();results=build_results_snapshot(catalog,self.results_snapshot.get("layers",[]));summary=build_territorial_summary(results)
        if self.geolocation_snapshot!=location or self.source_snapshot!=source or self.layer_catalog_snapshot!=catalog or self.results_snapshot!=results or self.summary_snapshot!=summary:raise ValidationError("Snapshots territoriales adulterados.")
        basis=compute_basis_hash(self.observation_contract_version,location,self.source_snapshot,catalog)
        if self.basis_hash!=basis or self.result_hash!=compute_result_hash(basis,results,summary):raise ValidationError("Hashes territoriales invalidos.")
