from decimal import Decimal

from django.db import models


class LecturaSensor(models.Model):
    class Tipo(models.TextChoices):
        DIESEL_LITROS = "diesel_litros", "Diesel litros"
        GASOLINA_LITROS = "gasolina_litros", "Gasolina litros"
        ELECTRICIDAD_KWH = "electricidad_kwh", "Electricidad kWh"
        HORAS_MAQUINARIA = "horas_maquinaria", "Horas maquinaria"
        TEMPERATURA = "temperatura", "Temperatura"
        HUMEDAD = "humedad", "Humedad"

    UNIDADES_POR_TIPO = {
        Tipo.DIESEL_LITROS: "litros",
        Tipo.GASOLINA_LITROS: "litros",
        Tipo.ELECTRICIDAD_KWH: "kWh",
        Tipo.HORAS_MAQUINARIA: "horas",
        Tipo.TEMPERATURA: "C",
        Tipo.HUMEDAD: "%",
    }

    FACTORES_CO2E = {
        Tipo.DIESEL_LITROS: Decimal("2.68"),
        Tipo.GASOLINA_LITROS: Decimal("2.31"),
        Tipo.ELECTRICIDAD_KWH: Decimal("0.39"),
        Tipo.HORAS_MAQUINARIA: Decimal("5.50"),
        Tipo.TEMPERATURA: Decimal("0"),
        Tipo.HUMEDAD: Decimal("0"),
    }

    constructora = models.CharField(max_length=180)
    etapa_obra = models.CharField(max_length=180)
    sensor = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=3)
    unidad = models.CharField(max_length=40)
    co2e_estimado = models.DecimalField(max_digits=14, decimal_places=3)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_registro"]
        indexes = [
            models.Index(fields=["fecha_registro"]),
            models.Index(fields=["sensor", "fecha_registro"]),
            models.Index(fields=["constructora", "fecha_registro"]),
            models.Index(fields=["tipo", "fecha_registro"]),
        ]

    def save(self, *args, **kwargs):
        self.unidad = self.UNIDADES_POR_TIPO.get(self.tipo, "")
        factor = self.FACTORES_CO2E.get(self.tipo, Decimal("0"))
        self.co2e_estimado = (self.valor or Decimal("0")) * factor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sensor} - {self.tipo} - {self.valor} {self.unidad}"
