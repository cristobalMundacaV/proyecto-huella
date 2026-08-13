from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.analytics.models import FactorEmision


REFERENCE_SOURCE = "Referencia interna - validar antes de uso oficial"


class Command(BaseCommand):
    help = "Crea factores referenciales iniciales por preset. Requieren validacion antes de uso oficial."

    def handle(self, *args, **options):
        rows = [
            ("construccion", "", "Materiales", "Material referencial", "kg", "0.000000"),
            ("construccion", "", "Maquinaria", "Maquinaria referencial", "horas maquina", "0.000000"),
            ("construccion", "", "Transporte", "Transporte referencial", "km", "0.000000"),
            ("construccion", "", "Energia", "Energia referencial", "kWh", "0.000000"),
            ("construccion", "", "Residuos", "Residuos referencial", "kg", "0.000000"),
            ("construccion", "", "Agua", "Agua referencial", "m3", "0.000000"),
            ("aserradero", "recepcion_trozas", "Materia prima", "Recepcion de trozas referencial", "m3", "0.000000"),
            ("aserradero", "produccion", "Produccion", "Produccion aserradero referencial", "m3 procesados", "0.000000"),
            ("aserradero", "secado", "Secado", "Secado energia referencial", "kWh", "0.000000"),
            ("aserradero", "energia", "Energia", "Energia aserradero referencial", "kWh", "0.000000"),
            ("aserradero", "transporte_forestal", "Transporte", "Diesel transporte forestal referencial", "litros diesel", "0.000000"),
            ("aserradero", "residuos_subproductos", "Subproductos", "Residuos valorizacion referencial", "kg", "0.000000"),
            ("transporte", "combustible", "Combustible", "Combustible transporte referencial", "litros", "0.000000"),
            ("transporte", "rutas", "Rutas", "Ruta transporte referencial", "km", "0.000000"),
            ("transporte", "flota", "Flota", "Flota referencial", "unidad", "0.000000"),
            ("transporte", "mantenciones", "Mantencion", "Mantencion referencial", "evento", "0.000000"),
            ("transporte", "carga", "Carga", "Carga referencial", "ton", "0.000000"),
            ("industrial", "energia", "Energia", "Energia industrial referencial", "kWh", "0.000000"),
            ("industrial", "combustible", "Combustible", "Combustible industrial referencial", "litros", "0.000000"),
            ("industrial", "procesos", "Procesos", "Proceso industrial referencial", "unidad", "0.000000"),
            ("industrial", "residuos", "Residuos", "Residuo industrial referencial", "kg", "0.000000"),
            ("industrial", "agua", "Agua", "Agua industrial referencial", "m3", "0.000000"),
            ("industrial", "transporte", "Transporte", "Transporte industrial referencial", "km", "0.000000"),
        ]
        created = 0
        for preset, module, categoria, actividad, unidad, factor in rows:
            _, was_created = FactorEmision.objects.get_or_create(
                actividad=actividad,
                unidad=unidad,
                fuente=REFERENCE_SOURCE,
                anio=2026,
                defaults={
                    "preset": preset,
                    "module": module,
                    "categoria": categoria,
                    "factor_emision": Decimal(factor),
                    "alcance": "Referencial",
                    "descripcion": "Factor inicial referencial. Validar antes de reportes oficiales.",
                    "metadata": {"requires_validation": True},
                    "activo": True,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Factores referenciales creados: {created}"))
