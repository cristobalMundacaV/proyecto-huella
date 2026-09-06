from datetime import date
from threading import Barrier, Thread
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.knowledge.test_legal_governance import LegalGovernanceTests
from apps.knowledge.legal_governance import activate_legal_obligation_version,promote_legal_candidate,validate_legal_obligation_version
from apps.knowledge.models import LegalObligationVersion
from .models import LegalObligationApplicabilityAssessment,Obra,Organizacion,UsuarioObraAcceso,UsuarioOrganizacion
from .services.legal_applicability import build_legal_applicability_context,evaluate_active_legal_obligations_for_organization,evaluate_active_legal_obligations_for_work,get_legal_assessment_freshness


class PersistedLegalApplicabilityTests(LegalGovernanceTests):
    def setUp(self):
        super().setUp();self.organization=Organizacion.objects.create(nombre="Constructora Demo",pais="Chile",preset="construccion",rubro="Construcción",region="Biobío",comuna="Los Ángeles")
        self.work=Obra.objects.create(organizacion=self.organization,nombre="Obra Demo",tipo_proyecto="Edificio habitacional",perfil_ambiental="edificacion",fecha_inicio=date(2026,1,1),region="Biobío",comuna="Los Ángeles",estado="en_ejecucion")
    def active(self,candidate=None,level="organization",mode="unconditional",criteria=None,target=None):
        obligation,version,_=promote_legal_candidate(candidate or self.candidates[0],self.superuser,"new_version" if target else "create_obligation",target,criteria or [],modality="obligation",canonical_statement="Declaración gobernada.",applicability_level=level,applicability_mode=mode)
        validate_legal_obligation_version(version,self.superuser);activate_legal_obligation_version(version,self.superuser);version.refresh_from_db();return obligation,version
    def assessment_payload(self, obligation, version, work=None):
        return {
            "organization": self.organization,
            "work": work,
            "obligation": obligation,
            "obligation_version": version,
            "scope_level": version.applicability_level,
            "evaluator_version": "legal-applicability-1",
            "revision": 1,
            "result": "applicable",
            "context_snapshot": {"organization": {}, "work": None},
            "criteria_snapshot": [],
            "legal_snapshot": {"obligation_version_id": version.id},
            "evaluation_details": {"result": "applicable"},
            "context_hash": "a" * 64,
            "input_hash": "b" * 64,
            "evaluated_by": self.superuser,
            "evaluated_at": timezone.now(),
        }
    def test_only_active_version_can_create_and_bulk_create_is_blocked(self):
        obligation, version = self.active()
        payload = self.assessment_payload(obligation, version)
        LegalObligationApplicabilityAssessment(**payload).full_clean()
        for state in ("draft", "validated", "obsolete"):
            LegalObligationVersion.objects.filter(pk=version.pk).update(state=state)
            version.refresh_from_db()
            invalid_payload = {**payload, "obligation_version": version}
            with self.assertRaises(ValidationError):
                LegalObligationApplicabilityAssessment(**invalid_payload).full_clean()
        LegalObligationVersion.objects.filter(pk=version.pk).update(state="active")
        version.refresh_from_db()
        active_payload = {**payload, "obligation_version": version}
        with self.assertRaises(ValidationError):
            LegalObligationApplicabilityAssessment.objects.bulk_create(
                [LegalObligationApplicabilityAssessment(**active_payload)]
            )
    def test_server_context_scope_and_organization_idempotency_history(self):
        _,version=self.active();context=build_legal_applicability_context(self.organization)
        self.assertEqual((context["organization"]["country"],context["work"]),("Chile",None))
        first=evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);second=evaluate_active_legal_obligations_for_organization(self.organization,self.superuser)
        self.assertEqual((first.created,first.applicable,second.unchanged),(1,1,1));assessment=LegalObligationApplicabilityAssessment.objects.get();self.assertEqual(assessment.revision,1)
        self.organization.region="Maule";self.organization.save(update_fields=["region"]);self.assertEqual(get_legal_assessment_freshness(assessment,self.organization),"stale_context")
        third=evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);self.assertEqual((third.created,third.superseded),(1,1));self.assertEqual(list(LegalObligationApplicabilityAssessment.objects.order_by("revision").values_list("revision","is_latest")),[(1,False),(2,True)])
    def test_work_conditional_results_and_missing(self):
        _,version=self.active(level="work",mode="conditional",criteria=[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}])
        result=evaluate_active_legal_obligations_for_work(self.organization,self.work,self.superuser);self.assertEqual((result.created,result.applicable),(1,1))
        self.work.estado="finalizada";self.work.save(update_fields=["estado"]);result=evaluate_active_legal_obligations_for_work(self.organization,self.work,self.superuser);self.assertEqual(result.not_applicable,1)
        self.work.estado="";self.work.save(update_fields=["estado"]);result=evaluate_active_legal_obligations_for_work(self.organization,self.work,self.superuser);self.assertEqual(result.undetermined,1)
    def test_descriptive_renames_are_semantically_idempotent(self):
        self.active(level="work", mode="unconditional")
        evaluate_active_legal_obligations_for_work(
            self.organization, self.work, self.superuser
        )
        assessment = LegalObligationApplicabilityAssessment.objects.get()
        original_snapshot = assessment.context_snapshot
        self.organization.nombre = "Nombre organizacional nuevo"
        self.organization.save(update_fields=["nombre"])
        self.work.nombre = "Edificio Parque Norte"
        self.work.codigo_obra = "CODIGO-NUEVO"
        self.work.save(update_fields=["nombre", "codigo_obra"])
        self.assertEqual(
            get_legal_assessment_freshness(assessment, self.organization, self.work),
            "fresh",
        )
        result = evaluate_active_legal_obligations_for_work(
            self.organization, self.work, self.superuser
        )
        self.assertEqual((result.unchanged, result.created), (1, 0))
        assessment.refresh_from_db()
        self.assertEqual(assessment.context_snapshot, original_snapshot)
        self.work.region = "Maule"
        self.work.save(update_fields=["region"])
        self.assertEqual(
            get_legal_assessment_freshness(assessment, self.organization, self.work),
            "stale_context",
        )
    def test_ephemeral_three_obligation_smoke_and_history(self):
        parse = self.candidates[0].extraction_run.article.parse
        third = self._candidate(parse, "3", "El titular deberá registrar.")
        self.active(self.candidates[0])
        self.active(
            self.candidates[1],
            level="work",
            mode="conditional",
            criteria=[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}],
        )
        self.active(
            third,
            level="work",
            mode="conditional",
            criteria=[{"dimension":"work_state","operator":"equals","values":["pausada"]}],
        )
        first = evaluate_active_legal_obligations_for_work(
            self.organization, self.work, self.superuser
        )
        self.assertEqual(
            (first.active_obligations, first.created, first.applicable, first.not_applicable),
            (3, 3, 2, 1),
        )
        self.work.estado = "finalizada"
        self.work.save(update_fields=["estado"])
        stale = LegalObligationApplicabilityAssessment.objects.filter(
            work=self.work, is_latest=True
        )
        self.assertTrue(
            all(
                get_legal_assessment_freshness(item, self.organization, self.work)
                == "stale_context"
                for item in stale
            )
        )
        second = evaluate_active_legal_obligations_for_work(
            self.organization, self.work, self.superuser
        )
        self.assertEqual((second.created, second.superseded), (2, 2))
        self.assertEqual(LegalObligationApplicabilityAssessment.objects.count(), 5)
    def test_only_active_and_legal_evaluator_contract_freshness(self):
        obligation,v1=self.active();evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);assessment=LegalObligationApplicabilityAssessment.objects.get(is_latest=True)
        with patch("apps.analytics.services.legal_applicability.LEGAL_APPLICABILITY_EVALUATOR_VERSION","legal-applicability-2"):
            self.assertEqual(get_legal_assessment_freshness(assessment,self.organization),"stale_evaluator");self.assertEqual(evaluate_active_legal_obligations_for_organization(self.organization,self.superuser).created,1)
        _,v2=self.active(self.candidates[1],target=obligation);latest=LegalObligationApplicabilityAssessment.objects.get(is_latest=True);self.assertEqual(get_legal_assessment_freshness(latest,self.organization),"stale_legal_version")
        self.assertTrue(LegalObligationApplicabilityAssessment.objects.filter(obligation_version=v1).exists())
        evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);latest=LegalObligationApplicabilityAssessment.objects.get(is_latest=True);LegalObligationVersion.objects.filter(pk=v2.pk).update(canonical_statement="Contrato simulado distinto")
        self.assertEqual(get_legal_assessment_freshness(latest,self.organization),"stale_legal_contract")
        self.assertEqual(evaluate_active_legal_obligations_for_organization(self.organization,self.superuser).active_obligations,1)
    def test_assessment_immutable_and_scope_fail_closed(self):
        obligation,version=self.active();evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);assessment=LegalObligationApplicabilityAssessment.objects.get();assessment.result="undetermined"
        with self.assertRaises(ValidationError):assessment.save()
        with self.assertRaises(ValidationError):assessment.delete()
        with self.assertRaises(ValidationError):LegalObligationApplicabilityAssessment.objects.all().delete()
    def test_rbac_scope_and_client_context_ignored(self):
        self.active();lector=self.user;UsuarioOrganizacion.objects.create(user=lector,organizacion=self.organization,rol="lector",alcance="organizacion")
        manager=type(self.user).objects.create_user("manager",password="x");UsuarioOrganizacion.objects.create(user=manager,organizacion=self.organization,rol="responsable_ambiental",alcance="obras");UsuarioObraAcceso.objects.create(usuario_organizacion=manager.organizaciones_perfil.get(),obra=self.work)
        client=APIClient();base=f"/api/organizaciones/{self.organization.organizacion_id}"
        self.assertIn(client.get(base+"/aplicabilidad-legal/").status_code,(401,403));client.force_authenticate(lector);self.assertEqual(client.get(base+"/aplicabilidad-legal/").status_code,200);self.assertEqual(client.post(base+"/aplicabilidad-legal/evaluar/",{},format="json").status_code,403)
        client.force_authenticate(manager);response=client.post(base+f"/obras/{self.work.id}/aplicabilidad-legal/evaluar/",{"work_state":"finalizada","region":"Maule"},format="json");self.assertEqual(response.status_code,200);assessment=LegalObligationApplicabilityAssessment.objects.get();self.assertEqual(assessment.context_snapshot["work"],None)
        outside=Obra.objects.create(organizacion=self.organization,nombre="Fuera",tipo_proyecto="Otro",perfil_ambiental="otro",fecha_inicio=date(2026,1,1));self.assertEqual(client.get(base+f"/obras/{outside.id}/aplicabilidad-legal/").status_code,404)


class LegalApplicabilityConcurrencyTests(TransactionTestCase):
    """PostgreSQL regression for target locking plus partial unique constraints."""

    _candidate = LegalGovernanceTests._candidate

    def _fixture_teardown(self):
        # The legacy schema contains a cross-app FK that Django's PostgreSQL
        # sql_flush misses. The test database can still be isolated safely by
        # truncating its complete table set with CASCADE.
        if connection.vendor != "postgresql":
            return super()._fixture_teardown()
        tables = connection.introspection.table_names()
        if tables:
            quoted = ", ".join(connection.ops.quote_name(table) for table in tables)
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")

    def setUp(self):
        LegalGovernanceTests.setUp(self)
        self.organization = Organizacion.objects.create(nombre="Concurrente")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Obra concurrente",
            fecha_inicio=date(2026, 1, 1),
        )
        obligation, version, _ = promote_legal_candidate(
            self.candidates[0],
            self.superuser,
            "create_obligation",
            None,
            [{"dimension": "work_state", "operator": "equals", "values": ["en_ejecucion"]}],
            modality="obligation",
            canonical_statement="Declaracion concurrente.",
            applicability_level="work",
            applicability_mode="conditional",
        )
        validate_legal_obligation_version(version, self.superuser)
        activate_legal_obligation_version(version, self.superuser)
        self.obligation_id = obligation.id

    def test_concurrent_work_evaluation_produces_one_revision(self):
        if connection.vendor != "postgresql":
            self.skipTest("Locking concurrency is verified on PostgreSQL.")

        barrier = Barrier(2)
        errors = []

        def evaluate():
            close_old_connections()
            try:
                barrier.wait()
                evaluate_active_legal_obligations_for_work(
                    Organizacion.objects.get(pk=self.organization.pk),
                    Obra.objects.get(pk=self.work.pk),
                    type(self.superuser).objects.get(pk=self.superuser.pk),
                )
            except Exception as exc:  # surfaced in the parent test thread
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=evaluate), Thread(target=evaluate)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        assessments = LegalObligationApplicabilityAssessment.objects.filter(
            work=self.work, obligation_id=self.obligation_id
        )
        self.assertEqual(assessments.count(), 1)
        self.assertEqual(
            list(assessments.values_list("revision", "is_latest")), [(1, True)]
        )
