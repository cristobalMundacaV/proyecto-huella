from django.core.exceptions import ValidationError

from apps.analytics.models import Obra, Organizacion

DIMENSIONS={
    "organization_country":("organization","country",None),"organization_preset":("organization","preset",set(Organizacion.Preset.values)),"organization_rubro":("organization","rubro",None),"organization_region":("organization","region",None),"organization_comuna":("organization","comuna",None),
    "work_type":("work","type",set(Obra.TipoProyecto.values)),"work_environmental_profile":("work","environmental_profile",set(Obra.PerfilAmbiental.values)),"work_region":("work","region",None),"work_comuna":("work","comuna",None),"work_state":("work","state",set(Obra.Estado.values)),
}

def validate_semantic_fields(modality,applicability_level,applicability_mode):
    from .models import LegalObligationVersion
    if modality not in LegalObligationVersion.Modality.values:raise ValidationError("Modalidad juridica invalida.")
    if applicability_level not in LegalObligationVersion.ApplicabilityLevel.values:raise ValidationError("Nivel de aplicabilidad invalido.")
    if applicability_mode not in LegalObligationVersion.ApplicabilityMode.values:raise ValidationError("Modo de aplicabilidad invalido.")

def validate_criterion(data,applicability_level=None):
    from .models import LegalObligationApplicabilityCriterion
    dimension=data.get("dimension");operator=data.get("operator");values=data.get("values")
    if dimension not in DIMENSIONS:raise ValidationError("Dimension de aplicabilidad invalida.")
    if applicability_level=="organization" and DIMENSIONS[dimension][0]=="work":raise ValidationError("Una obligacion organizacional no admite criterios de obra.")
    if operator not in LegalObligationApplicabilityCriterion.Operator.values:raise ValidationError("Operador invalido.")
    if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v.strip() for v in values):raise ValidationError("values debe contener strings no vacios.")
    values=[v.strip() for v in values]
    if operator=="equals" and len(values)!=1:raise ValidationError("equals requiere exactamente un valor.")
    choices=DIMENSIONS[dimension][2]
    if choices and any(v not in choices for v in values):raise ValidationError("Valor controlado invalido.")
    return {"dimension":dimension,"operator":operator,"values":values,"note":str(data.get("note","")).strip()}
