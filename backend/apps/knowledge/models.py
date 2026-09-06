import hashlib
import uuid

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
class ImmutableLegalProvenanceQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("La provenance juridica es inmutable y no puede eliminarse.")


class BcnLegalArticleFact(models.Model):
    objects=ImmutableLegalProvenanceQuerySet.as_manager()
    parse=models.ForeignKey(BcnLegalTextParse,on_delete=models.PROTECT,related_name="articles");article_key=models.CharField(max_length=300);article_number=models.CharField(max_length=100,blank=True,db_index=True);article_label=models.CharField(max_length=300,blank=True,db_index=True);heading=models.TextField(blank=True);order_index=models.PositiveIntegerField();source_path=models.CharField(max_length=1000);text_plain=models.TextField();text_hash=models.CharField(max_length=64);raw_fragment=models.TextField();metadata=models.JSONField(default=dict,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["parse","article_key"],name="knowledge_bcn_article_identity")];ordering=["order_index"]
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El articulo juridico es inmutable.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError("El articulo juridico es inmutable y no puede eliminarse.")


class BcnLegalObligationExtractionRun(models.Model):
    objects=ImmutableLegalProvenanceQuerySet.as_manager()
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
    def clean(self):
        if self.source_text_hash!=self.article.text_hash:raise ValidationError("source_text_hash no corresponde al articulo.")
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("El run de extraccion juridica es inmutable.")
        self.full_clean()
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError("El run juridico es inmutable y no puede eliminarse.")


class BcnLegalObligationCandidate(models.Model):
    objects=ImmutableLegalProvenanceQuerySet.as_manager()
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
    def delete(self,*args,**kwargs):raise ValidationError("El candidato juridico es inmutable y no puede eliminarse.")


def legal_obligation_code():return f"OBL-{uuid.uuid4()}"


class LegalObligation(models.Model):
    code=models.CharField(max_length=50,unique=True,default=legal_obligation_code,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def delete(self,*args,**kwargs):raise ValidationError("Una obligacion con historia no puede eliminarse.")


class LegalObligationVersion(models.Model):
    class State(models.TextChoices):DRAFT="draft","Draft";VALIDATED="validated","Validated";ACTIVE="active","Active";OBSOLETE="obsolete","Obsolete"
    class Modality(models.TextChoices):OBLIGATION="obligation","Obligation";PROHIBITION="prohibition","Prohibition"
    class ApplicabilityLevel(models.TextChoices):ORGANIZATION="organization","Organization";WORK="work","Work"
    class ApplicabilityMode(models.TextChoices):PENDING="pending","Pending";UNCONDITIONAL="unconditional","Unconditional";CONDITIONAL="conditional","Conditional"
    obligation=models.ForeignKey(LegalObligation,on_delete=models.PROTECT,related_name="versions")
    version=models.PositiveIntegerField()
    state=models.CharField(max_length=20,choices=State.choices,default=State.DRAFT,db_index=True)
    source_candidate=models.OneToOneField(BcnLegalObligationCandidate,on_delete=models.PROTECT,related_name="promoted_version")
    modality=models.CharField(max_length=20,choices=Modality.choices)
    canonical_statement=models.TextField(blank=True)
    subject_text=models.TextField(blank=True);action_text=models.TextField(blank=True);object_text=models.TextField(blank=True);condition_text=models.TextField(blank=True);temporal_text=models.TextField(blank=True)
    applicability_level=models.CharField(max_length=20,choices=ApplicabilityLevel.choices)
    applicability_mode=models.CharField(max_length=20,choices=ApplicabilityMode.choices,default=ApplicabilityMode.PENDING)
    source_provenance=models.JSONField()
    validated_by=models.ForeignKey("auth.User",on_delete=models.PROTECT,null=True,blank=True,related_name="validated_legal_obligation_versions");validated_at=models.DateTimeField(null=True,blank=True)
    activated_by=models.ForeignKey("auth.User",on_delete=models.PROTECT,null=True,blank=True,related_name="activated_legal_obligation_versions");activated_at=models.DateTimeField(null=True,blank=True);obsoleted_at=models.DateTimeField(null=True,blank=True)
    created_by=models.ForeignKey("auth.User",on_delete=models.PROTECT,related_name="created_legal_obligation_versions");created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["obligation","version"],name="knowledge_legal_obligation_version"),models.UniqueConstraint(fields=["obligation"],condition=models.Q(state="active"),name="knowledge_one_active_legal_obligation")]
    def save(self,*args,**kwargs):
        if self.pk:
            previous=LegalObligationVersion.objects.get(pk=self.pk)
            fixed=("obligation_id","version","source_candidate_id","source_provenance","created_by_id","created_at")
            if any(getattr(previous,key)!=getattr(self,key) for key in fixed):raise ValidationError("Identidad y provenance de la version son inmutables.")
            semantic=("modality","canonical_statement","subject_text","action_text","object_text","condition_text","temporal_text","applicability_level","applicability_mode")
            if previous.state!=self.State.DRAFT and any(getattr(previous,key)!=getattr(self,key) for key in semantic):raise ValidationError("Una version gobernada ya no es editable.")
            lifecycle=("state","validated_by_id","validated_at","activated_by_id","activated_at","obsoleted_at")
            if any(getattr(previous,key)!=getattr(self,key) for key in lifecycle):raise ValidationError("Use el lifecycle service explicito.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError("Una version juridica no puede eliminarse.")


class LegalCriterionQuerySet(models.QuerySet):
    def delete(self):
        if self.exclude(obligation_version__state="draft").exists():raise ValidationError("Los criterios gobernados son inmutables.")
        return super().delete()


class LegalObligationApplicabilityCriterion(models.Model):
    objects=LegalCriterionQuerySet.as_manager()
    class Operator(models.TextChoices):EQUALS="equals","Equals";IN="in","In"
    obligation_version=models.ForeignKey(LegalObligationVersion,on_delete=models.PROTECT,related_name="criteria")
    order_index=models.PositiveIntegerField();dimension=models.CharField(max_length=60);operator=models.CharField(max_length=20,choices=Operator.choices);values=models.JSONField();note=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["obligation_version","order_index"],name="knowledge_legal_criterion_order")];ordering=["order_index"]
    def clean(self):
        from .legal_contracts import validate_criterion
        cleaned=validate_criterion({"dimension":self.dimension,"operator":self.operator,"values":self.values,"note":self.note},self.obligation_version.applicability_level)
        self.dimension=cleaned["dimension"];self.operator=cleaned["operator"];self.values=cleaned["values"];self.note=cleaned["note"]
    def save(self,*args,**kwargs):
        if self.pk and LegalObligationApplicabilityCriterion.objects.get(pk=self.pk).obligation_version.state!="draft":raise ValidationError("Los criterios gobernados son inmutables.")
        if self.obligation_version.state!="draft":raise ValidationError("Los criterios solo pueden modificarse en draft.")
        self.full_clean();super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):
        if self.obligation_version.state!="draft":raise ValidationError("Los criterios gobernados son inmutables.")
        return super().delete(*args,**kwargs)


def legal_evidence_requirement_code():
    return f"ERQ-{uuid.uuid4()}"


class ImmutableLegalEvidenceQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("El requisito de evidencia gobernado no puede eliminarse.")


class LegalEvidenceRequirement(models.Model):
    objects = ImmutableLegalEvidenceQuerySet.as_manager()
    code = models.CharField(
        max_length=50,
        unique=True,
        default=legal_evidence_requirement_code,
        editable=False,
    )
    obligation = models.ForeignKey(
        LegalObligation,
        on_delete=models.PROTECT,
        related_name="evidence_requirements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            previous = LegalEvidenceRequirement.objects.get(pk=self.pk)
            if previous.code != self.code or previous.obligation_id != self.obligation_id:
                raise ValidationError("La identidad del requisito es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El requisito de evidencia gobernado no puede eliminarse.")


class LegalEvidenceRequirementVersion(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        VALIDATED = "validated", "Validated"
        ACTIVE = "active", "Active"
        OBSOLETE = "obsolete", "Obsolete"

    class EvidenceMode(models.TextChoices):
        ANY_OF = "any_of", "Any of"
        ALL_OF = "all_of", "All of"

    class EvidenceClass(models.TextChoices):
        DOCUMENT = "document", "Document"
        TRANSACTION_RECORD = "transaction_record", "Transaction record"
        OPERATIONAL_RECORD = "operational_record", "Operational record"
        MEASUREMENT = "measurement", "Measurement"
        CERTIFICATE = "certificate", "Certificate"
        REPORT = "report", "Report"
        MANIFEST = "manifest", "Manifest"
        PERMIT_OR_RESOLUTION = "permit_or_resolution", "Permit or resolution"
        TECHNICAL_SPECIFICATION = "technical_specification", "Technical specification"
        OTHER = "other", "Other"

    class TemporalScope(models.TextChoices):
        UNSPECIFIED = "unspecified", "Unspecified"
        ONE_TIME = "one_time", "One time"
        EVENT_BASED = "event_based", "Event based"
        PERIODIC = "periodic", "Periodic"
        CURRENT = "current", "Current"

    objects = ImmutableLegalEvidenceQuerySet.as_manager()
    requirement = models.ForeignKey(
        LegalEvidenceRequirement,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.PositiveIntegerField()
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT, db_index=True)
    legal_obligation_version = models.ForeignKey(
        LegalObligationVersion,
        on_delete=models.PROTECT,
        related_name="evidence_requirement_versions",
    )
    title = models.CharField(max_length=240)
    requirement_statement = models.TextField()
    proof_objective = models.TextField()
    evidence_mode = models.CharField(max_length=20, choices=EvidenceMode.choices)
    evidence_classes = models.JSONField()
    accepted_evidence_descriptions = models.JSONField()
    temporal_scope = models.CharField(max_length=20, choices=TemporalScope.choices)
    notes = models.TextField(blank=True)
    legal_basis_snapshot = models.JSONField()
    created_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="created_legal_evidence_requirement_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, null=True, blank=True, related_name="validated_legal_evidence_requirement_versions")
    validated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, null=True, blank=True, related_name="activated_legal_evidence_requirement_versions")
    activated_at = models.DateTimeField(null=True, blank=True)
    obsoleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requirement", "version"], name="knowledge_legal_evidence_req_version"),
            models.UniqueConstraint(fields=["requirement"], condition=models.Q(state="active"), name="knowledge_one_active_legal_evidence_req"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = LegalEvidenceRequirementVersion.objects.get(pk=self.pk)
            fixed = ("requirement_id", "version", "legal_obligation_version_id", "legal_basis_snapshot", "created_by_id", "created_at")
            if any(getattr(previous, field) != getattr(self, field) for field in fixed):
                raise ValidationError("La identidad y base juridica son inmutables.")
            semantic = ("title", "requirement_statement", "proof_objective", "evidence_mode", "evidence_classes", "accepted_evidence_descriptions", "temporal_scope", "notes")
            if previous.state != self.State.DRAFT and any(getattr(previous, field) != getattr(self, field) for field in semantic):
                raise ValidationError("Una version gobernada ya no es editable.")
            lifecycle = ("state", "validated_by_id", "validated_at", "activated_by_id", "activated_at", "obsoleted_at")
            if any(getattr(previous, field) != getattr(self, field) for field in lifecycle):
                raise ValidationError("Use el lifecycle service explicito.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Una version de requisito de evidencia no puede eliminarse.")


class BcnLegalObligationCandidateReview(models.Model):
    objects=ImmutableLegalProvenanceQuerySet.as_manager()
    class Decision(models.TextChoices):APPROVED="approved","Approved";REJECTED="rejected","Rejected"
    candidate=models.OneToOneField(BcnLegalObligationCandidate,on_delete=models.PROTECT,related_name="review")
    decision=models.CharField(max_length=20,choices=Decision.choices);reviewer=models.ForeignKey("auth.User",on_delete=models.PROTECT,related_name="legal_candidate_reviews");reviewed_at=models.DateTimeField();note=models.TextField(blank=True)
    promoted_obligation=models.ForeignKey(LegalObligation,on_delete=models.PROTECT,null=True,blank=True,related_name="candidate_reviews");promoted_version=models.ForeignKey(LegalObligationVersion,on_delete=models.PROTECT,null=True,blank=True,related_name="candidate_reviews")
    def clean(self):
        promoted=bool(self.promoted_obligation_id and self.promoted_version_id)
        if self.decision==self.Decision.APPROVED and not promoted:raise ValidationError("Una aprobacion requiere obligacion y version promovidas.")
        if self.decision==self.Decision.APPROVED and promoted and (self.promoted_version.obligation_id!=self.promoted_obligation_id or self.promoted_version.source_candidate_id!=self.candidate_id):raise ValidationError("La promocion aprobada no corresponde al candidato u obligacion.")
        if self.decision==self.Decision.REJECTED and (self.promoted_obligation_id or self.promoted_version_id):raise ValidationError("Un rechazo no puede tener promocion.")
    def save(self,*args,**kwargs):
        if self.pk:raise ValidationError("La revision juridica es inmutable.")
        self.full_clean();super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):raise ValidationError("La revision juridica no puede eliminarse.")
