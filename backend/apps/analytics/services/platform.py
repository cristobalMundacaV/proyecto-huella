from django.db import transaction

from ..models import EtapaObra, EvidenciaObra, Obra, RegistroEmision, TransporteObra


@transaction.atomic
def delete_organization_with_related_data(organization):
    works = Obra.objects.filter(organizacion=organization)
    stages = EtapaObra.objects.filter(organizacion=organization)
    emission_records = RegistroEmision.objects.filter(organizacion=organization)
    evidence = EvidenciaObra.objects.filter(organizacion=organization)
    transport_records = TransporteObra.objects.filter(obra__in=works)

    deleted_summary = {
        "transportes": transport_records.count(),
        "evidencias": evidence.count(),
        "registros_emision": emission_records.count(),
        "obras": works.count(),
        "etapas": stages.count(),
    }
    transport_records.delete()
    evidence.delete()
    emission_records.delete()
    works.delete()
    stages.delete()
    organization.delete()
    return deleted_summary
