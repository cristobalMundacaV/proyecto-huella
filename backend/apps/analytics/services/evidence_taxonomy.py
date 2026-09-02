from rest_framework.exceptions import ValidationError

from ..models import EvidenciaObra


T = EvidenciaObra.TipoEvidencia

EVIDENCE_TYPES_BY_DOMAIN = {
    "agua": (
        (T.FACTURA_AGUA, "Factura / boleta sanitaria"),
        (T.LECTURA_MEDIDOR_AGUA, "Lectura / registro de medidor de agua"),
        (T.ABASTECIMIENTO_ALJIBE, "Registro de abastecimiento por camión aljibe"),
        (T.EXTRACCION_AGUA_PROPIA, "Registro de extracción propia"),
        (T.INFORME_HIDRICO, "Informe / certificado hídrico"),
    ),
    "energia": (
        (T.BOLETA_ELECTRICA, "Factura / boleta eléctrica"),
        (T.LECTURA_MEDIDOR_ELECTRICO, "Lectura / registro de medidor eléctrico"),
    ),
    "generacion_propia": (
        (T.LECTURA_MEDIDOR_ELECTRICO, "Lectura / registro de medidor eléctrico"),
        (T.REPORTE_GENERACION, "Reporte de generación"),
        (T.REPORTE_INVERSOR, "Reporte de inversor / sistema energético"),
    ),
    "combustibles": (
        (T.FACTURA_COMBUSTIBLE, "Factura de combustible"),
        (T.VALE_COMBUSTIBLE, "Vale / comprobante de combustible"),
        (T.REGISTRO_ABASTECIMIENTO, "Registro de abastecimiento"),
        (T.REGISTRO_ESTANQUE, "Registro de estanque / telemetría"),
    ),
    "transporte": (
        (T.DOCUMENTO_TRANSPORTE, "Guía / documento de transporte"),
        (T.HOJA_RUTA, "Hoja / ficha de ruta"),
        (T.REGISTRO_GPS, "Registro GPS / kilometraje"),
        (T.COMPROBANTE_DESPACHO, "Comprobante de despacho"),
    ),
    "maquinaria": (
        (T.HOROMETRO, "Horómetro"),
        (T.PARTE_DIARIO_MAQUINARIA, "Parte diario de maquinaria"),
        (T.REGISTRO_ABASTECIMIENTO, "Registro de abastecimiento"),
        (T.REGISTRO_MANTENIMIENTO, "Registro de mantenimiento"),
    ),
    "materiales": (
        (T.FACTURA_MATERIAL, "Factura de material"),
        (T.ORDEN_COMPRA, "Orden de compra"),
        (T.GUIA_DESPACHO, "Guía de despacho"),
        (T.FICHA_TECNICA, "Ficha técnica"),
        (T.EPD, "EPD / declaración ambiental"),
        (T.CERTIFICADO_PROVEEDOR, "Certificado de proveedor"),
    ),
    "residuos": (
        (T.TICKET_PESAJE, "Ticket de pesaje"),
        (T.MANIFIESTO_RETIRO, "Manifiesto / guía de retiro"),
        (T.CERTIFICADO_DISPOSICION, "Certificado de disposición final"),
        (T.REGISTRO_RESIDUOS, "Registro de retiro"),
        (T.INFORME_GESTOR, "Informe del gestor"),
    ),
    "ruido": (
        (T.INFORME_RUIDO, "Informe de medición de ruido"),
        (T.REGISTRO_SONOMETRO, "Registro de sonómetro"),
        (T.CALIBRACION_SONOMETRO, "Certificado / informe de calibración"),
    ),
    "emisiones-atmosfericas": (
        (T.INFORME_MUESTREO, "Informe de muestreo"),
        (T.INFORME_LABORATORIO, "Informe de laboratorio"),
        (T.MEDICION_INSTRUMENTAL, "Registro de medición instrumental"),
        (T.INFORME_MONITOR, "Informe de monitor / sensor"),
    ),
}

FLOW_DOMAIN = {
    "combustible": "combustibles",
    "combustible_estacionario": "combustibles",
    "combustible_movil": "combustibles",
    "emisiones_atmosfericas": "emisiones-atmosfericas",
}


def evidence_domain(value):
    value = str(value or "").strip()
    return FLOW_DOMAIN.get(value, value)


def evidence_types_for_domain(value):
    domain = evidence_domain(value)
    rows = EVIDENCE_TYPES_BY_DOMAIN.get(domain)
    if rows is None:
        raise ValidationError({"dominio": "El dominio ambiental no es válido."})
    return [
        {"value": str(item), "label": label}
        for item, label in (*rows, (T.OTRO, "Otro documento"))
    ]


def validate_evidence_type(value, domain):
    normalized_value = str(value or T.OTRO)
    allowed = {item["value"] for item in evidence_types_for_domain(domain)}
    if normalized_value not in allowed:
        label = evidence_domain(domain).replace("-", " ").replace("_", " ").title()
        raise ValidationError(
            {"evidencia_tipo": f"Este tipo de respaldo no corresponde al flujo {label}."}
        )
    return normalized_value
