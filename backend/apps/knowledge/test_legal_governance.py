import hashlib
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .legal_governance import activate_legal_obligation_version, evaluate_legal_obligation_applicability, promote_legal_candidate, reject_legal_candidate, update_legal_obligation_draft, validate_criterion, validate_legal_obligation_version
from .models import BcnLegalArticleFact, BcnLegalNormFact, BcnLegalNormVersionFact, BcnLegalObligationCandidate, BcnLegalObligationCandidateReview, BcnLegalObligationExtractionRun, BcnLegalTextParse, BcnLegalTextSourceDocument, EnvironmentalSource, ExternalFileArtifact, ExternalRecord, ExternalSnapshot, LegalObligationApplicabilityCriterion, LegalObligationVersion, SyncRun


class LegalApplicabilityEvaluatorTests(SimpleTestCase):
    def version(self,mode="conditional",level="work",criteria=None):return SimpleNamespace(applicability_mode=mode,applicability_level=level,criteria=criteria or [])
    def criterion(self,dimension,operator,values):return SimpleNamespace(dimension=dimension,operator=operator,values=values)
    def test_applicable_not_applicable_and_missing(self):
        version=self.version(criteria=[self.criterion("work_state","equals",["en_ejecucion"]),self.criterion("work_region","in",["Biobío","Ñuble"])])
        base={"organization":{"country":"Chile"},"work":{"state":"en_ejecucion","region":"Biobío"}}
        self.assertEqual(evaluate_legal_obligation_applicability(version,base)["result"],"applicable")
        self.assertEqual(evaluate_legal_obligation_applicability(version,{**base,"work":{**base["work"],"region":"Maule"}})["result"],"not_applicable")
        self.assertEqual(evaluate_legal_obligation_applicability(version,{"organization":{},"work":{"state":"en_ejecucion"}})["result"],"undetermined")
    def test_pending_unconditional_and_work_without_context(self):
        self.assertEqual(evaluate_legal_obligation_applicability(self.version("pending"),{})["result"],"undetermined")
        self.assertEqual(evaluate_legal_obligation_applicability(self.version("unconditional"),{"organization":{},"work":{"state":"x"}})["result"],"applicable")
        self.assertEqual(evaluate_legal_obligation_applicability(self.version("unconditional"),{"organization":{}})["result"],"undetermined")
    def test_controlled_values_and_operators(self):
        validate_criterion({"dimension":"work_state","operator":"equals","values":["en_ejecucion"]})
        validate_criterion({"dimension":"organization_region","operator":"in","values":["Biobío","Ñuble"]})
        for invalid in ({"dimension":"work_state","operator":"equals","values":["inventado"]},{"dimension":"work_state","operator":"regex","values":["x"]},{"dimension":"unknown","operator":"equals","values":["x"]}):
            with self.assertRaises(ValidationError):validate_criterion(invalid)


class LegalGovernanceTests(TestCase):
    def setUp(self):
        self.superuser=get_user_model().objects.create_superuser("legal-admin","admin@example.com","x");self.user=get_user_model().objects.create_user("reader",password="x")
        source=EnvironmentalSource.objects.get(codigo="bcn-leychile");source.legal_norm_subscriptions.exclude(number="19300").update(active=False);now=timezone.now()
        sync=SyncRun.objects.create(source=source,trigger="manual",started_at=now);snapshot=ExternalSnapshot.objects.create(source=source,sync_run=sync,external_id="norm:19300",record_kind="bcn_legal_norm",retrieved_at=now,content_hash="a"*64)
        record=ExternalRecord.objects.create(source=source,external_id="norm:19300",kind="bcn_legal_norm",canonical_key="LEY:19300",current_snapshot=snapshot,first_seen_at=now,last_seen_at=now)
        fact=BcnLegalNormFact.objects.create(snapshot=snapshot,norm_uri="https://datos.bcn.cl/norm/19300",number="19300",title="Ley ambiental",norm_type_uri="https://datos.bcn.cl/type/ley",norm_type_name="Ley",latest_version_uri="https://datos.bcn.cl/version/latest")
        BcnLegalNormVersionFact.objects.create(norm_fact=fact,version_uri=fact.latest_version_uri,is_latest=True)
        artifact=ExternalFileArtifact.objects.create(source=source,parent_record=record,external_resource_id="legal:test",name="XML",source_url="https://www.leychile.cl/x.xml",format="XML",byte_size=1,retrieved_at=now,content_sha256="b"*64,metadata={"version_uri":fact.latest_version_uri,"norm_number":"19300"},is_current=True,version=1)
        document=BcnLegalTextSourceDocument.objects.create(artifact=artifact,raw_bytes=b"x",detected_encoding="UTF-8",byte_size=1);parse=BcnLegalTextParse.objects.create(source_document=document,parser_version="1",status="success",parsed_at=now,article_count=2)
        self.candidates=[self._candidate(parse,"1","El titular deberá informar."),self._candidate(parse,"2","Se prohíbe descargar.")]
    def _candidate(self,parse,number,text):
        article=BcnLegalArticleFact.objects.create(parse=parse,article_key=f"a:{number}",article_number=number,order_index=int(number),source_path=f"/{number}",text_plain=text,text_hash=hashlib.sha256(text.encode()).hexdigest(),raw_fragment="x")
        run=BcnLegalObligationExtractionRun.objects.create(article=article,extractor_version="rules-1",extractor_method="deterministic_rules",status="success",executed_at=timezone.now(),source_text_hash=article.text_hash,candidate_count=1)
        trigger="deberá" if "deberá" in text else "Se prohíbe";start=text.index(trigger);return BcnLegalObligationCandidate.objects.create(extraction_run=run,candidate_key=hashlib.sha256(text.encode()).hexdigest(),order_index=1,modality_hint="obligation" if "deberá" in text else "prohibition",trigger_text=trigger,trigger_start=start,trigger_end=start+len(trigger),source_quote=text,source_start=0,source_end=len(text),source_quote_hash=hashlib.sha256(text.encode()).hexdigest())
    def promote(self,candidate=None,mode="conditional",criteria=None,target=None):
        return promote_legal_candidate(candidate or self.candidates[0],self.superuser,"new_version" if target else "create_obligation",target,criteria or [],modality="obligation",canonical_statement="El titular debe informar.",applicability_level="work",applicability_mode=mode)
    def test_permissions_reject_and_historical_candidate(self):
        with self.assertRaises(ValidationError):reject_legal_candidate(self.candidates[0],self.user,"no")
        review=reject_legal_candidate(self.candidates[0],self.superuser,"No corresponde")
        self.assertEqual((review.decision,review.promoted_obligation_id),("rejected",None))
        self.candidates[1].extraction_run.article.parse.source_document.artifact.is_current=False;self.candidates[1].extraction_run.article.parse.source_document.artifact.save(update_fields=["is_current"])
        with self.assertRaises(ValidationError):reject_legal_candidate(self.candidates[1],self.superuser)
    def test_promote_draft_provenance_edit_validate_activate_and_version_switch(self):
        obligation,v1,review=self.promote(criteria=[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}])
        self.assertEqual((v1.version,v1.state,review.decision),(1,"draft","approved"));self.assertEqual(v1.source_provenance["source_quote"],self.candidates[0].source_quote)
        with self.assertRaises(ValidationError):self.promote(self.candidates[0])
        update_legal_obligation_draft(v1,self.superuser,canonical_statement="Declaración revisada")
        validate_legal_obligation_version(v1,self.superuser);activate_legal_obligation_version(v1,self.superuser);v1.refresh_from_db();self.assertEqual(v1.state,"active")
        with self.assertRaises(ValidationError):update_legal_obligation_draft(v1,self.superuser,canonical_statement="No")
        obligation,v2,_=self.promote(self.candidates[1],criteria=[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}],target=obligation)
        validate_legal_obligation_version(v2,self.superuser);activate_legal_obligation_version(v2,self.superuser);v1.refresh_from_db();v2.refresh_from_db();self.assertEqual((v1.state,v2.state),("obsolete","active"))
        self.assertEqual(LegalObligationVersion.objects.filter(obligation=obligation,state="active").count(),1)
    def test_modes_and_validation_contracts(self):
        _,pending,_=self.promote(mode="pending")
        with self.assertRaises(ValidationError):validate_legal_obligation_version(pending,self.superuser)
        _,unconditional,_=self.promote(self.candidates[1],mode="unconditional")
        validate_legal_obligation_version(unconditional,self.superuser)
    def test_api_permissions_provenance_and_reads(self):
        client=APIClient();client.force_authenticate(self.user)
        body={"mode":"create_obligation","canonical_statement":"Declaración","modality":"obligation","applicability_level":"work","applicability_mode":"unconditional","source_provenance":{"fake":True}}
        self.assertEqual(client.post(f"/api/knowledge/bcn/obligation-candidates/{self.candidates[0].id}/promote/",body,format="json").status_code,403)
        client.force_authenticate(self.superuser);self.assertEqual(client.post(f"/api/knowledge/bcn/obligation-candidates/{self.candidates[0].id}/promote/",body,format="json").status_code,400)
        body.pop("source_provenance");created=client.post(f"/api/knowledge/bcn/obligation-candidates/{self.candidates[0].id}/promote/",body,format="json");self.assertEqual(created.status_code,201)
        version=LegalObligationVersion.objects.get();validate_legal_obligation_version(version,self.superuser);activate_legal_obligation_version(version,self.superuser)
        client.force_authenticate(self.user);response=client.get("/api/knowledge/legal-obligations/?modality=obligation&applicability_level=work&norm_number=19300");self.assertEqual((response.status_code,response.data["count"]),(200,1));self.assertNotIn("source_provenance",response.data["results"][0])
        client.force_authenticate(None);self.assertIn(client.get("/api/knowledge/legal-obligations/").status_code,(401,403))
    def test_semantic_enums_fail_closed_in_services_and_api(self):
        for field,value in (("modality","inventada"),("applicability_level","inventado"),("applicability_mode","inventado")):
            kwargs={"modality":"obligation","canonical_statement":"Declaracion","applicability_level":"work","applicability_mode":"pending"};kwargs[field]=value
            with self.assertRaises(ValidationError):promote_legal_candidate(self.candidates[0],self.superuser,"create_obligation",None,[],**kwargs)
        client=APIClient();client.force_authenticate(self.superuser)
        response=client.post(f"/api/knowledge/bcn/obligation-candidates/{self.candidates[0].id}/promote/",{"mode":"create_obligation","modality":"obligation","canonical_statement":"Declaracion","applicability_level":"work","applicability_mode":"inventado"},format="json")
        self.assertEqual(response.status_code,400)
    def test_direct_lifecycle_mutation_is_blocked(self):
        _,version,_=self.promote(mode="unconditional")
        for field,value in (("state","active"),("state","obsolete"),("activated_by",self.superuser)):
            version.refresh_from_db();setattr(version,field,value)
            with self.assertRaises(ValidationError):version.save()
        validate_legal_obligation_version(version,self.superuser)
        version.state="draft"
        with self.assertRaises(ValidationError):version.save()
    def test_governed_criteria_are_immutable_and_level_consistent(self):
        with self.assertRaises(ValidationError):
            promote_legal_candidate(self.candidates[0],self.superuser,"create_obligation",None,[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}],modality="obligation",canonical_statement="Declaracion",applicability_level="organization",applicability_mode="conditional")
        _,version,_=self.promote(criteria=[{"dimension":"work_state","operator":"equals","values":["en_ejecucion"]}]);criterion=version.criteria.get()
        criterion.values=["pausada"];criterion.save();validate_legal_obligation_version(version,self.superuser);activate_legal_obligation_version(version,self.superuser)
        criterion.refresh_from_db();criterion.values=["finalizada"]
        with self.assertRaises(ValidationError):criterion.save()
        with self.assertRaises(ValidationError):criterion.delete()
        with self.assertRaises(ValidationError):LegalObligationApplicabilityCriterion.objects.filter(pk=criterion.pk).delete()
    def test_approved_review_requires_matching_version_candidate_and_obligation(self):
        obligation,version,_=self.promote()
        with self.assertRaises(ValidationError):
            BcnLegalObligationCandidateReview.objects.create(candidate=self.candidates[1],decision="approved",reviewer=self.superuser,reviewed_at=timezone.now(),promoted_obligation=obligation,promoted_version=version)
    def test_full_frozen_provenance_is_validated(self):
        _,version,_=self.promote(mode="unconditional")
        for key in ("candidate_id","candidate_key","extractor_version","modality_hint","artifact_id","artifact_sha256","version_uri","parser_version","article_id","article_key","article_number","article_text_hash","source_quote","source_start","source_end","trigger_text","trigger_start","trigger_end"):
            original=version.source_provenance;corrupt=dict(original);corrupt[key]="corrupt";LegalObligationVersion.objects.filter(pk=version.pk).update(source_provenance=corrupt);version.refresh_from_db()
            with self.assertRaises(ValidationError):validate_legal_obligation_version(version,self.superuser)
            LegalObligationVersion.objects.filter(pk=version.pk).update(source_provenance=original);version.refresh_from_db()
