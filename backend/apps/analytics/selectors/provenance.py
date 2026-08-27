from ..models import EvidenciaObra


def evidence_for_organization(organization, evidence_id):
    return EvidenciaObra.objects.filter(
        organizacion=organization, id=evidence_id
    ).first()


def next_evidence_version(evidence):
    latest = (
        evidence.versiones.order_by("-version")
        .values_list("version", flat=True)
        .first()
    )
    return (latest or 0) + 1
