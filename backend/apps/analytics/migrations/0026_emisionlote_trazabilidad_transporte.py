from django.db import migrations, models


def add_missing_transport_traceability_columns(apps, schema_editor):
    EmisionLote = apps.get_model("analytics", "EmisionLote")
    table_name = EmisionLote._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    fields = [
        models.JSONField(blank=True, null=True, name="destino_coords"),
        models.CharField(blank=True, default="", max_length=240, name="destino_transporte"),
        models.DecimalField(
            blank=True,
            decimal_places=3,
            max_digits=12,
            null=True,
            name="distancia_km",
        ),
        models.JSONField(blank=True, null=True, name="origen_coords"),
        models.CharField(blank=True, default="", max_length=240, name="origen_transporte"),
        models.JSONField(blank=True, default=list, name="ruta_geometry"),
    ]

    for field in fields:
        if field.name in existing_columns:
            continue

        field.set_attributes_from_name(field.name)
        schema_editor.add_field(EmisionLote, field)


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0025_lote_unidad_operativa_not_null"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_missing_transport_traceability_columns,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="emisionlote",
                    name="destino_coords",
                    field=models.JSONField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="emisionlote",
                    name="destino_transporte",
                    field=models.CharField(blank=True, max_length=240),
                ),
                migrations.AddField(
                    model_name="emisionlote",
                    name="distancia_km",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=12,
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="emisionlote",
                    name="origen_coords",
                    field=models.JSONField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="emisionlote",
                    name="origen_transporte",
                    field=models.CharField(blank=True, max_length=240),
                ),
                migrations.AddField(
                    model_name="emisionlote",
                    name="ruta_geometry",
                    field=models.JSONField(blank=True, default=list),
                ),
            ],
        ),
    ]
