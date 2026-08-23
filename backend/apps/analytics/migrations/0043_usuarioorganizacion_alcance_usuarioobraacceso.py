from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("analytics", "0042_aplicabilidadcapacidadobra_and_more")]

    operations = [
        migrations.AlterField(
            model_name="usuarioorganizacion",
            name="rol",
            field=models.CharField(
                choices=[
                    ("admin", "Administrador"),
                    ("responsable_ambiental", "Responsable ambiental"),
                    ("analista", "Analista ambiental"),
                    ("operador", "Operador"),
                    ("revisor_ambiental", "Revisor ambiental"),
                    ("lector", "Lector"),
                ],
                default="analista",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="usuarioorganizacion",
            name="alcance",
            field=models.CharField(
                choices=[("organizacion", "Toda la organización"), ("obras", "Obras específicas")],
                default="organizacion",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="UsuarioObraAcceso",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("obra", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accesos_usuario", to="analytics.obra")),
                ("usuario_organizacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accesos_obra", to="analytics.usuarioorganizacion")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("usuario_organizacion", "obra"), name="unique_usuario_obra_acceso")]},
        ),
    ]
