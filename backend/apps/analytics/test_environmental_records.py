from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Obra, Organizacion, RegistroEmision, UsuarioOrganizacion
from .services.environmental_records import (
    create_document_environmental_record,
    create_environmental_record,
    create_external_api_environmental_record,
    normalize_environmental_record,
)
from .views_importaciones import save_registros


def valid_payload(**overrides):
    payload = {
        "fecha": "2026-08-01",
        "actividad": "Consumo electrico",
        "categoria": RegistroEmision.Categoria.ENERGIA,
        "cantidad": "125.50",
        "unidad": "kWh",
        "factor_emision": "0.390000",
    }
    payload.update(overrides)
    return payload


class EnvironmentalRecordEngineTests(TestCase):
    def setUp(self):
        self.organizacion = Organizacion.objects.create(
            organizacion_id="ORG_A",
            nombre="Organizacion A",
            preset=Organizacion.Preset.INDUSTRIAL,
        )

    def test_creacion_manual_normalizada(self):
        user = User.objects.create_user("operador", password="clave-segura-123")
        UsuarioOrganizacion.objects.create(user=user, organizacion=self.organizacion)
        client = APIClient()
        client.force_login(user)
        response = client.post(
            f"/api/organizaciones/{self.organizacion.organizacion_id}/registros-emision/",
            valid_payload(proveedor="Energia Sur", numero_documento="FAC-10"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        registro = RegistroEmision.objects.get()
        self.assertEqual(registro.tipo_ingreso, RegistroEmision.TipoIngreso.MANUAL)
        self.assertEqual(registro.fuente_ingreso, "manual")
        self.assertEqual(registro.numero_documento, "FAC-10")
        self.assertEqual(response.data["actividad"], "Consumo electrico")

    def test_importacion_csv_converge_en_registro_normalizado(self):
        rows = [{"status": "valid", "errors": [], "data": valid_payload(
            fuente_emision="Diesel importado",
            fuente_dato="archivo.csv",
            registro_id="CSV-44",
        )}]
        result = save_registros(rows, self.organizacion)
        registro = RegistroEmision.objects.get()
        self.assertEqual(result["creados"], 1)
        self.assertEqual(registro.tipo_ingreso, RegistroEmision.TipoIngreso.CSV)
        self.assertEqual(registro.identificador_externo, "CSV-44")
        self.assertEqual(registro.metadata["ingesta"]["tipo"], "csv")

    def test_aislamiento_impide_relacion_de_otro_tenant(self):
        otra = Organizacion.objects.create(organizacion_id="ORG_B", nombre="Organizacion B")
        obra_ajena = Obra.objects.create(
            organizacion=otra,
            nombre="Obra ajena",
            fecha_inicio=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            create_environmental_record(
                valid_payload(obra=obra_ajena),
                organizacion=self.organizacion,
                tipo_ingreso=RegistroEmision.TipoIngreso.API_EXTERNA,
            )
        self.assertEqual(RegistroEmision.objects.count(), 0)

    def test_mismo_motor_funciona_con_todos_los_presets(self):
        for preset in Organizacion.Preset.values:
            organizacion = Organizacion.objects.create(
                organizacion_id=f"ORG_{preset.upper()}",
                nombre=f"Organizacion {preset}",
                preset=preset,
            )
            create_environmental_record(
                valid_payload(actividad=f"Actividad {preset}"),
                organizacion=organizacion,
                tipo_ingreso=RegistroEmision.TipoIngreso.MANUAL,
            )
        self.assertEqual(RegistroEmision.objects.count(), len(Organizacion.Preset.values))

    def test_conserva_origen_documento_y_api_sin_deduplicar(self):
        documento = SimpleNamespace(pk=77, nombre="Factura energia", numero_documento="DOC-77")
        document_record = create_document_environmental_record(
            valid_payload(), organizacion=self.organizacion, documento=documento
        )
        api_record = create_external_api_environmental_record(
            valid_payload(identificador_externo="EXT-1"),
            organizacion=self.organizacion,
            sistema="proveedor-energia-api",
        )
        self.assertEqual(document_record.tipo_ingreso, RegistroEmision.TipoIngreso.DOCUMENTO)
        self.assertEqual(document_record.metadata["documento_ambiental_id"], 77)
        self.assertEqual(api_record.tipo_ingreso, RegistroEmision.TipoIngreso.API_EXTERNA)
        self.assertEqual(api_record.fuente_ingreso, "proveedor-energia-api")
        self.assertEqual(api_record.identificador_externo, "EXT-1")

    def test_valida_cantidad_unidad_fecha_y_campos_requeridos(self):
        invalid_payloads = [
            valid_payload(cantidad="0"),
            valid_payload(cantidad="-2"),
            valid_payload(unidad="  "),
            valid_payload(fecha="01/08/2026"),
            valid_payload(actividad=""),
            valid_payload(categoria=""),
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                normalize_environmental_record(
                    payload,
                    organizacion=self.organizacion,
                    tipo_ingreso=RegistroEmision.TipoIngreso.MANUAL,
                )
