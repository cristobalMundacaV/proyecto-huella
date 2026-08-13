from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Organizacion, EtapaObra, EvidenciaObra, Obra, RegistroEmision
from .serializers import EtapaObraSerializer


def _to_decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _to_float(value):
    return float(_to_decimal(value))


def _effective_emissions(registro):
    stored = _to_decimal(registro.emisiones_kg_co2e)
    if stored > 0:
        return stored

    calculated = _to_decimal(registro.cantidad) * _to_decimal(registro.factor_emision)
    return calculated if calculated > 0 else Decimal("0")


def _serialize_registro(registro):
    emissions = _effective_emissions(registro)
    return {
        "id": registro.id,
        "fecha": registro.fecha,
        "categoria": registro.categoria,
        "fuente_emision": registro.fuente_emision,
        "cantidad": _to_float(registro.cantidad),
        "unidad": registro.unidad,
        "factor_emision": _to_float(registro.factor_emision),
        "emisiones_kg_co2e": _to_float(emissions),
        "emisiones": _to_float(emissions),
        "obra_codigo": registro.obra.codigo_obra if registro.obra_id else "",
        "obra_nombre": registro.obra.nombre if registro.obra_id else "",
        "etapa_nombre": registro.etapa.nombre if registro.etapa_id else "",
    }


def _serialize_obra(obra, registros):
    emissions = sum((_effective_emissions(registro) for registro in registros), Decimal("0"))
    return {
        "id": obra.id,
        "codigo_obra": obra.codigo_obra,
        "nombre": obra.nombre,
        "fecha": obra.fecha_inicio,
        "fecha_inicio": obra.fecha_inicio,
        "superficie_m2": _to_float(obra.superficie_m2),
        "emisiones_kg_co2e": _to_float(emissions),
        "balance_ambiental_kg": 0,
        "balance_neto_kg_co2e": _to_float(emissions),
        "registros_count": len(registros),
    }


def _build_enriched_stage(etapa, registros, obras, evidencias_count):
    serialized = dict(EtapaObraSerializer(etapa).data)
    total_emissions = sum((_effective_emissions(registro) for registro in registros), Decimal("0"))
    registros_by_obra_id = defaultdict(list)

    for registro in registros:
        if registro.obra_id:
            registros_by_obra_id[registro.obra_id].append(registro)

    obras_resumen = [
        _serialize_obra(obra, registros_by_obra_id.get(obra.id, []))
        for obra in obras
    ]

    serialized.update(
        {
            "emisiones_totales_kg_co2e": _to_float(total_emissions),
            "emisiones_kg_co2e": _to_float(total_emissions),
            "emisiones": _to_float(total_emissions),
            "balance_ambiental_kg": 0,
            "balance_neto_kg_co2e": _to_float(total_emissions),
            "obras_count": len(obras),
            "registros_count": len(registros),
            "evidencias_count": evidencias_count,
            "fichas_ambientales_count": evidencias_count,
            "obras_resumen": obras_resumen,
            "registros_emision_resumen": [_serialize_registro(registro) for registro in registros],
        }
    )

    return serialized


@api_view(["GET", "POST"])
def organizacion_etapas(request, organizacion_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)

    if request.method == "POST":
        serializer = EtapaObraSerializer(data={**request.data, "organizacion": organizacion.id})
        serializer.is_valid(raise_exception=True)
        etapa = serializer.save()
        return Response(EtapaObraSerializer(etapa).data, status=status.HTTP_201_CREATED)

    etapas = list(organizacion.etapas.order_by("nombre"))
    registros = list(
        RegistroEmision.objects.filter(organizacion=organizacion)
        .select_related("obra", "etapa")
        .order_by("-fecha", "-created_at")
    )
    obras = list(
        Obra.objects.filter(organizacion=organizacion)
        .select_related("etapa_principal")
        .order_by("nombre")
    )
    registros_by_etapa_id = defaultdict(list)
    obras_by_etapa_id = defaultdict(list)

    for obra in obras:
        if obra.etapa_principal_id:
            obras_by_etapa_id[obra.etapa_principal_id].append(obra)

    for registro in registros:
        etapa_id = registro.etapa_id or (registro.obra.etapa_principal_id if registro.obra_id else None)
        if etapa_id:
            registros_by_etapa_id[etapa_id].append(registro)

    enriched = []
    for etapa in etapas:
        etapa_obras = obras_by_etapa_id.get(etapa.id, [])
        etapa_registros = registros_by_etapa_id.get(etapa.id, [])
        evidencias_count = EvidenciaObra.objects.filter(
            Q(etapa=etapa) |
            Q(obra__etapa_principal=etapa) |
            Q(registro_emision__etapa=etapa),
            organizacion=organizacion,
        ).distinct().count()
        enriched.append(_build_enriched_stage(etapa, etapa_registros, etapa_obras, evidencias_count))

    return Response(enriched)
