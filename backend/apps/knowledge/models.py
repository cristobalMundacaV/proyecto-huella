from django.core.exceptions import ValidationError
from django.db import models


class EnvironmentalSource(models.Model):
    class AccessType(models.TextChoices):
        REST="REST","REST"; CKAN="CKAN","CKAN"; SPARQL="SPARQL","SPARQL"; ARCGIS="ARCGIS_REST","ArcGIS REST"; WFS="WFS","WFS"; WMS="WMS","WMS"; FILE="FILE","File"; DOCUMENT_INDEX="DOCUMENT_INDEX","Document index"
    codigo=models.SlugField(max_length=80, unique=True); nombre=models.CharField(max_length=160); organismo=models.CharField(max_length=200); descripcion=models.TextField(blank=True); connector_key=models.SlugField(max_length=80)
    tipo_acceso=models.CharField(max_length=30, choices=AccessType.choices); base_url=models.URLField(blank=True); documentation_url=models.URLField(blank=True); licencia_nombre=models.CharField(max_length=160, blank=True); licencia_url=models.URLField(blank=True); atribucion_requerida=models.BooleanField(default=True); nivel_autoridad=models.CharField(max_length=60); pais=models.CharField(max_length=80, blank=True); cadencia_sugerida=models.CharField(max_length=80, blank=True); stale_after_hours=models.PositiveIntegerField(default=168); activa=models.BooleanField(default=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)


class SourceState(models.Model):
    class Status(models.TextChoices):
        NEVER="nunca_sincronizada","Nunca sincronizada"; SYNCING="sincronizando","Sincronizando"; UPDATED="actualizada","Actualizada"; UNCHANGED="sin_cambios","Sin cambios"; PARTIAL="parcial","Parcial"; ERROR="error","Error"; STALE="desactualizada","Desactualizada"
    source=models.OneToOneField(EnvironmentalSource,on_delete=models.CASCADE,related_name="sync_state"); estado=models.CharField(max_length=30,choices=Status.choices,default=Status.NEVER); last_attempt_at=models.DateTimeField(null=True,blank=True); last_successful_sync_at=models.DateTimeField(null=True,blank=True); upstream_updated_at=models.DateTimeField(null=True,blank=True); retrieved_at=models.DateTimeField(null=True,blank=True); upstream_version=models.CharField(max_length=200,blank=True); cursor=models.JSONField(null=True,blank=True); etag=models.CharField(max_length=300,blank=True); last_modified=models.CharField(max_length=300,blank=True); last_checksum=models.CharField(max_length=64,blank=True); last_error=models.TextField(blank=True); metadata=models.JSONField(default=dict,blank=True); updated_at=models.DateTimeField(auto_now=True)


class SyncRun(models.Model):
    class Trigger(models.TextChoices): MANUAL="manual","Manual"; SCHEDULED="scheduled","Scheduled"; BOOTSTRAP="bootstrap","Bootstrap"
    source=models.ForeignKey(EnvironmentalSource,on_delete=models.PROTECT,related_name="sync_runs"); trigger=models.CharField(max_length=20,choices=Trigger.choices); started_at=models.DateTimeField(); finished_at=models.DateTimeField(null=True,blank=True); estado=models.CharField(max_length=30,default="sincronizando"); upstream_version=models.CharField(max_length=200,blank=True); received=models.PositiveIntegerField(default=0); created=models.PositiveIntegerField(default=0); modified=models.PositiveIntegerField(default=0); unchanged=models.PositiveIntegerField(default=0); disappeared=models.PositiveIntegerField(default=0); errors=models.PositiveIntegerField(default=0); initial_cursor=models.JSONField(null=True,blank=True); final_cursor=models.JSONField(null=True,blank=True); metadata=models.JSONField(default=dict,blank=True); message=models.TextField(blank=True)
    def save(self,*args,**kwargs):
        if self.pk and SyncRun.objects.filter(pk=self.pk,finished_at__isnull=False).exists(): raise ValidationError("Una ejecucion finalizada es inmutable.")
        super().save(*args,**kwargs)


class ExternalSnapshot(models.Model):
    source=models.ForeignKey(EnvironmentalSource,on_delete=models.PROTECT,related_name="snapshots"); sync_run=models.ForeignKey(SyncRun,on_delete=models.PROTECT,related_name="snapshots"); external_id=models.CharField(max_length=300); record_kind=models.CharField(max_length=100); source_url=models.URLField(blank=True); published_at=models.DateTimeField(null=True,blank=True); upstream_updated_at=models.DateTimeField(null=True,blank=True); retrieved_at=models.DateTimeField(); content_hash=models.CharField(max_length=64); raw_payload=models.JSONField(null=True,blank=True); raw_text=models.TextField(blank=True); metadata=models.JSONField(default=dict,blank=True); content_type=models.CharField(max_length=120,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["source","external_id","content_hash"],name="knowledge_snapshot_dedupe")]
    def save(self,*args,**kwargs):
        if self.pk: raise ValidationError("Los snapshots externos son inmutables.")
        super().save(*args,**kwargs)


class ExternalRecord(models.Model):
    class Status(models.TextChoices): ACTIVE="activo","Activo"; MISSING="no_observado","No observado"; WITHDRAWN="retirado","Retirado"
    source=models.ForeignKey(EnvironmentalSource,on_delete=models.PROTECT,related_name="records"); external_id=models.CharField(max_length=300); kind=models.CharField(max_length=100); canonical_key=models.CharField(max_length=300,blank=True); title=models.CharField(max_length=500,blank=True); source_url=models.URLField(blank=True); current_snapshot=models.ForeignKey(ExternalSnapshot,on_delete=models.PROTECT,related_name="current_for"); published_at=models.DateTimeField(null=True,blank=True); effective_from=models.DateTimeField(null=True,blank=True); effective_to=models.DateTimeField(null=True,blank=True); upstream_updated_at=models.DateTimeField(null=True,blank=True); estado=models.CharField(max_length=30,choices=Status.choices,default=Status.ACTIVE); metadata=models.JSONField(default=dict,blank=True); first_seen_at=models.DateTimeField(); last_seen_at=models.DateTimeField()
    class Meta: constraints=[models.UniqueConstraint(fields=["source","external_id"],name="knowledge_record_identity")]


class ExternalFileArtifact(models.Model):
    class Status(models.TextChoices):
        IMPORTED="importado","Importado"
    source=models.ForeignKey(EnvironmentalSource,on_delete=models.PROTECT,related_name="file_artifacts")
    parent_record=models.ForeignKey(ExternalRecord,on_delete=models.PROTECT,related_name="file_artifacts")
    external_resource_id=models.CharField(max_length=300)
    name=models.CharField(max_length=500)
    source_url=models.URLField()
    format=models.CharField(max_length=30)
    content_type=models.CharField(max_length=160,blank=True)
    expected_size=models.PositiveBigIntegerField(null=True,blank=True)
    byte_size=models.PositiveBigIntegerField()
    upstream_created_at=models.DateTimeField(null=True,blank=True)
    upstream_modified_at=models.DateTimeField(null=True,blank=True)
    retrieved_at=models.DateTimeField()
    content_sha256=models.CharField(max_length=64)
    estado=models.CharField(max_length=30,choices=Status.choices,default=Status.IMPORTED)
    metadata=models.JSONField(default=dict,blank=True)
    is_current=models.BooleanField(default=False)
    version=models.PositiveIntegerField()
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=["source","external_resource_id","content_sha256"],name="knowledge_file_artifact_version"),
            models.UniqueConstraint(fields=["source","external_resource_id"],condition=models.Q(is_current=True),name="knowledge_current_file_artifact"),
        ]


class RetcHazardousWasteFact(models.Model):
    artifact=models.ForeignKey(ExternalFileArtifact,on_delete=models.PROTECT,related_name="retc_hazardous_waste_facts")
    external_resource_id=models.CharField(max_length=300)
    year=models.PositiveSmallIntegerField(db_index=True)
    source_row_number=models.PositiveIntegerField()
    row_hash=models.CharField(max_length=64)
    id_vu=models.BigIntegerField()
    id_rol_establecimiento=models.BigIntegerField()
    rol_establecimiento=models.CharField(max_length=300)
    rut_razon_social=models.CharField(max_length=30)
    razon_social=models.CharField(max_length=500,blank=True)
    ciiu6_id=models.CharField(max_length=30,blank=True)
    ciiu6=models.CharField(max_length=500,blank=True)
    ciiu4_id=models.CharField(max_length=30,blank=True)
    ciiu4=models.CharField(max_length=500,blank=True)
    rubro=models.CharField(max_length=300,blank=True)
    rubro_id=models.BigIntegerField()
    codigo_unico_territorial=models.BigIntegerField()
    comuna=models.CharField(max_length=200,db_index=True)
    provincia=models.CharField(max_length=200)
    region=models.CharField(max_length=200,db_index=True)
    latitud_raw=models.CharField(max_length=100)
    longitud_raw=models.CharField(max_length=100)
    cantidad_kilos=models.DecimalField(max_digits=24,decimal_places=6,null=True,blank=True)
    cantidad_toneladas=models.DecimalField(max_digits=24,decimal_places=9)
    id_contaminantes=models.TextField(blank=True)
    contaminantes=models.TextField(blank=True)
    id_peligrosidad=models.TextField(blank=True)
    peligrosidad=models.TextField(blank=True)
    id_lista_a=models.TextField(blank=True)
    lista_a=models.TextField(blank=True)
    id_estado_materia=models.BigIntegerField()
    estado_materia=models.CharField(max_length=100)
    raw_row=models.JSONField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=["artifact","source_row_number"],name="knowledge_retc_fact_source_row")]
        indexes=[models.Index(fields=["artifact","year","region","comuna"],name="knowledge_retc_fact_filter")]
