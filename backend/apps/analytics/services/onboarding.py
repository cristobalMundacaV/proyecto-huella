import json
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from ..models import AreaCapacidadAmbiental, AreaOperacional, CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial, ElementoDiagnosticoAmbiental

FLOW_CATALOG = {
    "materiales": ("Materiales e insumos", "Recepcion, utilizacion y trazabilidad."), "transporte": ("Transporte y logistica", "Viajes, cargas y rutas."),
    "combustibles": ("Combustibles", "Consumo movil y estacionario."), "maquinaria": ("Maquinaria y equipos", "Uso, horas y mantenimiento."),
    "energia": ("Energia", "Consumo energetico."), "agua": ("Agua", "Consumo, abastecimiento y medicion."), "residuos": ("Residuos", "Generacion, valorizacion y disposicion."),
    "ruido": ("Ruido", "Mediciones y seguimiento."), "hidrica_suelo": ("Gestion hidrica y suelo", "Drenajes, descargas e intervencion."),
    "generacion_propia": ("Generacion propia", "Energia producida."), "procesos_productivos": ("Procesos productivos", "Procesos especificos del rubro."), "otros": ("Otros", "Otros aspectos configurables."),
}
AREA_FLOW_SUGGESTIONS = {"bodega": ["materiales", "residuos"], "maquinaria_operaciones": ["maquinaria", "combustibles"], "logistica_transporte": ["transporte", "combustibles"], "administracion_compras": ["materiales", "energia", "agua", "combustibles"], "calidad_laboratorio": ["ruido", "agua", "hidrica_suelo"]}

def ensure_flow_catalog():
    return {key: CapacidadAmbiental.objects.update_or_create(clave=key, defaults={"nombre": value[0], "descripcion": value[1], "activa": True, "orden": index})[0] for index, (key, value) in enumerate(FLOW_CATALOG.items(), 1)}

def valid_chilean_rut(value):
    normalized = "".join(character for character in str(value or "").upper() if character.isdigit() or character == "K")
    if len(normalized) != 9 or not normalized[:-1].isdigit(): return False
    total = 0; multiplier = 2
    for character in reversed(normalized[:-1]):
        total += int(character) * multiplier; multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - total % 11; expected = "0" if result == 11 else "K" if result == 10 else str(result)
    return normalized[-1] == expected

def regenerate_diagnostic(organization, user, answers):
    diagnostic, _ = DiagnosticoAmbientalInicial.objects.update_or_create(organizacion=organization, obra=None, defaults={"estado": DiagnosticoAmbientalInicial.Estado.COMPLETADO, "fecha_inicio": timezone.localdate(), "fecha_finalizacion": timezone.localdate(), "responsable": user, "objetivo_principal": "Preparacion inicial de informacion", "descripcion_contexto": json.dumps(answers, ensure_ascii=False)})
    diagnostic.elementos.all().delete()
    for relation in organization.capacidades_ambientales.exclude(estado=CapacidadOrganizacion.Estado.NO_APLICA).select_related("capacidad"):
        ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostic, tipo=ElementoDiagnosticoAmbiental.Tipo.PROCESO, nombre=relation.capacidad.nombre, descripcion="Flujo declarado por la organización durante su configuración inicial.")
        kind = ElementoDiagnosticoAmbiental.Tipo.INFORMACION_DISPONIBLE if relation.disponibilidad_inicial == "regular" else ElementoDiagnosticoAmbiental.Tipo.BRECHA
        ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostic, tipo=kind, nombre=relation.capacidad.nombre, descripcion=f"Disponibilidad declarada: {relation.get_disponibilidad_inicial_display() or 'por confirmar'}.")
    for area in organization.areas_operacionales.filter(activa=True): ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostic, tipo=ElementoDiagnosticoAmbiental.Tipo.FUENTE, nombre=area.nombre, descripcion="Área declarada como posible origen de información.")
    return diagnostic

@transaction.atomic
def apply_onboarding_step(organization, user, step, payload):
    stored = dict(organization.onboarding_data or {})
    stored[str(step)] = payload
    if step == 1:
        for field in ("nombre", "nombre_comercial", "rut", "rubro", "pais", "region", "comuna", "direccion", "email", "telefono", "contacto", "preset"):
            if field in payload: setattr(organization, field, payload[field])
        if not organization.nombre or not organization.rut or not organization.pais or not organization.preset:
            raise ValueError("Completa razón social, RUT, país y sector.")
        if not valid_chilean_rut(organization.rut): raise ValueError("El RUT ingresado no es válido.")
        if organization.email:
            try: validate_email(organization.email)
            except ValidationError as exc: raise ValueError("El formato del correo electrónico no es válido.") from exc
        if organization.telefono:
            digits = re.sub(r"\D", "", organization.telefono); local = digits[2:] if digits.startswith("56") else digits
            if not re.fullmatch(r"9\d{8}", local): raise ValueError("El formato del teléfono no es válido.")
            organization.telefono = f"+56{local}"
    elif step == 2:
        selected = payload.get("areas", [])
        existing = {item.tipo: item for item in organization.areas_operacionales.all()}
        for row in selected:
            kind = row.get("tipo") if isinstance(row, dict) else row
            name = row.get("nombre") if isinstance(row, dict) else dict(AreaOperacional.Tipo.choices).get(kind, kind.replace("_", " ").title())
            AreaOperacional.objects.update_or_create(organizacion=organization, nombre=name, defaults={"tipo": kind, "activa": True})
        organization.areas_operacionales.exclude(tipo__in=[row.get("tipo") if isinstance(row, dict) else row for row in selected]).update(activa=False)
    elif step == 3:
        catalog = ensure_flow_catalog(); selected = payload.get("flujos", {})
        relations = {}
        for key, availability in selected.items():
            if key not in catalog: continue
            state = CapacidadOrganizacion.Estado.APLICA if availability in {"regular", "parcial"} else CapacidadOrganizacion.Estado.SIN_DATOS if availability == "sin_informacion" else CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO
            relations[key] = CapacidadOrganizacion.objects.update_or_create(organizacion=organization, capacidad=catalog[key], defaults={"estado": state, "disponibilidad_inicial": availability})[0]
        organization.capacidades_ambientales.exclude(capacidad__clave__in=relations).update(estado=CapacidadOrganizacion.Estado.NO_APLICA)
        AreaCapacidadAmbiental.objects.filter(area__organizacion=organization).delete()
        custom = payload.get("relaciones", {})
        active_area_types = set(organization.areas_operacionales.filter(activa=True).values_list("tipo", flat=True))
        if set(custom) - active_area_types: raise ValueError("Una de las áreas no pertenece a la estructura activa de la organización.")
        if any(set(keys) - set(relations) for keys in custom.values()): raise ValueError("Uno de los flujos no pertenece a la organización.")
        for area in organization.areas_operacionales.filter(activa=True):
            for key in custom.get(area.tipo, AREA_FLOW_SUGGESTIONS.get(area.tipo, [])):
                if key in relations: AreaCapacidadAmbiental.objects.get_or_create(area=area, capacidad_organizacion=relations[key])
        if DiagnosticoAmbientalInicial.objects.filter(organizacion=organization, obra=None).exists(): regenerate_diagnostic(organization, user, stored.get("4", {}))
    elif step == 4:
        regenerate_diagnostic(organization, user, payload)
    elif step == 5:
        organization.onboarding_completado = True
    organization.onboarding_data = stored
    organization.onboarding_step = 5 if organization.onboarding_completado else max(organization.onboarding_step, min(5, step + 1))
    organization.full_clean(); organization.save()
    return organization
