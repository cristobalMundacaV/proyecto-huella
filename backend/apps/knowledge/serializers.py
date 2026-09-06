from rest_framework import serializers
from .models import BcnLegalArticleFact,BcnLegalNormFact,BcnLegalNormRelationFact,BcnLegalNormVersionFact,BcnLegalObligationCandidate,LegalEvidenceRequirementVersion,LegalObligationApplicabilityCriterion,LegalObligationVersion,EnvironmentalSource,ExternalRecord,ExternalSnapshot,HuellaChileEmissionFactorFact,RetcHazardousWasteFact,SourceState,SyncRun
class SourceStateSerializer(serializers.ModelSerializer):
    class Meta:model=SourceState;exclude=["source"]
class EnvironmentalSourceSerializer(serializers.ModelSerializer):
    sync_state=SourceStateSerializer(read_only=True)
    class Meta:model=EnvironmentalSource;fields="__all__"
class SyncRunSerializer(serializers.ModelSerializer):
    class Meta:model=SyncRun;fields="__all__"
class ExternalSnapshotSerializer(serializers.ModelSerializer):
    class Meta:model=ExternalSnapshot;fields="__all__"
class ExternalRecordSerializer(serializers.ModelSerializer):
    class Meta:model=ExternalRecord;fields="__all__"
class RetcHazardousWasteFactSerializer(serializers.ModelSerializer):
    class Meta:model=RetcHazardousWasteFact;exclude=["raw_row"]
class HuellaChileEmissionFactorFactSerializer(serializers.ModelSerializer):
    class Meta:model=HuellaChileEmissionFactorFact;fields="__all__"
class BcnLegalNormVersionFactSerializer(serializers.ModelSerializer):
    class Meta:model=BcnLegalNormVersionFact;exclude=["norm_fact"]
class BcnLegalNormRelationFactSerializer(serializers.ModelSerializer):
    class Meta:model=BcnLegalNormRelationFact;exclude=["norm_fact"]
class BcnLegalNormFactSerializer(serializers.ModelSerializer):
    versions=BcnLegalNormVersionFactSerializer(many=True,read_only=True);relations=BcnLegalNormRelationFactSerializer(many=True,read_only=True)
    class Meta:model=BcnLegalNormFact;fields="__all__"
class BcnLegalArticleFactSerializer(serializers.ModelSerializer):
    class Meta:model=BcnLegalArticleFact;exclude=["raw_fragment","parse"]
class BcnLegalObligationCandidateSerializer(serializers.ModelSerializer):
    norm_id=serializers.IntegerField(source="extraction_run.article.parse.source_document.artifact.parent_record.current_snapshot.bcn_legal_norm_fact.id",read_only=True)
    norm_number=serializers.CharField(source="extraction_run.article.parse.source_document.artifact.metadata.norm_number",read_only=True)
    norm_title=serializers.CharField(source="extraction_run.article.parse.source_document.artifact.parent_record.current_snapshot.bcn_legal_norm_fact.title",read_only=True)
    version_uri=serializers.CharField(source="extraction_run.article.parse.source_document.artifact.metadata.version_uri",read_only=True)
    artifact_sha256=serializers.CharField(source="extraction_run.article.parse.source_document.artifact.content_sha256",read_only=True)
    parser_version=serializers.CharField(source="extraction_run.article.parse.parser_version",read_only=True)
    article_id=serializers.IntegerField(source="extraction_run.article.id",read_only=True)
    article_key=serializers.CharField(source="extraction_run.article.article_key",read_only=True)
    article_number=serializers.CharField(source="extraction_run.article.article_number",read_only=True)
    article_label=serializers.CharField(source="extraction_run.article.article_label",read_only=True)
    article_text_hash=serializers.CharField(source="extraction_run.article.text_hash",read_only=True)
    extractor_version=serializers.CharField(source="extraction_run.extractor_version",read_only=True)
    review_status=serializers.SerializerMethodField();reviewed_at=serializers.SerializerMethodField();review_decision=serializers.SerializerMethodField();promoted_obligation_id=serializers.SerializerMethodField();promoted_version_id=serializers.SerializerMethodField()
    def _review(self,obj):
        try:return obj.review
        except Exception:return None
    def get_review_status(self,obj):return "reviewed" if self._review(obj) else "unreviewed"
    def get_reviewed_at(self,obj):return self._review(obj).reviewed_at if self._review(obj) else None
    def get_review_decision(self,obj):return self._review(obj).decision if self._review(obj) else None
    def get_promoted_obligation_id(self,obj):return self._review(obj).promoted_obligation_id if self._review(obj) else None
    def get_promoted_version_id(self,obj):return self._review(obj).promoted_version_id if self._review(obj) else None
    class Meta:
        model=BcnLegalObligationCandidate
        exclude=["extraction_run"]
class LegalObligationCriterionSerializer(serializers.ModelSerializer):
    class Meta:model=LegalObligationApplicabilityCriterion;exclude=["obligation_version"]
class LegalObligationVersionSerializer(serializers.ModelSerializer):
    criteria=LegalObligationCriterionSerializer(many=True,read_only=True);code=serializers.CharField(source="obligation.code",read_only=True);source=serializers.SerializerMethodField()
    def get_source(self,obj):
        p=obj.source_provenance
        return {"norm_number":p.get("norm_number"),"article_number":p.get("article_number"),"version_uri":p.get("version_uri"),"artifact_sha256":p.get("artifact_sha256"),"candidate_key":p.get("candidate_key"),"source_quote":p.get("source_quote")}
    class Meta:model=LegalObligationVersion;exclude=["source_provenance"]


class LegalEvidenceRequirementVersionSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="requirement.code", read_only=True)
    obligation_id = serializers.IntegerField(source="requirement.obligation_id", read_only=True)
    freshness = serializers.SerializerMethodField()
    legal_basis = serializers.SerializerMethodField()

    def get_freshness(self, obj):
        from .legal_evidence import get_legal_evidence_requirement_freshness
        return get_legal_evidence_requirement_freshness(obj)

    def get_legal_basis(self, obj):
        basis = obj.legal_basis_snapshot
        provenance = basis.get("source_provenance") or {}
        return {
            "obligation_code": basis.get("obligation_code"),
            "version": basis.get("obligation_version"),
            "norm_number": provenance.get("norm_number"),
            "article_number": provenance.get("article_number"),
            "source_quote": provenance.get("source_quote"),
        }

    class Meta:
        model = LegalEvidenceRequirementVersion
        exclude = ["legal_basis_snapshot"]
