from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import (
    DocumentoAmbiental, FuenteDatos, Obra, Organizacion, ProblematicaAmbiental,
    ProcesoIngesta, UsuarioObraAcceso, UsuarioOrganizacion,
)


class CriticalWorkScopeTests(APITestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Scope tenant")
        self.other = Organizacion.objects.create(nombre="Otro tenant")
        self.work_a = Obra.objects.create(organizacion=self.org, nombre="Obra A", fecha_inicio=date.today())
        self.work_b = Obra.objects.create(organizacion=self.org, nombre="Obra B", fecha_inicio=date.today())
        self.foreign_work = Obra.objects.create(organizacion=self.other, nombre="Obra ajena", fecha_inicio=date.today())
        self.document_a = DocumentoAmbiental.objects.create(organizacion=self.org, obra=self.work_a, nombre="Documento A", tipo_documento="permiso", fecha_documento=date.today())
        self.document_b = DocumentoAmbiental.objects.create(organizacion=self.org, obra=self.work_b, nombre="Documento B", tipo_documento="permiso", fecha_documento=date.today())
        self.foreign_document = DocumentoAmbiental.objects.create(organizacion=self.other, obra=self.foreign_work, nombre="Documento ajeno", tipo_documento="permiso", fecha_documento=date.today())
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Fuente controlada", tipo="manual")

    def scoped_user(self, username, role):
        user = User.objects.create_user(username, password="safe-password")
        membership = UsuarioOrganizacion.objects.create(
            user=user, organizacion=self.org, rol=role,
            alcance=UsuarioOrganizacion.Alcance.OBRAS,
        )
        UsuarioObraAcceso.objects.create(usuario_organizacion=membership, obra=self.work_a)
        return user

    def test_evidence_scope_and_role_actions(self):
        operator = self.scoped_user("operator-scope", UsuarioOrganizacion.Rol.OPERADOR)
        self.client.force_login(operator)
        self.assertEqual(self.client.get(f"{self.base}/documentos-ambientales/{self.document_a.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"{self.base}/documentos-ambientales/{self.document_b.id}/").status_code, 404)
        created = self.client.post(f"{self.base}/documentos-ambientales/?obra={self.work_a.id}", {
            "nombre": "Respaldo operacional", "tipo_documento": "permiso", "fecha_documento": str(date.today()),
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.patch(f"{self.base}/documentos-ambientales/{self.document_a.id}/", {"estado_validacion": "valido"}, format="json").status_code, 403)

        reviewer = self.scoped_user("reviewer-scope", UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL)
        self.client.force_login(reviewer)
        self.assertEqual(self.client.patch(f"{self.base}/documentos-ambientales/{self.document_a.id}/", {"estado_validacion": "valido"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(f"{self.base}/documentos-ambientales/{self.document_b.id}/", {"estado_validacion": "valido"}, format="json").status_code, 404)
        self.assertEqual(self.client.get(f"/api/organizaciones/{self.other.organizacion_id}/documentos-ambientales/{self.foreign_document.id}/").status_code, 404)

    def test_import_scope_revalidated_on_create_and_detail(self):
        analyst = self.scoped_user("analyst-scope", UsuarioOrganizacion.Rol.ANALISTA)
        self.client.force_login(analyst)
        upload = SimpleUploadedFile("datos.csv", b"viaje_id,km\nV-1,10\n", content_type="text/csv")
        response = self.client.post(f"{self.base}/ingestas/", {
            "archivo": upload, "fuente_nombre": "Planilla", "contexto": f'{{"obra_id": {self.work_b.id}}}',
        }, format="multipart")
        self.assertEqual(response.status_code, 404)
        process = ProcesoIngesta.objects.create(organizacion=self.org, fuente_datos=self.source, tipo_ingesta="manual_estructurado", contexto_confirmado={"obra_id": self.work_b.id})
        self.assertEqual(self.client.get(f"{self.base}/ingestas/{process.id}/").status_code, 404)

    def test_problem_scope_for_read_create_and_actions(self):
        analyst = self.scoped_user("problem-scope", UsuarioOrganizacion.Rol.ANALISTA)
        problem_a = ProblematicaAmbiental.objects.create(organizacion=self.org, obra=self.work_a, titulo="Problema A", descripcion="Detalle", categoria="Agua", indicador="agua", valor_inicial=20, objetivo_meta=10, fecha_deteccion=date.today(), nivel_riesgo="medio")
        problem_b = ProblematicaAmbiental.objects.create(organizacion=self.org, obra=self.work_b, titulo="Problema B", descripcion="Detalle", categoria="Agua", indicador="agua", valor_inicial=20, objetivo_meta=10, fecha_deteccion=date.today(), nivel_riesgo="medio")
        self.client.force_login(analyst)
        self.assertEqual(self.client.get(f"{self.base}/problematicas/{problem_a.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"{self.base}/problematicas/{problem_b.id}/").status_code, 404)
        payload = {"obra": self.work_b.id, "titulo": "No autorizada", "descripcion": "Detalle", "categoria": "Agua", "indicador": "agua", "valor_inicial": "20", "objetivo_meta": "10", "fecha_deteccion": str(date.today()), "nivel_riesgo": "medio"}
        self.assertEqual(self.client.post(f"{self.base}/problematicas/", payload, format="json").status_code, 404)
        self.assertEqual(self.client.post(f"{self.base}/problematicas/{problem_b.id}/acciones/", {"titulo": "Acción", "descripcion": "Detalle"}, format="json").status_code, 404)
