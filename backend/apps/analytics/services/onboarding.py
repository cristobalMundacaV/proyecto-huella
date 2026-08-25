import json
import re
from hashlib import sha1

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from ..models import AreaCapacidadAmbiental, AreaOperacional, CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial, ElementoDiagnosticoAmbiental
from .chile_locations import validate_chile_location

FLOW_CATALOG = {
    "materiales": ("Materiales e insumos", "Uso y trazabilidad de materiales e insumos."),
    "transporte": ("Transporte", "Traslados, viajes y movimiento de cargas."),
    "combustibles": ("Combustibles", "Consumo de combustibles de fuentes móviles y estacionarias."),
    "energia": ("Energía", "Consumo energético de la operación."),
    "agua": ("Agua", "Consumo, abastecimiento y medición de agua."),
    "residuos_no_peligrosos": ("Residuos no peligrosos", "Generación, valorización y disposición de residuos no peligrosos."),
    "residuos_peligrosos": ("Residuos peligrosos", "Generación, almacenamiento, transporte y disposición de residuos peligrosos."),
    "ruido": ("Ruido", "Mediciones y seguimiento de emisiones de ruido."),
    "emisiones_atmosfericas": ("Emisiones atmosféricas", "Emisiones de fuentes móviles, estacionarias y material particulado."),
    "suelo": ("Suelo", "Intervenciones, afectaciones y seguimiento del suelo."),
    "sustancias_peligrosas": ("Sustancias peligrosas", "Manejo y trazabilidad de sustancias peligrosas."),
    "biodiversidad_vegetacion": ("Biodiversidad / vegetación", "Interacción con biodiversidad, flora y vegetación."),
    "efluentes_descargas": ("Efluentes / descargas", "Generación, control y seguimiento de efluentes y descargas."),
    "generacion_energia": ("Generación de energía", "Energía generada dentro de la operación."),
    "otros": ("Otros", "Otras dimensiones ambientales configurables."),
}
AREA_FLOW_SUGGESTIONS = {"bodega": ["materiales", "residuos_no_peligrosos", "residuos_peligrosos", "sustancias_peligrosas"], "maquinaria_equipos": ["combustibles", "emisiones_atmosfericas", "ruido"], "logistica_transporte": ["transporte", "combustibles", "emisiones_atmosfericas"], "administracion": ["energia", "agua"], "compras_adquisiciones": ["materiales"], "calidad_laboratorio": ["ruido", "agua", "efluentes_descargas", "suelo"]}

AREA_CATALOGS = {
    "construccion": [
        ("oficina_tecnica", "Oficina técnica", True),
        ("bodega", "Bodega", True),
        ("administracion", "Administración", True),
        ("compras_adquisiciones", "Compras / Adquisiciones", True),
        ("medio_ambiente_sostenibilidad", "Medio ambiente / Sostenibilidad", True),
        ("prevencion_riesgos_hse", "Prevención de riesgos / HSE", True),
        ("logistica_transporte", "Logística / Transporte", False),
        ("maquinaria_equipos", "Maquinaria / Equipos", False),
        ("calidad_laboratorio", "Calidad / Laboratorio", False),
        ("terreno_supervision", "Terreno / Supervisión", False),
        ("mantenimiento", "Mantenimiento", False),
    ],
}

DEFAULT_AREA_CATALOG = [
    ("administracion", "Administración", True),
    ("medio_ambiente_sostenibilidad", "Medio ambiente / Sostenibilidad", True),
    ("logistica_transporte", "Logística / Transporte", False),
    ("maquinaria_equipos", "Maquinaria / Equipos", False),
    ("calidad_laboratorio", "Calidad / Laboratorio", False),
    ("mantenimiento", "Mantenimiento", False),
]


def area_catalog_for(sector):
    return [
        {"tipo": key, "nombre": name, "recomendada": recommended}
        for key, name, recommended in AREA_CATALOGS.get(sector, DEFAULT_AREA_CATALOG)
    ]


def _custom_area_type(name):
    digest = sha1(name.casefold().encode("utf-8")).hexdigest()[:12]
    return f"personalizada_{digest}"

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
    source_labels = {"sistema_interno": "Sistema interno / ERP", "planillas": "Excel / planillas", "documentos": "Documentos", "terreno": "Registros de terreno", "medidores": "Medidores", "sensores": "Sensores", "proveedor": "Proveedor / tercero", "manual": "Registro manual", "otro": "Otro"}
    flow_answers = answers.get("flujos", {})
    for relation in organization.capacidades_ambientales.exclude(estado=CapacidadOrganizacion.Estado.NO_APLICA).select_related("capacidad"):
        response = flow_answers.get(relation.capacidad.clave, {})
        availability = response.get("disponibilidad", "no_seguro")
        kind = ElementoDiagnosticoAmbiental.Tipo.INFORMACION_DISPONIBLE if availability == "suficiente" else ElementoDiagnosticoAmbiental.Tipo.BRECHA
        ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostic, tipo=kind, nombre=relation.capacidad.nombre, descripcion=json.dumps(response, ensure_ascii=False))
        for source in response.get("fuentes", []):
            ElementoDiagnosticoAmbiental.objects.create(diagnostico=diagnostic, tipo=ElementoDiagnosticoAmbiental.Tipo.FUENTE, nombre=f"{relation.capacidad.nombre} — {source_labels.get(source, source)}", descripcion="Fuente declarada durante el diagnóstico inicial de capacidad de información.")
    return diagnostic

@transaction.atomic
def apply_onboarding_step(organization, user, step, payload):
    stored = dict(organization.onboarding_data or {})
    stored[str(step)] = payload
    if step == 1:
        for field in ("nombre", "nombre_comercial", "rut", "rubro", "region", "comuna", "direccion", "email", "telefono", "contacto", "preset"):
            if field in payload: setattr(organization, field, payload[field])
        organization.pais = "Chile"
        if not organization.nombre or not organization.rut or not organization.preset:
            raise ValueError("Completa razón social, RUT y sector.")
        if not valid_chilean_rut(organization.rut): raise ValueError("El RUT ingresado no es válido.")
        location_error = validate_chile_location(organization.region, organization.comuna)
        if location_error: raise ValueError(location_error)
        if organization.email:
            try: validate_email(organization.email)
            except ValidationError as exc: raise ValueError("El formato del correo electrónico no es válido.") from exc
        if organization.telefono:
            digits = re.sub(r"\D", "", organization.telefono); local = digits[2:] if digits.startswith("56") else digits
            if not re.fullmatch(r"9\d{8}", local): raise ValueError("El formato del teléfono no es válido.")
            organization.telefono = f"+56{local}"
    elif step == 2:
        selected = payload.get("areas", [])
        if not isinstance(selected, list) or not selected:
            raise ValueError("Selecciona al menos un área para continuar.")
        allowed = {row[0]: row[1] for row in AREA_CATALOGS.get(organization.preset, DEFAULT_AREA_CATALOG)}
        normalized = []
        seen_names = set()
        for row in selected:
            kind = str(row.get("tipo", "") if isinstance(row, dict) else row).strip()
            supplied_name = str(row.get("nombre", "") if isinstance(row, dict) else "").strip()
            if kind in allowed:
                name = allowed[kind]
            elif supplied_name:
                name = supplied_name
                existing_by_type = organization.areas_operacionales.filter(tipo=kind).first()
                kind = existing_by_type.tipo if existing_by_type else _custom_area_type(name)
            else:
                raise ValueError("Una de las áreas seleccionadas no es válida.")
            if not name or len(name) > 120:
                raise ValueError("El nombre del área debe tener entre 1 y 120 caracteres.")
            identity = name.casefold()
            if identity in seen_names:
                continue
            seen_names.add(identity)
            area = organization.areas_operacionales.filter(nombre__iexact=name).first() or organization.areas_operacionales.filter(tipo=kind).first()
            if area:
                area.tipo = kind; area.nombre = name; area.activa = True; area.save(update_fields=["tipo", "nombre", "activa", "updated_at"])
            else:
                AreaOperacional.objects.create(organizacion=organization, nombre=name, tipo=kind, activa=True)
            normalized.append({"tipo": kind, "nombre": name})
        organization.areas_operacionales.exclude(tipo__in=[row["tipo"] for row in normalized]).update(activa=False)
        stored[str(step)] = {"areas": normalized}
    elif step == 3:
        catalog = ensure_flow_catalog(); selected = payload.get("flujos", {})
        if not isinstance(selected, dict) or not selected:
            raise ValueError("Selecciona al menos un aspecto ambiental para continuar.")
        relations = {}
        for key, availability in selected.items():
            if key not in catalog: continue
            state = CapacidadOrganizacion.Estado.APLICA if availability in {"regular", "parcial"} else CapacidadOrganizacion.Estado.SIN_DATOS if availability == "sin_informacion" else CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO
            relations[key] = CapacidadOrganizacion.objects.update_or_create(organizacion=organization, capacidad=catalog[key], defaults={"estado": state, "disponibilidad_inicial": availability})[0]
        organization.capacidades_ambientales.exclude(capacidad__clave__in=relations).update(estado=CapacidadOrganizacion.Estado.NO_APLICA)
        if "relaciones" in payload:
            AreaCapacidadAmbiental.objects.filter(area__organizacion=organization).delete()
            custom = payload.get("relaciones", {})
            active_area_types = set(organization.areas_operacionales.filter(activa=True).values_list("tipo", flat=True))
            if set(custom) - active_area_types: raise ValueError("Una de las áreas no pertenece a la estructura activa de la organización.")
            if any(set(keys) - set(relations) for keys in custom.values()): raise ValueError("Uno de los flujos no pertenece a la organización.")
            for area in organization.areas_operacionales.filter(activa=True):
                for key in custom.get(area.tipo, []):
                    if key in relations: AreaCapacidadAmbiental.objects.get_or_create(area=area, capacidad_organizacion=relations[key])
        if DiagnosticoAmbientalInicial.objects.filter(organizacion=organization, obra=None).exists(): regenerate_diagnostic(organization, user, stored.get("4", {}))
    elif step == 4:
        previous = organization.onboarding_data.get("4", {}) if organization.onboarding_data else {}
        diagnostic = {**previous, **payload}
        diagnostic["flujos"] = {**previous.get("flujos", {}), **payload.get("flujos", {})}
        active_flows = set(organization.capacidades_ambientales.exclude(estado=CapacidadOrganizacion.Estado.NO_APLICA).values_list("capacidad__clave", flat=True))
        diagnostic["flujos"] = {key: value for key, value in diagnostic["flujos"].items() if key in active_flows}
        stored[str(step)] = diagnostic
        if payload.get("completado"):
            if active_flows - set(diagnostic["flujos"]):
                raise ValueError("Completa la disponibilidad de todos los aspectos ambientales.")
            for key, answers in diagnostic["flujos"].items():
                availability = answers.get("disponibilidad")
                if availability not in {"suficiente", "parcial", "sin_informacion", "no_seguro"}:
                    raise ValueError("Una respuesta de disponibilidad no es válida.")
                relation = organization.capacidades_ambientales.get(capacidad__clave=key)
                relation.disponibilidad_inicial = "regular" if availability == "suficiente" else availability
                relation.estado = CapacidadOrganizacion.Estado.APLICA if availability in {"suficiente", "parcial"} else CapacidadOrganizacion.Estado.SIN_DATOS if availability == "sin_informacion" else CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO
                relation.save(update_fields=["disponibilidad_inicial", "estado", "updated_at"])
            regenerate_diagnostic(organization, user, diagnostic)
    elif step == 5:
        organization.onboarding_completado = True
    organization.onboarding_data = stored
    advance_to = step if step == 4 and not payload.get("completado") else min(5, step + 1)
    organization.onboarding_step = 5 if organization.onboarding_completado else max(organization.onboarding_step, advance_to)
    organization.full_clean(); organization.save()
    return organization
