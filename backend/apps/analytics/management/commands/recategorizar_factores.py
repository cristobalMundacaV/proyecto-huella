from django.core.management.base import BaseCommand

from apps.analytics.models import FactorEmision, normalize_key


def infer_categoria_construccion(actividad, unidad):
    text = f"{actividad} {unidad}".lower()
    if any(token in text for token in ["hormigon", "cemento", "acero", "arido", "yeso", "material"]):
        return FactorEmision.Categoria.MATERIALES
    if any(token in text for token in ["transporte", "camion", "km", "viaje"]):
        return FactorEmision.Categoria.TRANSPORTE
    if any(token in text for token in ["maquinaria", "excavadora", "grua", "retroexcavadora", "compactadora"]):
        return FactorEmision.Categoria.MAQUINARIA
    if any(token in text for token in ["electricidad", "kwh", "generador", "energia"]):
        return FactorEmision.Categoria.ENERGIA
    if any(token in text for token in ["agua", "litros agua"]):
        return FactorEmision.Categoria.AGUA
    if any(token in text for token in ["residuo", "escombro", "retiro"]):
        return FactorEmision.Categoria.RESIDUOS
    return FactorEmision.Categoria.OTROS


class Command(BaseCommand):
    help = "Recategoriza factores de emision con reglas simples de construccion."

    def handle(self, *args, **options):
        updated = 0
        for factor in FactorEmision.objects.all().iterator():
            factor.categoria = infer_categoria_construccion(factor.actividad, factor.unidad)
            factor.actividad_key = normalize_key(factor.actividad).replace(" ", "_")
            factor.save(update_fields=["categoria", "actividad_key", "updated_at"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Factores recategorizados: {updated}."))
