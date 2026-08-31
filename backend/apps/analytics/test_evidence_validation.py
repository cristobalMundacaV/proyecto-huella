from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .services.evidence_validation import (
    classify_evidence_relevance,
    compare_evidence_to_observation,
    evaluate_evidence_validation,
    extract_evidence_claims,
)
from .services.document_extraction import extract_number_near_units
from .services.document_extraction import extract_environmental_document
from .services.document_extractors import VisualAIExtractor


class EvidenceValidationContractTests(SimpleTestCase):
    def observation(self):
        return SimpleNamespace(
            concepto="combustible_consumido",
            valor_numerico=Decimal("180"),
            unidad="L",
            timestamp_observacion=datetime(2026, 9, 3, 12, tzinfo=timezone.utc),
        )

    def validate(self, extraction):
        observation = self.observation()
        relevance = classify_evidence_relevance(extraction, observation)
        comparisons = compare_evidence_to_observation(
            observation,
            extract_evidence_claims(extraction),
            {"tipo_recurso": "diesel"},
        )
        return evaluate_evidence_validation(relevance, comparisons)

    def extraction(self, **claims):
        return {
            "tipo_documento": "factura_combustible",
            "confianza": "0.95",
            "texto_extraido": "Factura de combustible legible",
            "claims": {"fecha": "2026-09-03", **claims},
        }

    def test_factura_coincidente_es_verificada(self):
        result = self.validate(self.extraction(cantidad="180", unidad="L", tipo_recurso="diesel"))
        self.assertEqual(result["estado"], "verificada")
        self.assertTrue(all(item["estado"] == "coincide" for item in result["comparaciones"]))

    def test_cantidad_distinta_es_contradiccion_critica(self):
        result = self.validate(self.extraction(cantidad="120", unidad="L", tipo_recurso="diesel"))
        quantity = next(item for item in result["comparaciones"] if item["campo"] == "cantidad")
        self.assertEqual(result["estado"], "contradiccion")
        self.assertEqual(quantity["estado"], "contradice")
        self.assertEqual(quantity["documental"], "120 L")

    def test_combustible_distinto_es_contradiccion(self):
        result = self.validate(self.extraction(cantidad="180", unidad="L", tipo_recurso="gasolina"))
        fuel = next(item for item in result["comparaciones"] if item["campo"] == "tipo_recurso")
        self.assertEqual(result["estado"], "contradiccion")
        self.assertEqual(fuel["estado"], "contradice")

    def test_documento_sin_cantidad_es_compatible_incompleto(self):
        result = self.validate(self.extraction(tipo_recurso="diesel"))
        self.assertEqual(result["estado"], "compatible_incompleta")

    def test_documento_de_otro_dominio_es_no_pertinente(self):
        extraction = self.extraction(cantidad="180", unidad="L")
        extraction["tipo_documento"] = "boleta_electrica"
        result = self.validate(extraction)
        self.assertEqual(result["estado"], "no_pertinente")

    def test_clasificador_visual_puede_marcar_foto_irrelevante_con_alta_confianza(self):
        result = self.validate({
            "tipo_documento": "otro",
            "relevancia_detectada": "no_pertinente",
            "motivo_relevancia": "La imagen no contiene un documento operacional.",
            "confianza": "0.96",
            "texto_extraido": "",
            "claims": {},
        })
        self.assertEqual(result["estado"], "no_pertinente")

    def test_confianza_baja_no_aprueba_ni_rechaza_automaticamente(self):
        extraction = self.extraction(cantidad="180", unidad="L", tipo_recurso="diesel")
        extraction["confianza"] = "0.60"
        self.assertEqual(self.validate(extraction)["estado"], "compatible_incompleta")
        extraction["tipo_documento"] = "boleta_electrica"
        self.assertEqual(self.validate(extraction)["estado"], "indeterminada")

    def test_archivo_ilegible_es_indeterminado_sin_inventar_campos(self):
        result = self.validate({
            "tipo_documento": "otro",
            "confianza": "0.20",
            "texto_extraido": "",
            "claims": {},
        })
        self.assertEqual(result["estado"], "indeterminada")
        self.assertEqual(extract_evidence_claims({"claims": {}}), {})

    def test_conversion_deterministica_es_trazable(self):
        result = self.validate(self.extraction(cantidad="0.18", unidad="m3", tipo_recurso="diesel"))
        quantity = next(item for item in result["comparaciones"] if item["campo"] == "cantidad")
        self.assertEqual(result["estado"], "verificada")
        self.assertEqual(quantity["estado"], "compatible_por_conversion")
        self.assertEqual(quantity["conversion"], "m3 → L")
        self.assertTrue(result["motivos"])

    def test_separador_de_miles_chileno_no_se_interpreta_como_decimal(self):
        self.assertEqual(
            extract_number_near_units("Factura diesel 1.800 L")["cantidad_sugerida"],
            "1800",
        )

    def test_png_recibe_claims_reales_del_analisis_visual(self):
        visual_result = {
            "tipo_documento": "factura_combustible",
            "relevancia_detectada": "pertinente",
            "motivo_relevancia": "Factura de combustible legible.",
            "confianza_clasificacion": 0.97,
            "legibilidad": "legible",
            "confianza_extraccion": 0.96,
            "claims": {
                "tipo_recurso": {"valor_original": "Diésel Grado B", "valor_normalizado": "diesel", "confianza": 0.98},
                "cantidad": {"valor_original": "250,00", "valor_normalizado": "250", "confianza": 0.99},
                "unidad": {"valor_original": "Litros", "valor_normalizado": "L", "confianza": 0.99},
                "fecha": {"valor_original": "04-09-2026", "valor_normalizado": "2026-09-04", "confianza": 0.98},
            },
        }
        response = Mock(output_text=__import__("json").dumps(visual_result))
        client = Mock()
        client.responses.create.return_value = response
        upload = SimpleUploadedFile("factura.png", b"\x89PNG\r\n", content_type="image/png")
        with self.settings(OPENAI_API_KEY="test"), patch(
            "apps.analytics.services.openai_document_provider.OpenAI", return_value=client
        ):
            extraction = extract_environmental_document(upload)

        self.assertEqual(extraction["claims"]["cantidad"], "250")
        self.assertEqual(extraction["claims"]["tipo_recurso"], "diesel")
        self.assertEqual(extraction["claims_trazables"]["cantidad"]["valor_original"], "250,00")
        observation = self.observation()
        observation.valor_numerico = Decimal("250")
        relevance = classify_evidence_relevance(extraction, observation)
        comparisons = compare_evidence_to_observation(
            observation,
            extract_evidence_claims(extraction),
            {"tipo_recurso": "diesel", "claims_trazables": extraction["claims_trazables"]},
        )
        result = evaluate_evidence_validation(relevance, comparisons)
        date_comparison = next(item for item in result["comparaciones"] if item["campo"] == "fecha")
        self.assertEqual(result["estado"], "contradiccion")
        self.assertEqual(date_comparison["estado"], "contradice")
        self.assertEqual(
            [item["campo"] for item in result["comparaciones"] if item["estado"] == "contradice"],
            ["fecha"],
        )

    def test_documento_textual_funciona_sin_ia_y_respeta_contrato(self):
        upload = SimpleUploadedFile(
            "factura.txt",
            b"Factura combustible diesel 250,00 litros 05-09-2026",
            content_type="text/plain",
        )
        with self.settings(OPENAI_API_KEY=""):
            result = extract_environmental_document(upload)
        contract = {
            "tipo_documento", "relevancia_detectada", "confianza",
            "texto_extraido", "claims", "claims_trazables", "origen_extraccion",
        }
        self.assertTrue(contract.issubset(result))
        self.assertEqual(result["origen_extraccion"], "texto_heuristico")
        self.assertEqual(result["claims"]["cantidad"], "250")

    def test_imagen_sin_api_key_usa_fallback_seguro(self):
        upload = SimpleUploadedFile("factura.png", b"\x89PNG", content_type="image/png")
        with self.settings(OPENAI_API_KEY=""):
            result = extract_environmental_document(upload)
        self.assertEqual(result["origen_extraccion"], "visual_no_disponible")
        self.assertEqual(result["relevancia_detectada"], "indeterminado")
        self.assertEqual(result["claims"], {})

    def test_fallo_de_proveedor_visual_no_rompe_extraccion(self):
        provider = Mock()
        provider.extract_visual.side_effect = RuntimeError("proveedor caido")
        result = VisualAIExtractor(provider).extract(
            SimpleUploadedFile("factura.png", b"png", content_type="image/png")
        )
        self.assertEqual(result.origen_extraccion, "visual_no_disponible")
        self.assertEqual(result.claims, {})

    def test_logica_ambiental_no_importa_openai(self):
        services = Path(__file__).parent / "services"
        for name in ("quality_v2.py", "eligibility_v2.py", "calculation_v2.py", "evidence_validation.py"):
            source = (services / name).read_text(encoding="utf-8")
            self.assertNotIn("from openai", source.lower())
            self.assertNotIn("import openai", source.lower())

    def test_contrato_refactorizado_preserva_resultado_del_motor(self):
        legacy = self.extraction(cantidad="180", unidad="L", tipo_recurso="diesel")
        upload = SimpleUploadedFile(
            "factura.txt",
            b"Factura combustible diesel 180 litros 03-09-2026",
            content_type="text/plain",
        )
        with self.settings(OPENAI_API_KEY=""):
            refactored = extract_environmental_document(upload)
        self.assertEqual(self.validate(legacy)["estado"], "verificada")
        self.assertEqual(self.validate(refactored)["estado"], "verificada")
        self.assertEqual(
            {item["campo"]: item["estado"] for item in self.validate(legacy)["comparaciones"]},
            {item["campo"]: item["estado"] for item in self.validate(refactored)["comparaciones"]},
        )
