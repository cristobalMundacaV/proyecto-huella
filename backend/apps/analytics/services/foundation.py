from django.db import transaction

from ..models import CapacidadAmbiental, CapacidadOrganizacion, DiagnosticoAmbientalInicial, Organizacion


CAPACIDADES_CATALOGO = [
    ("energia", "Energia"), ("agua", "Agua"), ("combustibles", "Combustibles"),
    ("transporte", "Transporte"), ("maquinaria", "Maquinaria"), ("mantenimiento", "Mantenimiento"),
    ("materiales", "Materiales"), ("residuos", "Residuos"),
    ("generacion_propia", "Generacion propia"), ("continuidad_operacional", "Continuidad operacional"),
    ("ruido", "Ruido"), ("gestion_hidrica_suelo", "Gestion hidrica y suelo"),
]

PRESET_CAPACIDADES = {Organizacion.Preset.CONSTRUCCION: [clave for clave, _ in CAPACIDADES_CATALOGO]}


@transaction.atomic
def inicializar_capacidades_preset(organizacion):
    catalogo = {}
    for orden, (clave, nombre) in enumerate(CAPACIDADES_CATALOGO):
        capacidad, _ = CapacidadAmbiental.objects.get_or_create(clave=clave, defaults={"nombre": nombre, "orden": orden})
        catalogo[clave] = capacidad
    recomendadas = PRESET_CAPACIDADES.get(organizacion.preset, [])
    for clave in recomendadas:
        relacion, creada = CapacidadOrganizacion.objects.get_or_create(
            organizacion=organizacion, capacidad=catalogo[clave],
            defaults={"recomendada_por_preset": True},
        )
        if creada:
            relacion.recomendada_por_preset = True
    return CapacidadOrganizacion.objects.filter(organizacion=organizacion).select_related("capacidad")


def resumen_preparacion_ambiental(organizacion):
    diagnostico = DiagnosticoAmbientalInicial.objects.filter(organizacion=organizacion, obra__isnull=True).first()
    capacidades = CapacidadOrganizacion.objects.filter(organizacion=organizacion)
    configuradas = capacidades.exclude(estado=CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO).count()
    aplicables = capacidades.exclude(estado__in=[CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO, CapacidadOrganizacion.Estado.NO_APLICA])
    linea_base_pendiente = aplicables.exclude(estado=CapacidadOrganizacion.Estado.OPERATIVA).exists()
    todas_configuradas = capacidades.exists() and configuradas == capacidades.count()
    preparada = bool(
        diagnostico and diagnostico.estado == DiagnosticoAmbientalInicial.Estado.COMPLETADO
        and todas_configuradas and organizacion.unidades_operacionales.exists()
        and organizacion.procesos_operacionales.exists()
    )
    return {
        "requiere_diagnostico": not diagnostico or diagnostico.estado in ["pendiente", "requiere_actualizacion"],
        "diagnostico_en_progreso": bool(diagnostico and diagnostico.estado == "en_progreso"),
        "capacidades_configuradas": configuradas,
        "linea_base_pendiente": linea_base_pendiente,
        "preparada_para_operacion": preparada,
        "siguiente_paso": "Comenzar captura de datos" if preparada else ("Completar perfil ambiental" if not diagnostico or diagnostico.estado != "completado" else "Configurar capacidades y procesos"),
    }
