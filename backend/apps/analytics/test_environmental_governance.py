from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import DocumentoAmbiental, EvidenciaObra, Organizacion, RegistroEmision
from .services.environmental_records import (
    build_environmental_fingerprints,
    create_document_environmental_record,
    create_environmental_record,
    link_evidence_to_records,
    normalize_environmental_record,
)


def payload(**overrides):
    data = {
        "fecha": "2026-08-10",
        "actividad": "Consumo eléctrico",
        "categoria": "Energía",
        "cantidad": "100.000",
        "unidad": "kWh",
        "factor_emision": "0.39",
        "proveedor": "Empresa Eléctrica Sur",
        "numero_documento": "FAC 001",
        "area_operacional": "Planta Norte",
        "unidad_operacional": "Línea 1",
    }
    data.update(overrides)
    return data


class EnvironmentalGovernanceTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(organizacion_id="GOV_A", nombre="Gobernanza A")

    def create(self, kind, **overrides):
        return create_environmental_record(
            payload(**overrides), organizacion=self.org, tipo_ingreso=kind, fuente_ingreso=kind
        )

    def test_mismo_hecho_manual_excel_api_tiene_un_solo_registro_contabilizable(self):
        manual = self.create(RegistroEmision.TipoIngreso.MANUAL)
        excel = self.create(RegistroEmision.TipoIngreso.EXCEL)
        api = self.create(RegistroEmision.TipoIngreso.API_EXTERNA)
        self.assertEqual(manual.pk, excel.pk)
        self.assertEqual(manual.pk, api.pk)
        self.assertEqual(RegistroEmision.objects.filter(contabilizable=True).count(), 1)
        manual.refresh_from_db()
        self.assertEqual(len(manual.metadata["origenes_ingesta"]), 3)

    def test_mismo_documento_desde_fuentes_distintas_reutiliza_hecho(self):
        doc_pdf = DocumentoAmbiental.objects.create(
            organizacion=self.org, tipo_documento="factura", nombre="Factura PDF",
            fecha_documento=date(2026, 8, 10), fuente_origen=DocumentoAmbiental.FuenteOrigen.PDF,
        )
        doc_excel = DocumentoAmbiental.objects.create(
            organizacion=self.org, tipo_documento="factura", nombre="Factura Excel",
            fecha_documento=date(2026, 8, 10), fuente_origen=DocumentoAmbiental.FuenteOrigen.EXCEL,
        )
        first = create_document_environmental_record(payload(), organizacion=self.org, documento=doc_pdf)
        second = create_document_environmental_record(payload(), organizacion=self.org, documento=doc_excel)
        self.assertEqual(first.pk, second.pk)
        self.assertTrue(doc_pdf.registros_emision.filter(pk=first.pk).exists())
        self.assertTrue(doc_excel.registros_emision.filter(pk=first.pk).exists())

    def test_hechos_distintos_no_colisionan(self):
        first = self.create(RegistroEmision.TipoIngreso.MANUAL)
        second = self.create(RegistroEmision.TipoIngreso.EXCEL, cantidad="101")
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertTrue(first.contabilizable)
        self.assertTrue(second.contabilizable)

    def test_identificador_distinto_marca_posible_duplicado_sin_contabilizar(self):
        canonical = self.create(RegistroEmision.TipoIngreso.MANUAL, identificador_externo="MAN-1")
        candidate = self.create(RegistroEmision.TipoIngreso.API_EXTERNA, identificador_externo="API-9")
        self.assertNotEqual(canonical.pk, candidate.pk)
        self.assertEqual(candidate.estado_gobernanza, RegistroEmision.EstadoGobernanza.POSIBLE_DUPLICADO)
        self.assertEqual(candidate.registro_canonico, canonical)
        self.assertFalse(candidate.contabilizable)
        self.assertEqual(RegistroEmision.objects.filter(contabilizable=True).count(), 1)

    def test_fingerprint_esta_aislado_por_organizacion(self):
        other = Organizacion.objects.create(organizacion_id="GOV_B", nombre="Gobernanza B")
        first = self.create(RegistroEmision.TipoIngreso.MANUAL)
        second = create_environmental_record(
            payload(), organizacion=other, tipo_ingreso=RegistroEmision.TipoIngreso.MANUAL
        )
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(RegistroEmision.objects.filter(contabilizable=True).count(), 2)

    def test_multiples_evidencias_y_una_evidencia_para_varios_registros(self):
        first = self.create(RegistroEmision.TipoIngreso.MANUAL)
        second = self.create(RegistroEmision.TipoIngreso.MANUAL, actividad="Consumo diesel")
        evidence_a = EvidenciaObra.objects.create(
            organizacion=self.org, nombre="Respaldo A",
            archivo=SimpleUploadedFile("a.pdf", b"pdf"),
        )
        evidence_b = EvidenciaObra.objects.create(
            organizacion=self.org, nombre="Respaldo B",
            archivo=SimpleUploadedFile("b.pdf", b"pdf"),
        )
        link_evidence_to_records(evidence_a, [first, second], organizacion=self.org)
        link_evidence_to_records(evidence_b, [first], organizacion=self.org)
        self.assertEqual(evidence_a.registros_emision.count(), 2)
        self.assertEqual(first.evidencias.count(), 2)

    def test_fingerprint_estable_ante_formato_texto_unidad_y_decimal(self):
        normalized_a = normalize_environmental_record(
            payload(), organizacion=self.org, tipo_ingreso=RegistroEmision.TipoIngreso.MANUAL
        )
        normalized_b = normalize_environmental_record(
            payload(
                actividad="  CONSUMO ELECTRICO ", categoria="energia",
                cantidad=Decimal("100"), unidad="kw h",
                proveedor="empresa electrica sur", numero_documento="fac-001",
                area_operacional="PLANTA   NORTE", unidad_operacional="linea 1",
            ),
            organizacion=self.org, tipo_ingreso=RegistroEmision.TipoIngreso.PDF if hasattr(RegistroEmision.TipoIngreso, "PDF") else RegistroEmision.TipoIngreso.DOCUMENTO,
        )
        self.assertEqual(build_environmental_fingerprints(normalized_a), build_environmental_fingerprints(normalized_b))
