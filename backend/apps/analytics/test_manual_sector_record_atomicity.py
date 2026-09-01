from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import (
    ActividadOperacional,
    AreaOperacional,
    EspacioTrabajoOperacional,
    DiscrepanciaDato,
    EvidenciaObra,
    FuenteDatos,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    UsuarioAreaOperacional,
    UsuarioOrganizacion,
    VersionEvidencia,
)


class ManualSectorRecordAtomicityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("marcela", first_name="Marcela", password="test-pass")
        self.organization = Organizacion.objects.create(nombre="Constructora Atomicidad", preset="construccion")
        self.membership = UsuarioOrganizacion.objects.create(
            user=self.user,
            organizacion=self.organization,
            rol=UsuarioOrganizacion.Rol.OPERADOR,
        )
        self.work = Obra.objects.create(
            id=71,
            organizacion=self.organization,
            nombre="Edificio Los Robles",
            fecha_inicio="2026-08-25",
        )
        self.area = AreaOperacional.objects.create(
            organizacion=self.organization,
            nombre="Medio ambiente",
            tipo="medio_ambiente_sostenibilidad",
        )
        self.workspace = EspacioTrabajoOperacional.objects.create(
            usuario_organizacion=self.membership,
            area=self.area,
            obra=self.work,
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Vale de combustible",
            tipo="manual",
        )
        self.client.force_login(self.user)
        self.url = f"/api/organizaciones/{self.organization.organizacion_id}/flujos-ambientales/registro-manual/"

    def payload(self, **overrides):
        payload = {
            "obra": self.work.id,
            "tipo_actividad": "consumo_combustible_estacionario",
            "codigo_actividad": "manual-combustibles-test",
            "nombre_actividad": "Registro manual · combustibles",
            "flujo": "combustible_estacionario",
            "periodo_inicio": "2026-08-25T12:00:00",
            "concepto": "combustible_consumido",
            "valor_numerico": "20",
            "unidad": "L",
            "fuente": self.source.id,
            "tipo_recurso": "diesel",
            "destino_operacional": "generador",
        }
        payload.update(overrides)
        return payload

    def post(self, payload, organization_id=None):
        url = self.url if organization_id is None else f"/api/organizaciones/{organization_id}/flujos-ambientales/registro-manual/"
        return self.client.post(
            url,
            payload,
            format="multipart",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )

    def process_document(self, response):
        evidence = response.data["evidencia"]
        return self.client.post(
            f"/api/organizaciones/{self.organization.organizacion_id}/evidencias/{evidence['id']}/versiones/{evidence['version_actual']}/procesar/",
            {},
            format="json",
        )

    def test_registro_sin_evidencia_crea_actividad_y_registro(self):
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ActividadOperacional.objects.count(), 1)
        self.assertEqual(RegistroFlujoAmbiental.objects.count(), 1)
        self.assertEqual(EvidenciaObra.objects.count(), 0)

    def test_area_principal_resuelve_y_crea_contexto_sin_workspace_expuesto(self):
        self.workspace.delete()
        UsuarioAreaOperacional.objects.create(
            usuario_organizacion=self.membership,
            area=self.area,
            cargo="Encargada ambiental",
            es_principal=True,
        )

        response = self.client.post(
            self.url,
            self.payload(periodo_inicio="2026-09-03T12:00:00"),
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        workspace = EspacioTrabajoOperacional.objects.get()
        self.assertEqual(workspace.usuario_organizacion, self.membership)
        self.assertEqual(workspace.area, self.area)
        self.assertEqual(workspace.obra_id, 71)
        self.assertEqual(ActividadOperacional.objects.get().timestamp_inicio.date().isoformat(), "2026-09-03")

    def test_registro_con_evidencia_conserva_todos_los_vinculos(self):
        response = self.post(self.payload(
            evidencia_archivo=SimpleUploadedFile("vale.txt", b"respaldo combustible", content_type="text/plain"),
            evidencia_nombre="Registro de abastecimiento de combustible",
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        evidence = EvidenciaObra.objects.get()
        observation = Observacion.objects.select_related("evidencia", "fuente").get()
        self.assertEqual(evidence.obra, self.work)
        self.assertEqual(evidence.area_origen, self.area)
        self.assertEqual(evidence.usuario_origen, self.user)
        self.assertEqual(evidence.metadata_extraccion["workspace_id"], self.workspace.id)
        self.assertEqual(
            evidence.metadata_extraccion["flujo"],
            RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
        )
        self.assertEqual(observation.evidencia, evidence)
        self.assertEqual(observation.fuente, self.source)
        self.assertIsNotNone(observation.version_evidencia)
        self.assertEqual(VersionEvidencia.objects.filter(evidencia=evidence).count(), 1)

    def test_archivo_de_evidencia_se_entrega_autenticado_inline(self):
        content = b"\x89PNG\r\n\x1a\ncontenido-prueba"
        response = self.post(self.payload(
            evidencia_archivo=SimpleUploadedFile("factura.png", content, content_type="image/png"),
            evidencia_tipo="factura_combustible",
        ))
        self.assertEqual(response.status_code, 201, response.data)
        evidence = EvidenciaObra.objects.get()

        file_response = self.client.get(f"/api/context/evidence/{evidence.id}/file/")

        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response["Content-Type"], "image/png")
        self.assertIn("inline", file_response["Content-Disposition"])
        self.assertEqual(b"".join(file_response.streaming_content), content)

    def test_factura_coincidente_verifica_documento_y_mejora_calidad(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustible-verificado",
            periodo_inicio="2026-09-03T12:00:00",
            valor_numerico="180",
            evidencia_archivo=SimpleUploadedFile(
                "factura-diesel.txt",
                b"Factura combustible diesel 180 litros 03-09-2026",
                content_type="text/plain",
            ),
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["validacion_documental"]["estado_procesamiento"], "recibida")
        processed = self.process_document(response)
        self.assertEqual(processed.status_code, 200, processed.data)
        self.assertEqual(processed.data["resultado_documental"]["veredicto"], "verificada")
        self.assertEqual(Observacion.objects.get().evaluaciones_calidad.latest("id").estado, "confiable")
        version = VersionEvidencia.objects.get()
        self.assertEqual(version.metadata_tecnica["document_result"]["veredicto"], "verificada")

    def test_factura_con_cantidad_distinta_crea_discrepancia(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustible-contradictorio",
            periodo_inicio="2026-09-03T12:00:00",
            valor_numerico="180",
            evidencia_archivo=SimpleUploadedFile(
                "factura-diesel.txt",
                b"Factura combustible diesel 120 litros 03-09-2026",
                content_type="text/plain",
            ),
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        processed = self.process_document(response)
        self.assertEqual(processed.data["resultado_documental"]["veredicto"], "contradiccion")
        discrepancy = DiscrepanciaDato.objects.get(concepto="evidencia_cantidad")
        self.assertEqual(discrepancy.severidad, DiscrepanciaDato.Severidad.ALTA)
        self.assertIn('"documental": "120 L"', discrepancy.motivo)
        self.assertEqual(Observacion.objects.get().evaluaciones_calidad.latest("id").estado, "requiere_revision")

    def test_factura_con_recurso_distinto_crea_solo_discrepancia_de_recurso(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustible-recurso-contradictorio",
            periodo_inicio="2026-09-06T12:00:00",
            valor_numerico="250",
            evidencia_archivo=SimpleUploadedFile(
                "factura.txt",
                b"Factura combustible Gasolina 250 L 06-09-2026",
                content_type="text/plain",
            ),
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        processed = self.process_document(response)
        self.assertEqual(processed.data["resultado_documental"]["veredicto"], "contradiccion")
        self.assertEqual(
            list(DiscrepanciaDato.objects.values_list("concepto", flat=True)),
            ["evidencia_tipo_recurso"],
        )

    def test_factura_sin_cantidad_es_incompleta_y_no_crea_discrepancia(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustible-incompleto",
            periodo_inicio="2026-09-06T12:00:00",
            valor_numerico="250",
            evidencia_archivo=SimpleUploadedFile(
                "factura.txt",
                b"Factura combustible Diesel Grado B 06-09-2026",
                content_type="text/plain",
            ),
            evidencia_tipo="factura_combustible",
        ))

        self.assertEqual(response.status_code, 201, response.data)
        processed = self.process_document(response)
        self.assertEqual(processed.data["resultado_documental"]["veredicto"], "compatible_incompleta")
        quantity = next(
            item for item in processed.data["resultado_documental"]["comparaciones"]
            if item["campo"] == "cantidad"
        )
        self.assertEqual(quantity["estado"], "no_disponible")
        self.assertFalse(DiscrepanciaDato.objects.exists())

    def test_procesamiento_es_idempotente_y_no_duplica_verdad_derivada(self):
        response = self.post(self.payload(
            periodo_inicio="2026-09-03T12:00:00",
            valor_numerico="180",
            evidencia_archivo=SimpleUploadedFile(
                "factura.txt", b"Factura combustible diesel 120 L 03-09-2026", content_type="text/plain"
            ),
            evidencia_tipo="factura_combustible",
        ))
        first = self.process_document(response)
        discrepancy_count = DiscrepanciaDato.objects.count()
        quality_count = Observacion.objects.get().evaluaciones_calidad.count()
        second = self.process_document(response)

        self.assertEqual(first.data["resultado_documental"], second.data["resultado_documental"])
        self.assertEqual(DiscrepanciaDato.objects.count(), discrepancy_count)
        self.assertEqual(Observacion.objects.get().evaluaciones_calidad.count(), quality_count)

    def test_timeout_no_revierte_registro_y_retry_reprocesa_version(self):
        response = self.post(self.payload(
            periodo_inicio="2026-09-03T12:00:00",
            valor_numerico="180",
            evidencia_archivo=SimpleUploadedFile(
                "factura.txt", b"Factura combustible diesel 180 L 03-09-2026", content_type="text/plain"
            ),
            evidencia_tipo="factura_combustible",
        ))
        technical_failure = {
            "execution_status": "failed", "failure_code": "provider_timeout",
            "claims": {}, "claims_trazables": {}, "claims_count": 0, "texto_extraido": "",
        }
        with patch("apps.analytics.services.evidence_processing.extract_environmental_document", return_value=technical_failure):
            failed = self.process_document(response)
        self.assertEqual(failed.data["estado_procesamiento"], "error")
        self.assertEqual(RegistroFlujoAmbiental.objects.count(), 1)
        retried = self.process_document(response)
        self.assertEqual(retried.data["estado_procesamiento"], "procesada")
        self.assertEqual(retried.data["resultado_documental"]["veredicto"], "verificada")

    def test_resultado_durable_conserva_modelo_solicitado_y_real(self):
        response = self.post(self.payload(
            periodo_inicio="2026-09-03T12:00:00",
            valor_numerico="180",
            evidencia_archivo=SimpleUploadedFile(
                "factura.png", b"\x89PNG\r\n\x1a\ncontenido", content_type="image/png"
            ),
            evidencia_tipo="factura_combustible",
        ))
        extraction = {
            "tipo_documento": "factura_combustible",
            "relevancia_detectada": "pertinente",
            "confianza": 0.99,
            "execution_status": "success",
            "extractor_used": "VisualAIExtractor",
            "provider_used": "openrouter",
            "model_used": "google/gemini-2.5-flash",
            "failure_code": "",
            "claims_count": 4,
            "claims": {"cantidad": "180", "unidad": "L", "fecha": "2026-09-03", "tipo_recurso": "diesel"},
            "claims_trazables": {},
            "texto_extraido": "",
            "extraction_metadata": {
                "requested_model": "openrouter/free",
                "actual_model": "google/gemini-2.5-flash",
                "response_id": "gen-test",
                "finish_reason": "stop",
                "choices_count": 1,
                "content_type": "str",
            },
        }
        with patch("apps.analytics.services.evidence_processing.extract_environmental_document", return_value=extraction):
            processed = self.process_document(response)
        self.assertEqual(processed.status_code, 200)
        persisted = VersionEvidencia.objects.get().metadata_tecnica["document_result"]["extraccion"]["metadata"]
        self.assertEqual(persisted["requested_model"], "openrouter/free")
        self.assertEqual(persisted["actual_model"], "google/gemini-2.5-flash")

    def test_fallo_al_crear_registro_revierte_actividad_y_evidencia(self):
        counts_before = (
            EvidenciaObra.objects.count(),
            ActividadOperacional.objects.count(),
            RegistroFlujoAmbiental.objects.count(),
        )
        self.client.raise_request_exception = False
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            with patch(
                "apps.analytics.views_sector_flows_v1.RegistroFlujoAmbientalSerializer.save",
                side_effect=RuntimeError("controlled failure"),
            ):
                response = self.post(self.payload(
                    evidencia_archivo=SimpleUploadedFile("rollback.txt", b"rollback", content_type="text/plain"),
                ))

            self.assertFalse(any(item.is_file() for item in Path(media_root).rglob("*")))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(counts_before, (
            EvidenciaObra.objects.count(),
            ActividadOperacional.objects.count(),
            RegistroFlujoAmbiental.objects.count(),
        ))

    def test_error_de_validacion_no_deja_elementos_parciales(self):
        payload = self.payload()
        payload.pop("fuente")
        response = self.post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(EvidenciaObra.objects.exists())
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_cross_tenant_no_crea_elementos(self):
        other = Organizacion.objects.create(nombre="Otro tenant")
        response = self.post(self.payload(), organization_id=other.organizacion_id)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_usuario_sin_permiso_no_crea_elementos(self):
        self.membership.rol = UsuarioOrganizacion.Rol.LECTOR
        self.membership.save(update_fields=["rol"])
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())

    def test_combustible_persiste_tipo_cantidad_y_destino(self):
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 201, response.data)
        record = RegistroFlujoAmbiental.objects.get()
        observation = record.actividad.observaciones.get()
        self.assertEqual(record.tipo_recurso, "diesel")
        self.assertEqual(record.destino_operacional, "generador")
        self.assertEqual(str(observation.valor_numerico), "20.000000")
        self.assertEqual(observation.unidad, "L")

    def test_respaldo_es_opcional(self):
        response = self.post(self.payload(codigo_actividad="manual-combustibles-sin-respaldo"))

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(Observacion.objects.get().evidencia_id)

    def test_fecha_anterior_al_inicio_de_obra_es_rechazada(self):
        response = self.post(self.payload(
            codigo_actividad="manual-combustibles-fecha-invalida",
            periodo_inicio="2026-08-24T12:00:00",
        ))

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("inicio de la obra", str(response.data).lower())
        self.assertFalse(ActividadOperacional.objects.exists())
        self.assertFalse(RegistroFlujoAmbiental.objects.exists())
