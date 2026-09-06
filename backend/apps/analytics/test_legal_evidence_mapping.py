from datetime import date
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from threading import Barrier, Thread
from apps.knowledge.bootstrap import ensure_environmental_source_registry
from apps.knowledge.test_legal_governance import LegalGovernanceTests

from apps.knowledge.legal_evidence import activate_legal_evidence_requirement_version,create_legal_evidence_requirement,validate_legal_evidence_requirement_version
from apps.knowledge.test_legal_evidence import LegalEvidenceRequirementTests,VALID_FIELDS
from .models import EvidenciaObra,LegalEvidenceOperationalLink,LegalEvidenceOperationalMappingRevision,Obra,Organizacion,VersionEvidencia
from .services.legal_applicability import evaluate_active_legal_obligations_for_organization
from .services.legal_evidence_mapping import create_operational_evidence_link,get_legal_evidence_link_freshness,get_legal_evidence_mapping_freshness,list_operational_evidence_candidates,publish_legal_evidence_operational_mapping,withdraw_legal_evidence_link


class LegalEvidenceMappingTests(LegalEvidenceRequirementTests):
    def setUp(self):
        super().setUp();self.organization=Organizacion.objects.create(nombre="Tenant evidencia")

    def governed(self):
        obligation,legal=self.active_obligation();requirement,version=create_legal_evidence_requirement(obligation,legal,self.superuser,**VALID_FIELDS);validate_legal_evidence_requirement_version(version,self.superuser);activate_legal_evidence_requirement_version(version,self.superuser);version.refresh_from_db();evaluate_active_legal_obligations_for_organization(self.organization,self.superuser);return requirement,version

    def evidence(self,kind="informe_medicion_ruido",versioned=True):
        evidence=EvidenciaObra.objects.create(organizacion=self.organization,tipo_evidencia=kind,nombre="Informe",archivo=SimpleUploadedFile("a.pdf",b"a"))
        version=None
        if versioned:version=VersionEvidencia.objects.create(evidencia=evidence,organizacion=self.organization,version=1,archivo=SimpleUploadedFile("v.pdf",b"a"),nombre_original="a.pdf",checksum_sha256="a"*64)
        return evidence,version

    def test_mapping_validation_hash_idempotency_and_history(self):
        _,version=self.governed();items=[{"evidence_class":"measurement","evidence_type":"registro_sonometro","note":""},{"evidence_class":"report","evidence_type":"informe_medicion_ruido","note":"Informe"}]
        first,created=publish_legal_evidence_operational_mapping(version,items,self.superuser);same,created2=publish_legal_evidence_operational_mapping(version,list(reversed(items)),self.superuser)
        self.assertTrue(created);self.assertFalse(created2);self.assertEqual(first.pk,same.pk)
        changed,_=publish_legal_evidence_operational_mapping(version,[items[0],{**items[1],"note":"Otra"}],self.superuser)
        first.refresh_from_db();self.assertEqual((first.is_latest,changed.revision),(False,2));self.assertEqual(get_legal_evidence_mapping_freshness(changed),"fresh")
        for invalid in ([items[1]],[items[0],items[0],items[1]],[items[0],{**items[1],"evidence_type":"inventado"}]):
            with self.assertRaises(ValidationError):publish_legal_evidence_operational_mapping(version,invalid,self.superuser)
        with self.assertRaises(ValidationError):LegalEvidenceOperationalMappingRevision.objects.bulk_create([])

    def test_exact_candidates_link_snapshot_withdraw_relink_and_freshness(self):
        requirement,version=self.governed();mapping,_=publish_legal_evidence_operational_mapping(version,[{"evidence_class":"report","evidence_type":"informe_medicion_ruido","note":""},{"evidence_class":"measurement","evidence_type":"registro_sonometro","note":""}],self.superuser)
        compatible,v1=self.evidence();legacy,_=self.evidence(versioned=False);self.evidence("otro",True)
        candidates=list_operational_evidence_candidates(requirement.code,self.organization)
        self.assertEqual(len(candidates),2);self.assertTrue(candidates[0]["linkable"]);self.assertEqual(candidates[1]["reason"],"unversioned_evidence")
        link,created=create_operational_evidence_link(requirement.code,self.organization,None,compatible,v1,self.superuser)
        duplicate,created2=create_operational_evidence_link(requirement.code,self.organization,None,compatible,v1,self.superuser)
        self.assertTrue(created);self.assertFalse(created2);self.assertEqual(link.pk,duplicate.pk);self.assertEqual(link.evidence_snapshot["checksum_sha256"],"a"*64);self.assertEqual(get_legal_evidence_link_freshness(link),"fresh")
        v2=VersionEvidencia.objects.create(evidencia=compatible,organizacion=self.organization,version=2,archivo=SimpleUploadedFile("v2.pdf",b"b"),nombre_original="b.pdf",checksum_sha256="b"*64)
        self.assertEqual(get_legal_evidence_link_freshness(link),"stale_evidence_version")
        withdraw_legal_evidence_link(link,self.superuser,"Reemplazada");new,_=create_operational_evidence_link(requirement.code,self.organization,None,compatible,v2,self.superuser)
        self.assertEqual(LegalEvidenceOperationalLink.objects.count(),2);self.assertNotEqual(link.pk,new.pk)
        with self.assertRaises(ValidationError):new.delete()


class LegalEvidenceMappingConcurrencyTests(TransactionTestCase):
    _candidate=LegalGovernanceTests._candidate
    active_obligation=LegalEvidenceRequirementTests.active_obligation
    requirement=LegalEvidenceRequirementTests.requirement
    govern=LegalEvidenceRequirementTests.govern
    governed=LegalEvidenceMappingTests.governed
    evidence=LegalEvidenceMappingTests.evidence

    def _fixture_teardown(self):
        if connection.vendor!="postgresql":return super()._fixture_teardown()
        tables=connection.introspection.table_names()
        if tables:
            with connection.cursor() as cursor:cursor.execute("TRUNCATE "+", ".join(connection.ops.quote_name(t) for t in tables)+" RESTART IDENTITY CASCADE")

    def setUp(self):
        ensure_environmental_source_registry();LegalGovernanceTests.setUp(self);self.organization=Organizacion.objects.create(nombre="Concurrente");self.requirement_obj,self.requirement_version=self.governed()

    def test_mapping_and_link_concurrency(self):
        if connection.vendor!="postgresql":self.skipTest("PostgreSQL locking")
        items=[{"evidence_class":"report","evidence_type":"informe_medicion_ruido","note":"A"},{"evidence_class":"measurement","evidence_type":"registro_sonometro","note":""}]
        barrier=Barrier(2);errors=[]
        def publish(note):
            close_old_connections()
            try:barrier.wait();publish_legal_evidence_operational_mapping(type(self.requirement_version).objects.get(pk=self.requirement_version.pk),[{**x,"note":note if x["evidence_class"]=="report" else ""} for x in items],type(self.superuser).objects.get(pk=self.superuser.pk))
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        threads=[Thread(target=publish,args=(x,)) for x in ("A","B")]
        for t in threads:t.start()
        for t in threads:t.join(20)
        self.assertEqual(errors,[]);self.assertEqual(LegalEvidenceOperationalMappingRevision.objects.filter(requirement_version=self.requirement_version).count(),2);self.assertEqual(LegalEvidenceOperationalMappingRevision.objects.filter(requirement_version=self.requirement_version,is_latest=True).count(),1)
        evidence,ev=self.evidence();barrier=Barrier(2);results=[];errors=[]
        def link():
            close_old_connections()
            try:barrier.wait();results.append(create_operational_evidence_link(self.requirement_obj.code,Organizacion.objects.get(pk=self.organization.pk),None,EvidenciaObra.objects.get(pk=evidence.pk),VersionEvidencia.objects.get(pk=ev.pk),type(self.superuser).objects.get(pk=self.superuser.pk))[1])
            except Exception as exc:errors.append(exc)
            finally:close_old_connections()
        threads=[Thread(target=link),Thread(target=link)]
        for t in threads:t.start()
        for t in threads:t.join(20)
        self.assertEqual(errors,[]);self.assertEqual(sorted(results),[False,True]);self.assertEqual(LegalEvidenceOperationalLink.objects.filter(status="linked").count(),1)
