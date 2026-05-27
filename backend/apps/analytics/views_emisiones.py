from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Constructora, RegistroEmision
from .serializers import RegistroEmisionSerializer


def _to_decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _to_float(value):
    return float(_to_decimal(value))


def _normalize_text(value):
    return str(value or "").strip().lower()


def _chart_axis_label(value):
    # Recharts can split long SVG tick labels by spaces. NBSP keeps source names in one line.
    return str(value or "").replace(" ", "\u00A0")


def _effective_emissions(registro):
    """Return stored emissions or calculate a safe fallback from quantity * factor."""
    stored = _to_decimal(registro.emisiones_kg_co2e)
    if stored > 0:
        return stored

    quantity = _to_decimal(registro.cantidad)
    factor = _to_decimal(registro.factor_emision)
    calculated = quantity * factor

    return calculated if calculated > 0 else Decimal("0")


def _build_serialized_rows(registros):
    serialized = RegistroEmisionSerializer(registros, many=True).data
    rows = []

    for registro, row in zip(registros, serialized):
        emissions = _effective_emissions(registro)
        obra_codigo = registro.obra.codigo_obra if registro.obra_id else ""
        obra_nombre = registro.obra.nombre if registro.obra_id else ""
        etapa_nombre = registro.etapa.nombre if registro.etapa_id else "Sin etapa"

        row = dict(row)
        row["emisiones"] = _to_float(emissions)
        row["emisiones_kg_co2e"] = _to_float(emissions)
        row["codigo_obra"] = obra_codigo
        row["obra_codigo"] = obra_codigo
        row["obra_nombre"] = obra_nombre
        row["etapa_nombre"] = etapa_nombre
        rows.append(row)

    return rows


def _sorted_items(grouped, label_key):
    items = []

    for label, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True):
        display_label = _chart_axis_label(label) if label_key == "fuente_emision" else label
        items.append({label_key: display_label, "emisiones": round(value, 3)})

    return items


@api_view(["GET"])
def constructora_emisiones(request, constructora_id):
    constructora = get_object_or_404(Constructora, constructora_id=constructora_id)
    queryset = (
        RegistroEmision.objects.filter(constructora=constructora)
        .select_related("constructora", "obra", "etapa")
        .order_by("-fecha", "-created_at")
    )
    registros = list(queryset)
    rows = _build_serialized_rows(registros)

    por_categoria = defaultdict(float)
    por_unidad = defaultdict(float)
    por_fuente = defaultdict(float)
    por_obra = defaultdict(float)
    diesel_total = 0.0
    total = 0.0
    registros_sin_factor = 0
    obras_con_registro = set()

    for registro, row in zip(registros, rows):
        emissions = float(row.get("emisiones") or 0)
        total += emissions

        categoria = row.get("categoria") or "Otros"
        unidad = row.get("etapa_nombre") or "Sin etapa"
        fuente = row.get("fuente_emision") or "Sin fuente"
        obra_nombre = row.get("obra_nombre") or row.get("codigo_obra") or "Sin obra"

        por_categoria[categoria] += emissions
        por_unidad[unidad] += emissions
        por_fuente[fuente] += emissions
        por_obra[obra_nombre] += emissions

        if row.get("codigo_obra"):
            obras_con_registro.add(row.get("codigo_obra"))

        normalized_source = _normalize_text(fuente)
        normalized_category = _normalize_text(categoria)
        if "diesel" in normalized_source or "diesel" in normalized_category or "diésel" in normalized_source:
            diesel_total += emissions

        if _to_decimal(registro.factor_emision) <= 0:
            registros_sin_factor += 1

    categoria_critica = max(por_categoria, key=por_categoria.get, default="Sin datos")
    unidad_critica = max(por_unidad, key=por_unidad.get, default="Sin datos")
    fuente_critica = max(por_fuente, key=por_fuente.get, default="Sin datos")
    obra_critica = max(por_obra, key=por_obra.get, default="Sin datos")
    fuente_critica_total = por_fuente.get(fuente_critica, 0.0)

    emisiones_por_unidad = _sorted_items(por_unidad, "unidad")
    emisiones_por_fuente = _sorted_items(por_fuente, "fuente_emision")
    emisiones_por_categoria = _sorted_items(por_categoria, "categoria")

    page_size = int(request.query_params.get("page_size") or 0)
    page = max(1, int(request.query_params.get("page") or 1))
    response_rows = rows
    if page_size > 0:
        start = (page - 1) * page_size
        end = start + page_size
        response_rows = rows[start:end]

    kpis = {
        "emisiones_totales": round(total, 3),
        "fuente_critica": fuente_critica,
        "unidad_critica": unidad_critica,
        "etapa_critica": unidad_critica,
        "categoria_critica": categoria_critica,
        "obra_critica": obra_critica,
        "porcentaje_diesel": round((diesel_total / total) * 100, 2) if total else 0,
        "porcentaje_top_fuente_emision": round((fuente_critica_total / total) * 100, 2) if total else 0,
        "promedio_emision_por_obra": round(total / len(obras_con_registro), 3) if obras_con_registro else 0,
        "registros_emision_sin_factor": registros_sin_factor,
        "registros_count": len(rows),
    }

    return Response(
        {
            "constructora_id": constructora.constructora_id,
            "constructora_nombre": constructora.nombre,
            "kpis": kpis,
            "rows": response_rows,
            "datos": rows,
            "total_emisiones": round(total, 3),
            "emisiones_totales": round(total, 3),
            "fuente_critica": fuente_critica,
            "unidad_critica": unidad_critica,
            "etapa_critica": unidad_critica,
            "categoria_critica": categoria_critica,
            "obra_critica": obra_critica,
            "emisiones_por_unidad": emisiones_por_unidad,
            "emisiones_por_fuente_emision": emisiones_por_fuente,
            "emisiones_por_categoria": emisiones_por_categoria,
        }
    )
