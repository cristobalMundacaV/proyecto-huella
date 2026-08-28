from ..models import CompatibilidadVersionMetodologia


def compare_calculations(left, right):
    if left.version_metodologia_id == right.version_metodologia_id:
        status, detail = (
            CompatibilidadVersionMetodologia.Estado.COMPATIBLE,
            "Misma versión metodológica.",
        )
    else:
        relation = (
            CompatibilidadVersionMetodologia.objects.filter(
                version_origen=left.version_metodologia,
                version_destino=right.version_metodologia,
            ).first()
            or CompatibilidadVersionMetodologia.objects.filter(
                version_origen=right.version_metodologia,
                version_destino=left.version_metodologia,
            ).first()
        )
        status = (
            relation.estado
            if relation
            else CompatibilidadVersionMetodologia.Estado.REQUIERE_REVISION
        )
        detail = (
            relation.detalle
            if relation
            else "No existe una evaluación explícita de compatibilidad."
        )
    if left.unidad_resultado != right.unidad_resultado:
        status, detail = (
            CompatibilidadVersionMetodologia.Estado.INCOMPATIBLE,
            "Las unidades de resultado son diferentes.",
        )
    return {
        "estado": status,
        "detalle": detail,
        "calculo_origen": left.id,
        "calculo_destino": right.id,
    }
