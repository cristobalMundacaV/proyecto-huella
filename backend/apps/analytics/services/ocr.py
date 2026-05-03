import re
from decimal import Decimal, InvalidOperation

from apps.analytics.models import EmisionLote
from .documentos import extraer_texto_archivo

DIESEL_FACTOR = Decimal("2.68")
ELECTRICITY_FACTOR = Decimal("0.4")


def _normalize_number(value):
    if not value:
        return None

    normalized = value.replace(".", "").replace(",", ".")

    try:
        return float(Decimal(normalized))
    except (InvalidOperation, ValueError):
        return None


def extraer_texto_documento(documento):
    return extraer_texto_archivo(documento.archivo)["texto_extraido"]


def _first_match(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)

    if not match:
        return ""

    for group in match.groups():
        if group:
            return group.strip()

    return ""


def proponer_datos_desde_texto(text):
    litros = _first_match(
        r"(?:litros|lts)[ \t]*:?[ \t]*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)[ \t]*(?:litros|lts|l\b)",
        text,
    )
    kwh = _first_match(
        r"(?:kwh)[ \t]*:?[ \t]*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)[ \t]*kwh",
        text,
    )
    volumen = _first_match(
        r"(?:volumen)[ \t]*:?[ \t]*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)[ \t]*m3",
        text,
    )
    monto = _first_match(r"(?:monto|total)\s*:?\s*\$?\s*([\d.,]+)", text)

    return {
        "fecha": _first_match(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text),
        "proveedor": _first_match(r"(?:proveedor|emisor)\s*:?\s*([^\n\r]+)", text),
        "litros_combustible": _normalize_number(litros),
        "kwh": _normalize_number(kwh),
        "patente": _first_match(r"(?:patente)\s*:?\s*([A-Z0-9-]{5,10})", text),
        "origen": _first_match(r"(?:origen)\s*:?\s*([^\n\r]+)", text),
        "destino": _first_match(r"(?:destino)\s*:?\s*([^\n\r]+)", text),
        "volumen": _normalize_number(volumen),
        "monto": _normalize_number(monto),
        "numero_documento": _first_match(
            r"(?:numero|nro|folio|documento)\s*:?\s*([A-Z0-9-]+)",
            text,
        ),
    }


def generar_extraccion_documento(documento):
    texto = extraer_texto_documento(documento)
    return {
        "texto_extraido": texto,
        "datos_sugeridos": proponer_datos_desde_texto(texto),
    }


def aplicar_datos_validados(extraccion, datos_validados):
    lote = extraccion.documento.lote
    created = []
    litros = datos_validados.get("litros_combustible")
    kwh = datos_validados.get("kwh")

    if litros:
        created.append(
            EmisionLote.objects.create(
                lote=lote,
                actividad="diesel",
                cantidad=Decimal(str(litros)),
                unidad="litros",
                factor_emision=DIESEL_FACTOR,
            )
        )

    if kwh:
        created.append(
            EmisionLote.objects.create(
                lote=lote,
                actividad="electricidad",
                cantidad=Decimal(str(kwh)),
                unidad="kWh",
                factor_emision=ELECTRICITY_FACTOR,
            )
        )

    return created
