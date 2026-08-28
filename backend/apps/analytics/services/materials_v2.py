from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import EventoMaterial, LoteMaterial, MaterialOperacional
from .capture import capture_observation
from ..selectors.materials import registered_material_events

INCOMING = {EventoMaterial.Tipo.RECEPCION}
OUTGOING = {
    EventoMaterial.Tipo.USO,
    EventoMaterial.Tipo.CONSUMO,
    EventoMaterial.Tipo.DEVOLUCION,
    EventoMaterial.Tipo.REUTILIZACION,
    EventoMaterial.Tipo.RESIDUO,
}
INDICATOR_TYPES = {
    EventoMaterial.Tipo.ADQUISICION: "cantidad_adquirida",
    EventoMaterial.Tipo.RECEPCION: "cantidad_recibida",
    EventoMaterial.Tipo.USO: "cantidad_utilizada",
    EventoMaterial.Tipo.CONSUMO: "cantidad_utilizada",
    EventoMaterial.Tipo.REUTILIZACION: "cantidad_reutilizada",
    EventoMaterial.Tipo.DEVOLUCION: "cantidad_devuelta",
    EventoMaterial.Tipo.SOBRANTE: "cantidad_sobrante",
    EventoMaterial.Tipo.RESIDUO: "cantidad_residuo",
}


_events = registered_material_events


def _event_value(event):
    observation = event.observacion_cantidad
    if not observation or observation.valor_numerico is None or not observation.unidad:
        return None
    return observation.valor_numerico, observation.unidad


def material_balance(
    organization, material, *, lot=None, start=None, end=None, work=None
):
    totals = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    opening = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    seen = defaultdict(set)
    opening_seen = defaultdict(set)
    signals = []
    if start:
        for event in _events(organization, material, lot=lot, before=start, work=work):
            value = _event_value(event)
            if value is None:
                continue
            amount, unit = value
            opening_seen[unit].add(event.tipo)
            if event.tipo in INCOMING:
                opening[unit]["ingresos"] += amount
            elif event.tipo in OUTGOING:
                opening[unit]["egresos"] += amount
    for event in _events(
        organization, material, lot=lot, start=start, end=end, work=work
    ):
        value = _event_value(event)
        if value is None:
            signals.append({"tipo": "cantidad_sin_observacion", "evento_id": event.id})
            continue
        amount, unit = value
        seen[unit].add(event.tipo)
        indicator = INDICATOR_TYPES.get(event.tipo)
        if indicator:
            totals[unit][indicator] += amount
        if event.tipo in INCOMING:
            totals[unit]["ingresos_balance"] += amount
        elif event.tipo in OUTGOING:
            totals[unit]["egresos_balance"] += amount
        if event.tipo in {EventoMaterial.Tipo.DESPACHO, EventoMaterial.Tipo.TRASLADO}:
            if not event.origen:
                signals.append({"tipo": "movimiento_sin_origen", "evento_id": event.id})
            if not event.destino:
                signals.append(
                    {"tipo": "movimiento_sin_destino", "evento_id": event.id}
                )
        if event.tipo == EventoMaterial.Tipo.RECEPCION and not event.evidencia_id:
            signals.append(
                {"tipo": "material_recibido_sin_evidencia", "evento_id": event.id}
            )
        if (
            event.tipo in {EventoMaterial.Tipo.USO, EventoMaterial.Tipo.CONSUMO}
            and not event.lote_id
            and not event.evento_origen_id
        ):
            signals.append(
                {
                    "tipo": "material_usado_sin_trazabilidad_recepcion",
                    "evento_id": event.id,
                }
            )

    balances = []
    for unit in sorted(set(totals) | set(opening)):
        values = totals[unit]
        received = values["cantidad_recibida"]
        outgoing = values["egresos_balance"]
        opening_stock = opening[unit]["ingresos"] - opening[unit]["egresos"]
        stock = opening_stock + values["ingresos_balance"] - outgoing
        known_reception = (
            EventoMaterial.Tipo.RECEPCION in opening_seen[unit]
            or EventoMaterial.Tipo.RECEPCION in seen[unit]
        )
        status = "completo" if known_reception else "incompleto"
        if stock < 0 and known_reception:
            status = "inconsistente"
            signals.append({"tipo": "stock_negativo", "unidad": unit, "valor": stock})
        use = values["cantidad_utilizada"]
        remainder = values["cantidad_sobrante"]
        reused = values["cantidad_reutilizada"]
        balances.append(
            {
                "unidad": unit,
                "saldo_inicial": opening_stock,
                "ingresos_periodo": values["ingresos_balance"],
                "egresos_periodo": outgoing,
                "cantidad_adquirida": values["cantidad_adquirida"],
                "cantidad_recibida": received,
                "cantidad_utilizada": use,
                "cantidad_reutilizada": reused,
                "cantidad_devuelta": values["cantidad_devuelta"],
                "cantidad_sobrante": remainder,
                "cantidad_residuo": values["cantidad_residuo"],
                "stock_restante": stock,
                "porcentaje_uso": use / received * Decimal("100") if received else None,
                "porcentaje_sobrante": (
                    remainder / received * Decimal("100") if received else None
                ),
                "porcentaje_reutilizado": (
                    reused / received * Decimal("100") if received else None
                ),
                "calidad_balance": status,
            }
        )
    if not balances:
        balances.append(
            {
                "unidad": None,
                "saldo_inicial": None,
                "ingresos_periodo": Decimal("0"),
                "egresos_periodo": Decimal("0"),
                "calidad_balance": "incompleto",
                "stock_restante": None,
            }
        )
    return {
        "material_id": material.id,
        "lote_id": lot.id if lot else None,
        "obra_id": work.id if work else None,
        "balances": balances,
        "senales": signals,
    }


def material_lineage(organization, material, *, lot=None):
    events = []
    for event in _events(organization, material, lot=lot):
        value = _event_value(event)
        events.append(
            {
                "id": event.id,
                "tipo": event.tipo,
                "fecha_hora": event.fecha_hora,
                "evento_origen_id": event.evento_origen_id,
                "actividad_id": event.actividad_id,
                "lote_id": event.lote_id,
                "obra_id": event.obra_id,
                "proceso_id": event.proceso_id,
                "origen": event.origen,
                "destino": event.destino,
                "cantidad": value[0] if value else None,
                "unidad": value[1] if value else None,
                "fuente_id": event.fuente_id,
                "evidencia_id": event.evidencia_id,
                "version_evidencia_id": event.version_evidencia_id,
            }
        )
    return {
        "material_id": material.id,
        "lote_id": lot.id if lot else None,
        "eventos": events,
    }


@transaction.atomic
def save_event_quantity(
    event, *, amount, unit, source, evidence=None, evidence_version=None, actor=None
):
    if source.organizacion_id != event.organizacion_id:
        raise ValidationError("La fuente pertenece a otra organizacion.")
    observation = capture_observation(
        channel="manual",
        organization=event.organizacion,
        activity=event.actividad,
        source=source,
        concept="cantidad_material",
        numeric_value=amount,
        unit=unit,
        timestamp=event.fecha_hora,
        actor=actor,
        evidence=evidence,
        evidence_version=evidence_version,
    )
    event.observacion_cantidad = observation
    event.fuente = source
    event.evidencia = evidence
    event.version_evidencia = evidence_version
    event.save()
    return event


def save_entity(instance, organization, data):
    for field, value in data.items():
        setattr(instance, field, value)
    instance.organizacion = organization
    instance.full_clean()
    instance.save()
    return instance


@transaction.atomic
def save_material_event(instance, organization, data, actor=None):
    amount, unit = data.pop("cantidad", None), data.pop("unidad", None)
    save_entity(instance, organization, data)
    if amount is not None:
        save_event_quantity(
            instance,
            amount=amount,
            unit=unit,
            source=instance.fuente,
            evidence=instance.evidencia,
            evidence_version=instance.version_evidencia,
            actor=actor,
        )
    return instance
