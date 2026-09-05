from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import MaterialOperacional, Organizacion, VersionFactorAmbiental
from .services.factor_governance import (create_factor_version,
    create_private_material_factor, transition_factor_version)


class MaterialFactorGovernanceTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Factores privados")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="MAT-CEM", nombre="Cemento Portland", categoria="cemento", unidad_base="kg", proveedor_fabricante="Proveedor")
        self.payload = {"material": self.material.id, "nombre": "EPD Cemento", "valor": "0.2", "unidad_entrada": "kg", "unidad_resultado": "kgCO2e", "fuente_tipo": "epd", "fuente": "TEST", "referencia": "TEST", "alcance_ciclo_vida": "A1-A3", "vigencia_desde": date(2026, 1, 1)}

    def test_crea_factor_privado_opaco_y_borrador_con_contexto_derivado(self):
        factor = create_private_material_factor(self.org, self.material, self.payload)
        version = factor.versiones.get()
        self.assertRegex(factor.codigo, r"^FAM-[0-9A-F]{32}$")
        self.assertEqual(factor.organizacion, self.org)
        self.assertEqual(version.estado, "borrador")
        self.assertEqual(factor.contexto, {"material_codigo":"MAT-CEM","material_categoria":"cemento","producto":"Cemento Portland","proveedor":"Proveedor","especificidad":"producto","alcance_ciclo_vida":"A1-A3","fuente_tipo":"epd"})

    def test_transiciones_y_nueva_version_no_mutan_historia(self):
        factor = create_private_material_factor(self.org, self.material, self.payload)
        first = factor.versiones.get()
        for state in ("pruebas", "validado", "activo"): transition_factor_version(first, state)
        second = create_factor_version(factor, {**self.payload, "valor": "0.3"})
        self.assertEqual(second.version, 2)
        self.assertEqual(first.valor, Decimal("0.2"))
        for state in ("pruebas", "validado"):
            transition_factor_version(second, state)
        with self.assertRaises(ValidationError): transition_factor_version(second, "activo")
        transition_factor_version(first, "obsoleto")
        transition_factor_version(second, "activo")
        self.assertEqual(factor.versiones.filter(estado=VersionFactorAmbiental.Estado.ACTIVO).count(), 1)
