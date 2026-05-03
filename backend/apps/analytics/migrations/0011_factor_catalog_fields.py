from django.db import migrations, models


def strip_accents(value):
    import unicodedata

    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_activity_key(value):
    import re

    aliases = {
        "diesel_movil": "diesel_combustion_movil",
        "diesel_combustion_movil": "diesel_combustion_movil",
        "diesel_estacionario": "diesel_combustion_estacionaria",
        "diesel_combustion_estacionaria": "diesel_combustion_estacionaria",
        "camion_diesel_rigido_promedio": "camion_diesel_rigido_promedio",
        "carton_virgen": "carton_virgen",
        "carton_reciclado": "carton_reciclado",
    }
    text = strip_accents(value).lower()
    text = re.sub(r"[\s\-–—/]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    text = "_".join(
        token for token in text.split("_") if token not in {"de", "del", "la", "el"}
    )
    return aliases.get(text, text)


def infer_category(*values):
    import re

    text = normalize_activity_key(" ".join(str(value or "") for value in values))
    tokens = set(text.split("_"))

    if re.search(r"(residuo|relleno|compostaje|reciclaje|disposicion|tratamiento_disposicion)", text):
        return "Residuos"
    if re.search(r"(refrigerante|r507|r407|r410|fuga)", text):
        return "Refrigerantes"
    if tokens.intersection({"camion", "tren", "barco", "avion", "vehiculo", "bus", "metro", "transporte", "carga"}) or re.search(r"(t_km|km_pasajero)", text):
        return "Transporte"
    if re.search(r"(diesel|glp|gas_natural|gas_licuado|combustion|combustible)", text):
        return "Combustible"
    if re.search(r"(electricidad|electrico|sen|los_lagos|aysen|magallanes|kwh)", text):
        return "Electricidad"
    if "agua" in text:
        return "Agua"
    if re.search(r"(carton|papel|plastico|vidrio|aluminio|notebook)", text):
        return "Materiales"
    return "Otros"


def populate_catalog_fields(apps, schema_editor):
    FactorEmision = apps.get_model("analytics", "FactorEmision")
    EmisionLote = apps.get_model("analytics", "EmisionLote")

    seen = {}
    for factor in FactorEmision.objects.order_by("id"):
        factor.actividad_key = normalize_activity_key(
            factor.actividad_key or factor.actividad
        )
        factor.categoria = factor.categoria or infer_category(
            factor.actividad,
            factor.fuente,
            factor.unidad,
        )
        key = (
            factor.actividad_key,
            factor.unidad.lower(),
            factor.fuente.lower(),
            factor.anio,
        )

        if key in seen:
            # Keep the earliest row to avoid violating the normalized unique key.
            factor.actividad_key = f"{factor.actividad_key}_{factor.id}"
        else:
            seen[key] = factor.id

        factor.save(update_fields=["actividad_key", "categoria"])

    for actividad in EmisionLote.objects.order_by("id"):
        actividad.actividad_key = normalize_activity_key(actividad.actividad)
        actividad.save(update_fields=["actividad_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0010_emisionlote_fecha_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="emisionlote",
            name="actividad_key",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="factoremision",
            name="actividad_key",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="factoremision",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("Combustible", "Combustible"),
                    ("Electricidad", "Electricidad"),
                    ("Transporte", "Transporte"),
                    ("Agua", "Agua"),
                    ("Materiales", "Materiales"),
                    ("Residuos", "Residuos"),
                    ("Refrigerantes", "Refrigerantes"),
                    ("Otros", "Otros"),
                ],
                default="Otros",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="factoremision",
            name="descripcion",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(populate_catalog_fields, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="factoremision",
            constraint=models.UniqueConstraint(
                fields=("actividad_key", "unidad", "fuente", "anio"),
                name="unique_factor_emision_key_fuente_anio",
            ),
        ),
        migrations.AlterModelOptions(
            name="factoremision",
            options={"ordering": ["categoria", "actividad", "unidad", "-anio"]},
        ),
    ]
