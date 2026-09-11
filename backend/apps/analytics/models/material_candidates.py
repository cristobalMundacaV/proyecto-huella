"""Material candidates are global, separate from HuellaChile candidates."""

from contextvars import ContextVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

material_write = ContextVar("material_candidate_write", default=False)


class GovernedMaterialQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Use el servicio de candidatos materiales.")

    def delete(self):
        raise ValidationError("El historial material es inmutable.")

    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Use el servicio de candidatos materiales.")


class GovernedMaterialModel(models.Model):
    objects = GovernedMaterialQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not material_write.get():
            raise ValidationError("Use el servicio de candidatos materiales.")
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if (
                not isinstance(self, MaterialEnvironmentalFactorCandidate)
                or previous.status == "promoted_to_draft"
            ):
                raise ValidationError("El historial material es inmutable.")
            for field in (
                "source_profile_id",
                "source_indicator_id",
                "normalization",
                "provenance",
                "functional_context",
                "initial_eligibility",
            ):
                if getattr(previous, field) != getattr(self, field):
                    raise ValidationError("La evidencia del candidato es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial material es inmutable.")


class MaterialEnvironmentalFactorCandidate(GovernedMaterialModel):
    class Status(models.TextChoices):
        DETECTED = "detected", "Detected"
        REVIEW = "requires_review", "Requires review"
        READY = "ready_for_review", "Approved for promotion"
        REJECTED = "rejected", "Rejected"
        PROMOTED = "promoted_to_draft", "Promoted to draft"

    source_profile = models.OneToOneField(
        "knowledge.OekobaudatEnvironmentalProfileFact",
        on_delete=models.PROTECT,
        related_name="material_factor_candidate",
    )
    source_indicator = models.ForeignKey(
        "knowledge.OekobaudatEnvironmentalIndicatorFact",
        null=True,
        on_delete=models.PROTECT,
        related_name="material_factor_candidates",
    )
    status = models.CharField(max_length=30, choices=Status.choices, db_index=True)
    normalization = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)
    functional_context = models.JSONField(default=dict)
    initial_eligibility = models.JSONField(default=dict)
    promoted_factor = models.OneToOneField(
        "analytics.FactorAmbiental",
        null=True,
        on_delete=models.PROTECT,
        related_name="material_source_candidate",
    )
    promoted_version = models.OneToOneField(
        "analytics.VersionFactorAmbiental",
        null=True,
        on_delete=models.PROTECT,
        related_name="material_source_candidate",
    )
    promoted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="material_candidates_promoted",
    )
    promoted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "detected",
                        "requires_review",
                        "ready_for_review",
                        "rejected",
                        "promoted_to_draft",
                    ]
                ),
                name="material_candidate_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="promoted_to_draft",
                        promoted_factor__isnull=False,
                        promoted_version__isnull=False,
                        promoted_by__isnull=False,
                        promoted_at__isnull=False,
                    )
                    | (
                        ~models.Q(status="promoted_to_draft")
                        & models.Q(
                            promoted_factor__isnull=True,
                            promoted_version__isnull=True,
                            promoted_by__isnull=True,
                            promoted_at__isnull=True,
                        )
                    )
                ),
                name="material_candidate_promotion_pair",
            ),
        ]


class MaterialFactorCandidateReview(GovernedMaterialModel):
    candidate = models.ForeignKey(
        MaterialEnvironmentalFactorCandidate,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    decision = models.CharField(
        max_length=10, choices=[("approved", "Approved"), ("rejected", "Rejected")]
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="material_factor_reviews",
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
    context = models.JSONField(default=dict)
    eligibility = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(decision__in=["approved", "rejected"]),
                name="material_review_valid_decision",
            )
        ]


@receiver(pre_save, sender="analytics.FactorAmbiental")
@receiver(pre_save, sender="analytics.VersionFactorAmbiental")
def protect_material_origin(sender, instance, **kwargs):
    if not instance.pk:
        return
    is_factor = sender._meta.model_name == "factorambiental"
    field = "promoted_factor_id" if is_factor else "promoted_version_id"
    if not MaterialEnvironmentalFactorCandidate.objects.filter(
        **{field: instance.pk}
    ).exists():
        return
    previous = sender.objects.get(pk=instance.pk)
    fields = (
        (
            "contexto",
            "organizacion_id",
            "unidad_entrada",
            "unidad_resultado",
            "sustancia_impacto",
            "categoria",
        )
        if is_factor
        else (
            f.attname
            for f in sender._meta.fields
            if f.name not in {"estado", "vigencia_desde", "vigencia_hasta"}
        )
    )
    if any(getattr(instance, field) != getattr(previous, field) for field in fields):
        raise ValidationError(
            "La provenance material y su valor de origen son inmutables."
        )
