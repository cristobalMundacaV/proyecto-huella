from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora, EvidenciaObra, LoteForestal, RegistroEmision, TransporteLoteForestal
from .serializers import LoteForestalDetailSerializer, LoteForestalSerializer, TransporteLoteForestalSerializer
from .services.forestal_carbono import calcular_balance_neto_lote


def get_constructora_or_404(constructora_id):
    return get_object_or_404(Constructora, constructora_id=constructora_id)


def get_lote_or_404(constructora, lote_id):
    return get_object_or_404(
        LoteForestal.objects.select_related("constructora").prefetch_related(
            "transportes",
            "evidencias",
            "registros_emision",
        ),
        constructora=constructora,
        lote_id=lote_id,
    )


@api_view(["GET", "POST"])
def constructora_lotes_forestales(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)

    if request.method == "GET":
        lotes = LoteForestal.objects.filter(constructora=constructora).order_by("-fecha", "lote_id")
        return Response(LoteForestalDetailSerializer(lotes, many=True, context={"request": request}).data)

    serializer = LoteForestalSerializer(data={**request.data, "constructora": constructora.id})
    serializer.is_valid(raise_exception=True)
    lote = serializer.save()
    return Response(LoteForestalDetailSerializer(lote, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def constructora_lote_forestal_detail(request, constructora_id, lote_id):
    constructora = get_constructora_or_404(constructora_id)
    lote = get_lote_or_404(constructora, lote_id)

    if request.method == "GET":
        return Response(LoteForestalDetailSerializer(lote, context={"request": request}).data)

    if request.method == "PATCH":
        serializer = LoteForestalSerializer(lote, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        lote = serializer.save()
        return Response(LoteForestalDetailSerializer(lote, context={"request": request}).data)

    with transaction.atomic():
        RegistroEmision.objects.filter(lote_forestal=lote).update(lote_forestal=None)
        EvidenciaObra.objects.filter(lote_forestal=lote).update(lote_forestal=None)
        lote.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def constructora_lote_forestal_transportes(request, constructora_id, lote_id):
    constructora = get_constructora_or_404(constructora_id)
    lote = get_lote_or_404(constructora, lote_id)

    if request.method == "GET":
        transportes = lote.transportes.order_by("-fecha", "-created_at")
        return Response(TransporteLoteForestalSerializer(transportes, many=True).data)

    serializer = TransporteLoteForestalSerializer(data={**request.data, "lote_forestal": lote.id})
    serializer.is_valid(raise_exception=True)
    transporte = serializer.save()
    return Response(TransporteLoteForestalSerializer(transporte).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def constructora_lotes_forestales_resumen(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    lotes = list(LoteForestal.objects.filter(constructora=constructora).order_by("-fecha", "lote_id"))

    total_emisiones = 0.0
    total_co2 = 0.0
    estados = {
        "favorable": 0,
        "intermedio": 0,
        "critico": 0,
        "incompleto": 0,
    }
    balances = []

    for lote in lotes:
        balance = calcular_balance_neto_lote(lote)
        total_emisiones += balance["emisiones_generadas_kg_co2e"]
        total_co2 += balance["co2_almacenado_kg"]
        estados[balance["estado_balance"]] = estados.get(balance["estado_balance"], 0) + 1
        balances.append(
            {
                "lote_id": lote.lote_id,
                "especie": lote.especie,
                "volumen_m3": float(lote.volumen_m3 or 0),
                **balance,
            }
        )

    top_criticos = sorted(
        [item for item in balances if item["estado_balance"] in {"critico", "intermedio", "incompleto"}],
        key=lambda item: item["balance_neto_kg_co2e"],
        reverse=True,
    )[:5]
    top_favorables = sorted(
        [item for item in balances if item["estado_balance"] == "favorable"],
        key=lambda item: item["balance_neto_kg_co2e"],
    )[:5]
    volumen_total = LoteForestal.objects.filter(constructora=constructora).aggregate(total=Sum("volumen_m3"))["total"] or 0

    return Response(
        {
            "total_lotes": len(lotes),
            "volumen_total_m3": round(float(volumen_total), 3),
            "emisiones_generadas_kg_co2e": round(total_emisiones, 3),
            "co2_almacenado_kg": round(total_co2, 3),
            "balance_neto_kg_co2e": round(total_emisiones - total_co2, 3),
            "lotes_balance_favorable": estados["favorable"],
            "lotes_balance_intermedio": estados["intermedio"],
            "lotes_balance_critico": estados["critico"],
            "lotes_balance_incompleto": estados["incompleto"],
            "top_lotes_criticos": top_criticos,
            "top_lotes_favorables": top_favorables,
        }
    )
