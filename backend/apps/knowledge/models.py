import hashlib

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


class HuellaChileEmissionFactorFact(models.Model):
    artifact=models.ForeignKey(ExternalFileArtifact,on_delete=models.PROTECT,related_name="huellachile_emission_factor_facts")
    sheet_name=models.CharField(max_length=200)
    source_row_number=models.PositiveIntegerField()
    row_hash=models.CharField(max_length=64)
    raw_row=models.JSONField()
    publisher=models.CharField(max_length=200,default="Programa HuellaChile / Ministerio del Medio Ambiente")
    dataset_year=models.PositiveSmallIntegerField(db_index=True)
    alcance=models.CharField(max_length=200,db_index=True)
    categoria=models.CharField(max_length=300,db_index=True)
    subcategoria=models.CharField(max_length=500)
    actividad=models.CharField(max_length=500,db_index=True)
    auxiliar=models.CharField(max_length=500,blank=True)
    unidad_actividad=models.CharField(max_length=200,db_index=True)
    factor_value=models.DecimalField(max_digits=30,decimal_places=15,null=True,blank=True)
    published_value_raw=models.CharField(max_length=200)
    unidad_factor=models.CharField(max_length=300)
    technical_source_1=models.TextField(blank=True)
    technical_source_2=models.TextField(blank=True)
    technical_source_3=models.TextField(blank=True)
    formula_original=models.TextField(blank=True)
    cached_value_available=models.BooleanField(default=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["artifact","sheet_name","source_row_number"],name="knowledge_hc_factor_source_row")]
        indexes=[models.Index(fields=["artifact","dataset_year","alcance","categoria"],name="knowledge_hc_factor_filter")]

class BcnLegalNormSubscription(models.Model):
    source=models.ForeignKey(EnvironmentalSource,on_delete=models.PROTECT,related_name="legal_norm_subscriptions");norm_type=models.CharField(max_length=30);number=models.CharField(max_length=60);label=models.CharField(max_length=300);scope_tags=models.JSONField(default=list,blank=True);active=models.BooleanField(default=True);created_at=models.DateTimeField(auto_now_add=True);updated_at=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["source","norm_type","number"],name="knowledge_bcn_subscription_identity")]
class BcnLegalNormFact(models.Model):
    snapshot=models.OneToOneField(ExternalSnapshot,on_delete=models.PROTECT,related_name="bcn_legal_norm_fact");norm_uri=models.URLField(max_length=500);identifier=models.CharField(max_length=200,blank=True);number=models.CharField(max_length=60,db_index=True);title=models.CharField(max_length=1000);norm_type_uri=models.URLField(max_length=500);norm_type_name=models.CharField(max_length=200,db_index=True);issuer_uri=models.URLField(max_length=500,blank=True);issuer_name=models.CharField(max_length=500,blank=True,db_index=True);publish_date=models.DateField(null=True,blank=True);promulgation_date=models.DateField(null=True,blank=True);latest_version_uri=models.URLField(max_length=500);latest_version_date=models.DateField(null=True,blank=True);scope_tags=models.JSONField(default=list,blank=True)
class BcnLegalNormVersionFact(models.Model):
    norm_fact=models.ForeignKey(BcnLegalNormFact,on_delete=models.PROTECT,related_name="versions");version_uri=models.URLField(max_length=500);version_date=models.DateField(null=True,blank=True);is_latest=models.BooleanField(default=False);xml_document_url=models.URLField(max_length=500,blank=True);html_document_url=models.URLField(max_length=500,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["norm_fact","version_uri"],name="knowledge_bcn_version_identity"),models.UniqueConstraint(fields=["norm_fact"],condition=models.Q(is_latest=True),name="knowledge_bcn_one_latest_version")]
class BcnLegalNormRelationFact(models.Model):
    norm_fact=models.ForeignKey(BcnLegalNormFact,on_delete=models.PROTECT,related_name="relations");relation_type=models.CharField(max_length=40);target_uri=models.URLField(max_length=500);target_number=models.CharField(max_length=60,blank=True);target_title=models.CharField(max_length=1000,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["norm_fact","relation_type","target_uri"],name="knowledge_bcn_relation_identity")]
class BcnLegalTextSourceDocument(models.Model):
    artifact=models.OneToOneField(ExternalFileArtifact,on_delete=models.PROTECT,related_name="bcn_legal_source_document");raw_bytes=models.BinaryField();detected_encoding=models.CharField(max_length=60);byte_size=models.PositiveBigIntegerField();created_at=models.DateTimeField(auto_now_add=True)
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El documento fuente legal es inmutable.")
        super().save(*args,**kwargs)
class BcnLegalTextParse(models.Model):
    class Status(models.TextChoices):SUCCESS="success","Success";ERROR="error","Error"
    source_document=models.ForeignKey(BcnLegalTextSourceDocument,on_delete=models.PROTECT,related_name="parses");parser_version=models.CharField(max_length=30);status=models.CharField(max_length=20,choices=Status.choices);parsed_at=models.DateTimeField();article_count=models.PositiveIntegerField(default=0);error_message=models.TextField(blank=True);metadata=models.JSONField(default=dict,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["source_document","parser_version"],name="knowledge_bcn_text_parse_version")]
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El parse legal es inmutable.")
        super().save(*args,**kwargs)
class BcnLegalArticleFact(models.Model):
    parse=models.ForeignKey(BcnLegalTextParse,on_delete=models.PROTECT,related_name="articles");article_key=models.CharField(max_length=300);article_number=models.CharField(max_length=100,blank=True,db_index=True);article_label=models.CharField(max_length=300,blank=True,db_index=True);heading=models.TextField(blank=True);order_index=models.PositiveIntegerField();source_path=models.CharField(max_length=1000);text_plain=models.TextField();text_hash=models.CharField(max_length=64);raw_fragment=models.TextField();metadata=models.JSONField(default=dict,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["parse","article_key"],name="knowledge_bcn_article_identity")];ordering=["order_index"]


class BcnLegalObligationExtractionRun(models.Model):
    class Status(models.TextChoices):
        SUCCESS="success","Success";ERROR="error","Error"
    article=models.ForeignKey(BcnLegalArticleFact,on_delete=models.PROTECT,related_name="obligation_extraction_runs")
    extractor_version=models.CharField(max_length=60,db_index=True)
    extractor_method=models.CharField(max_length=60)
    status=models.CharField(max_length=20,choices=Status.choices)
    executed_at=models.DateTimeField()
    source_text_hash=models.CharField(max_length=64)
    candidate_count=models.PositiveIntegerField(default=0)
    error_message=models.TextField(blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["article","extractor_version"],name="knowledge_bcn_obligation_run_version")]
        indexes=[models.Index(fields=["extractor_version","status"],name="knowledge_bcn_obl_run_lookup")]
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El run de extraccion juridica es inmutable.")
        super().save(*args,**kwargs)


class BcnLegalObligationCandidate(models.Model):
    class Modality(models.TextChoices):
        OBLIGATION="obligation","Obligation";PROHIBITION="prohibition","Prohibition"
    extraction_run=models.ForeignKey(BcnLegalObligationExtractionRun,on_delete=models.PROTECT,related_name="candidates")
    candidate_key=models.CharField(max_length=64,db_index=True)
    order_index=models.PositiveIntegerField()
    modality_hint=models.CharField(max_length=20,choices=Modality.choices,db_index=True)
    trigger_text=models.TextField();trigger_start=models.PositiveIntegerField();trigger_end=models.PositiveIntegerField()
    source_quote=models.TextField();source_start=models.PositiveIntegerField();source_end=models.PositiveIntegerField()
    source_quote_hash=models.CharField(max_length=64)
    subject_hint=models.TextField(blank=True);subject_start=models.PositiveIntegerField(null=True,blank=True);subject_end=models.PositiveIntegerField(null=True,blank=True)
    action_hint=models.TextField(blank=True);action_start=models.PositiveIntegerField(null=True,blank=True);action_end=models.PositiveIntegerField(null=True,blank=True)
    condition_hint=models.TextField(blank=True);condition_start=models.PositiveIntegerField(null=True,blank=True);condition_end=models.PositiveIntegerField(null=True,blank=True)
    temporal_hint=models.TextField(blank=True);temporal_start=models.PositiveIntegerField(null=True,blank=True);temporal_end=models.PositiveIntegerField(null=True,blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["extraction_run","candidate_key"],name="knowledge_bcn_obligation_candidate_key")]
        indexes=[models.Index(fields=["modality_hint","candidate_key"],name="knowledge_bcn_obl_cand_idx")]
        ordering=["order_index"]
    def clean(self):
        text=self.extraction_run.article.text_plain
        spans=(("trigger_text","trigger_start","trigger_end"),("source_quote","source_start","source_end"),("subject_hint","subject_start","subject_end"),("action_hint","action_start","action_end"),("condition_hint","condition_start","condition_end"),("temporal_hint","temporal_start","temporal_end"))
        for value_field,start_field,end_field in spans:
            value=getattr(self,value_field);start=getattr(self,start_field);end=getattr(self,end_field)
            if not value:
                if start is not None or end is not None:raise ValidationError(f"{value_field}: offsets sin texto.")
                continue
            if start is None or end is None or start>=end or text[start:end]!=value:raise ValidationError(f"{value_field}: provenance textual invalida.")
        if hashlib.sha256(self.source_quote.encode()).hexdigest()!=self.source_quote_hash:raise ValidationError("source_quote_hash invalido.")
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El candidato juridico es inmutable.")
        self.full_clean()
        super().save(*args,**kwargs)
