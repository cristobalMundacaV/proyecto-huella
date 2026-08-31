from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .services.evidence_validation import (
    classify_evidence_relevance,
    compare_evidence_to_observation,
    evaluate_evidence_validation,
    extract_evidence_claims,
)
from .services.document_extraction import extract_number_near_units


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
