from django.core.exceptions import ValidationError
from django.db import models


class ImmutableAssessmentQuerySet(models.QuerySet):
    def bulk_create(self, *args, **kwargs):
        raise ValidationError(
            "Las evaluaciones juridicas deben crearse mediante el service gobernado."
        )

    def delete(self):
        raise ValidationError("Las evaluaciones juridicas son inmutables.")


class LegalObligationApplicabilityAssessment(models.Model):
    class Scope(models.TextChoices):ORGANIZATION="organization","Organization";WORK="work","Work"
    class Result(models.TextChoices):APPLICABLE="applicable","Applicable";NOT_APPLICABLE="not_applicable","Not applicable";UNDETERMINED="undetermined","Undetermined"
    objects=ImmutableAssessmentQuerySet.as_manager()
    organization=models.ForeignKey("analytics.Organizacion",on_delete=models.PROTECT,related_name="legal_applicability_assessments")
    work=models.ForeignKey("analytics.Obra",on_delete=models.PROTECT,null=True,blank=True,related_name="legal_applicability_assessments")
    obligation=models.ForeignKey("knowledge.LegalObligation",on_delete=models.PROTECT,related_name="applicability_assessments")
    obligation_version=models.ForeignKey("knowledge.LegalObligationVersion",on_delete=models.PROTECT,related_name="applicability_assessments")
    scope_level=models.CharField(max_length=20,choices=Scope.choices)
    evaluator_version=models.CharField(max_length=60,db_index=True);revision=models.PositiveIntegerField();is_latest=models.BooleanField(default=True,db_index=True)
    result=models.CharField(max_length=30,choices=Result.choices,db_index=True)
    context_snapshot=models.JSONField()
    criteria_snapshot=models.JSONField(blank=True)
    legal_snapshot=models.JSONField()
    evaluation_details=models.JSONField()
    context_hash=models.CharField(max_length=64);input_hash=models.CharField(max_length=64)
    evaluated_by=models.ForeignKey("auth.User",on_delete=models.PROTECT,related_name="legal_applicability_assessments");evaluated_at=models.DateTimeField()
    class Meta:
        constraints=[
            models.CheckConstraint(
                condition=(
                    models.Q(scope_level="organization", work__isnull=True)
                    | models.Q(scope_level="work", work__isnull=False)
                ),
                name="analytics_legal_scope_work",
            ),
            models.UniqueConstraint(fields=["organization","obligation","revision"],condition=models.Q(work__isnull=True),name="analytics_legal_org_revision"),
            models.UniqueConstraint(fields=["work","obligation","revision"],condition=models.Q(work__isnull=False),name="analytics_legal_work_revision"),
            models.UniqueConstraint(fields=["organization","obligation"],condition=models.Q(work__isnull=True,is_latest=True),name="analytics_legal_org_latest"),
            models.UniqueConstraint(fields=["work","obligation"],condition=models.Q(work__isnull=False,is_latest=True),name="analytics_legal_work_latest"),
        ]
        ordering=["-evaluated_at"]
    def clean(self):
        from apps.knowledge.models import LegalObligationVersion

        if self.obligation_version.state != LegalObligationVersion.State.ACTIVE:
            raise ValidationError(
                "Solo una version juridica ACTIVE puede originar una evaluacion."
            )
        if self.obligation_version.obligation_id != self.obligation_id:
            raise ValidationError("La version no pertenece a la obligacion.")
        if self.scope_level == self.Scope.ORGANIZATION and (
            self.work_id or self.obligation_version.applicability_level != "organization"
        ):
            raise ValidationError("Scope organizacional inconsistente.")
        if self.scope_level == self.Scope.WORK and (
            not self.work_id or self.obligation_version.applicability_level != "work"
        ):
            raise ValidationError("Scope de obra inconsistente.")
        if self.work_id and self.work.organizacion_id != self.organization_id:
            raise ValidationError("La obra pertenece a otra organizacion.")
    def save(self,*args,**kwargs):
        if self.pk:
            raise ValidationError(
                "La evaluacion juridica es inmutable; use supersession interna."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La evaluacion juridica es inmutable.")
