from django.http import Http404
from django.db import models
from django.db.models.fields.json import KeyTextTransform
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import BasePermission,IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from . import bcn_text
from .bcn_obligations import BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION,current_bcn_norm_facts
from .bcn_text import get_current_bcn_legal_text
from .legal_governance import EDITABLE,activate_legal_obligation_version,obsolete_legal_obligation_version,promote_legal_candidate,reject_legal_candidate,update_legal_obligation_draft,validate_legal_obligation_version
from .legal_evidence import EDITABLE_EVIDENCE_FIELDS,activate_legal_evidence_requirement_version,create_legal_evidence_requirement,create_legal_evidence_requirement_version,get_legal_evidence_requirement_freshness,obsolete_legal_evidence_requirement_version,update_legal_evidence_requirement_draft,validate_legal_evidence_requirement_version
from .models import BcnLegalArticleFact,BcnLegalNormFact,BcnLegalObligationCandidate,LegalEvidenceRequirement,LegalEvidenceRequirementVersion,LegalObligation,LegalObligationVersion,EnvironmentalSource,ExternalFileArtifact,ExternalRecord,HuellaChileEmissionFactorFact,RetcHazardousWasteFact,SnifaOpenDatasetFact,SnifaRegulatoryReferenceFact,SnifaReferenceSubscription,SeaProjectFact,SeaProjectSubscription,SimbioGeoLayerFact,IdeMmaDatasetFact,IdeMmaDownloadResourceFact,OekobaudatDataStockFact,OekobaudatProcessFact
from .serializers import BcnLegalArticleFactSerializer,BcnLegalNormFactSerializer,BcnLegalObligationCandidateSerializer,LegalEvidenceRequirementVersionSerializer,LegalObligationVersionSerializer,EnvironmentalSourceSerializer,ExternalRecordSerializer,ExternalSnapshotSerializer,HuellaChileEmissionFactorFactSerializer,RetcHazardousWasteFactSerializer,SyncRunSerializer
from .services import source_freshness
class KnowledgePagination(PageNumberPagination):
    page_size=50;page_size_query_param="page_size";max_page_size=200
class IsSuperUser(BasePermission):
    def has_permission(self,request,view):return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
def paginated(request,queryset,serializer):
    paginator=KnowledgePagination();page=paginator.paginate_queryset(queryset,request);return paginator.get_paginated_response(serializer(page,many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources(request): return Response(EnvironmentalSourceSerializer(EnvironmentalSource.objects.filter(activa=True),many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_detail(request,code):
    from .source_health import source_health
    source=get_object_or_404(EnvironmentalSource,codigo=code);data=EnvironmentalSourceSerializer(source).data;data["freshness"]=source_freshness(source);data["health"]=source_health(source);return Response(data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_runs(request,code):return paginated(request,get_object_or_404(EnvironmentalSource,codigo=code).sync_runs.all().order_by("-started_at"),SyncRunSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_records(request,code):return paginated(request,get_object_or_404(EnvironmentalSource,codigo=code).records.select_related("current_snapshot").order_by("external_id"),ExternalRecordSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_detail(request,code,external_id):
    record=get_object_or_404(ExternalRecord,source__codigo=code,external_id=external_id);data=ExternalRecordSerializer(record).data
    paginator=KnowledgePagination();page=paginator.paginate_queryset(record.source.snapshots.filter(external_id=external_id).order_by("retrieved_at"),request);data["snapshots"]={"count":paginator.page.paginator.count,"next":paginator.get_next_link(),"previous":paginator.get_previous_link(),"results":ExternalSnapshotSerializer(page,many=True).data};return Response(data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retc_hazardous_waste(request):
    queryset=RetcHazardousWasteFact.objects.filter(artifact__is_current=True).select_related("artifact").order_by("id")
    for parameter in ("year","region","comuna","contaminantes","razon_social","rubro"):
        value=request.query_params.get(parameter)
        if not value: continue
        lookup=parameter if parameter=="year" else f"{parameter}__iexact"
        queryset=queryset.filter(**{lookup:value})
    return paginated(request,queryset,RetcHazardousWasteFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retc_hazardous_waste_metadata(request):
    artifact=get_object_or_404(ExternalFileArtifact.objects.select_related("source","parent_record"),source__codigo="retc",parent_record__canonical_key="generacion-de-residuos-peligrosos",is_current=True)
    return Response({"source":artifact.source.nombre,"dataset":artifact.parent_record.title,"resource":{"id":artifact.external_resource_id,"name":artifact.name,"url":artifact.source_url,"format":artifact.format},"year":artifact.metadata.get("year") or artifact.retc_hazardous_waste_facts.values_list("year",flat=True).first(),"sha256":artifact.content_sha256,"retrieved_at":artifact.retrieved_at,"upstream_modified_at":artifact.upstream_modified_at,"record_count":artifact.retc_hazardous_waste_facts.count(),"license":{"name":artifact.source.licencia_nombre,"url":artifact.source.licencia_url,"attribution_required":artifact.source.atribucion_requerida},"freshness":source_freshness(artifact.source)})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def huellachile_emission_factors(request):
    queryset=HuellaChileEmissionFactorFact.objects.filter(artifact__is_current=True).select_related("artifact").order_by("id")
    for parameter in ("dataset_year","alcance","categoria","actividad","unidad_actividad","technical_source_1"):
        value=request.query_params.get(parameter)
        if value: queryset=queryset.filter(**{parameter if parameter=="dataset_year" else f"{parameter}__iexact":value})
    return paginated(request,queryset,HuellaChileEmissionFactorFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def huellachile_emission_factors_metadata(request):
    artifacts=ExternalFileArtifact.objects.select_related("source","parent_record").filter(source__codigo="huellachile",parent_record__kind="huellachile_emission_factor_dataset",is_current=True,metadata__edition=request.query_params.get("edition","completa"))
    if request.query_params.get("year"): artifacts=artifacts.filter(metadata__year=request.query_params["year"])
    artifact=artifacts.order_by("-metadata__year","-retrieved_at").first()
    if not artifact: raise Http404
    metadata=artifact.metadata;publication=artifact.parent_record.current_snapshot.raw_payload or {}
    return Response({"publisher":metadata.get("publisher"),"source_page":metadata.get("source_page"),"logical_resource":artifact.external_resource_id,"title":artifact.parent_record.title,"year":metadata.get("year"),"edition":metadata.get("edition"),"filename":publication.get("filename") or metadata.get("filename"),"filename_version":publication.get("filename_version") or metadata.get("filename_version"),"source_url":publication.get("url") or artifact.source_url,"sha256":artifact.content_sha256,"bytes":artifact.byte_size,"retrieved_at":artifact.retrieved_at,"artifact_version":artifact.version,"fact_count":artifact.huellachile_emission_factor_facts.count(),"sheet_count":len(metadata.get("sheets",[])),"references":metadata.get("references",[]),"freshness":source_freshness(artifact.source)})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norms(request):
    queryset=BcnLegalNormFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="bcn-leychile").prefetch_related("versions","relations").order_by("number")
    for parameter,lookup in {"number":"number__iexact","norm_type":"norm_type_name__iexact","issuer":"issuer_name__icontains","title":"title__icontains"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    if request.query_params.get("scope_tag"):queryset=queryset.filter(scope_tags__contains=[request.query_params["scope_tag"]])
    return paginated(request,queryset,BcnLegalNormFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norm_detail(request,pk):
    queryset=BcnLegalNormFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="bcn-leychile").prefetch_related("versions","relations")
    return Response(BcnLegalNormFactSerializer(get_object_or_404(queryset,pk=pk)).data)
def _current_text(fact):
    try:return get_current_bcn_legal_text(fact)
    except Exception:raise Http404
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norm_text(request,pk):
    fact=get_object_or_404(BcnLegalNormFact,pk=pk);artifact,parse=_current_text(fact);return Response({"norm":{"id":fact.id,"number":fact.number,"title":fact.title},"version_uri":fact.latest_version_uri,"version_date":fact.latest_version_date,"source_url":artifact.source_url,"sha256":artifact.content_sha256,"retrieved_at":artifact.retrieved_at,"parser_version":parse.parser_version,"article_count":parse.article_count})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norm_articles(request,pk):
    fact=get_object_or_404(BcnLegalNormFact,pk=pk);artifact,parse=_current_text(fact);queryset=parse.articles.all()
    if request.query_params.get("article_number"):queryset=queryset.filter(article_number__iexact=request.query_params["article_number"])
    if request.query_params.get("article_label"):queryset=queryset.filter(article_label__icontains=request.query_params["article_label"])
    return paginated(request,queryset,BcnLegalArticleFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_article_detail(request,pk):
    article=get_object_or_404(BcnLegalArticleFact.objects.select_related("parse__source_document__artifact__parent_record__current_snapshot"),pk=pk);artifact=article.parse.source_document.artifact
    try: current_fact=artifact.parent_record.current_snapshot.bcn_legal_norm_fact
    except BcnLegalNormFact.DoesNotExist: raise Http404
    try:current_artifact,current_parse=get_current_bcn_legal_text(current_fact)
    except Exception:raise Http404
    if article.parse_id!=current_parse.id or artifact.id!=current_artifact.id:raise Http404
    data=BcnLegalArticleFactSerializer(article).data;data.update({"version_uri":artifact.metadata.get("version_uri"),"source_url":artifact.source_url,"sha256":artifact.content_sha256});return Response(data)
def _current_obligation_candidates():
    snapshot_ids=current_bcn_norm_facts().values_list("snapshot_id",flat=True)
    return BcnLegalObligationCandidate.objects.annotate(artifact_version_uri=KeyTextTransform("version_uri","extraction_run__article__parse__source_document__artifact__metadata")).filter(extraction_run__extractor_version=BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION,extraction_run__status="success",extraction_run__source_text_hash=models.F("extraction_run__article__text_hash"),extraction_run__article__parse__parser_version=bcn_text.BCN_LEGAL_XML_PARSER_VERSION,extraction_run__article__parse__status="success",extraction_run__article__parse__source_document__artifact__is_current=True,extraction_run__article__parse__source_document__artifact__parent_record__current_snapshot_id__in=snapshot_ids,artifact_version_uri=models.F("extraction_run__article__parse__source_document__artifact__parent_record__current_snapshot__bcn_legal_norm_fact__latest_version_uri")).select_related("extraction_run__article__parse__source_document__artifact__parent_record__current_snapshot__bcn_legal_norm_fact")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_obligation_candidates(request):
    queryset=_current_obligation_candidates().order_by("id")
    for parameter,lookup in {"norm_number":"extraction_run__article__parse__source_document__artifact__metadata__norm_number__iexact","article_number":"extraction_run__article__article_number__iexact","modality":"modality_hint","trigger":"trigger_text__icontains"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    review_status=request.query_params.get("review_status")
    if review_status=="unreviewed":queryset=queryset.filter(review__isnull=True)
    elif review_status in ("approved","rejected"):queryset=queryset.filter(review__decision=review_status)
    return paginated(request,queryset,BcnLegalObligationCandidateSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_obligation_candidate_detail(request,pk):return Response(BcnLegalObligationCandidateSerializer(get_object_or_404(_current_obligation_candidates(),pk=pk)).data)
def _error(exc):return Response({"detail":getattr(exc,"messages",[str(exc)])},status=400)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def bcn_obligation_candidate_reject(request,pk):
    try:review=reject_legal_candidate(get_object_or_404(BcnLegalObligationCandidate,pk=pk),request.user,request.data.get("note",""));return Response({"id":review.id,"decision":review.decision},status=201)
    except Exception as exc:return _error(exc)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def bcn_obligation_candidate_promote(request,pk):
    forbidden={"source_provenance","code","version","state","reviewer"}&set(request.data)
    if forbidden:return Response({"detail":"Campos administrados por el servidor."},status=400)
    target=get_object_or_404(LegalObligation,pk=request.data["target_obligation_id"]) if request.data.get("target_obligation_id") else None
    fields={key:request.data.get(key,"") for key in EDITABLE};fields["note"]=request.data.get("note","")
    try:obligation,version,_=promote_legal_candidate(get_object_or_404(BcnLegalObligationCandidate,pk=pk),request.user,request.data.get("mode"),target,request.data.get("criteria",[]),**fields);return Response({"obligation_id":obligation.id,"version":LegalObligationVersionSerializer(version).data},status=201)
    except Exception as exc:return _error(exc)
def _version(pk):return get_object_or_404(LegalObligationVersion,pk=pk)
@api_view(["PATCH"])
@permission_classes([IsSuperUser])
def legal_obligation_draft(request,pk):
    forbidden=set(request.data)-set(EDITABLE)-{"criteria"}
    if forbidden:return Response({"detail":"Campos no editables."},status=400)
    try:return Response(LegalObligationVersionSerializer(update_legal_obligation_draft(_version(pk),request.user,request.data.get("criteria") if "criteria" in request.data else None,**{k:v for k,v in request.data.items() if k in EDITABLE})).data)
    except Exception as exc:return _error(exc)
def _transition(request,pk,service):
    try:return Response(LegalObligationVersionSerializer(service(_version(pk),request.user)).data)
    except Exception as exc:return _error(exc)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_obligation_validate(request,pk):return _transition(request,pk,validate_legal_obligation_version)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_obligation_activate(request,pk):return _transition(request,pk,activate_legal_obligation_version)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_obligation_obsolete(request,pk):return _transition(request,pk,obsolete_legal_obligation_version)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_obligations(request):
    queryset=LegalObligationVersion.objects.filter(state="active").select_related("obligation").prefetch_related("criteria").order_by("obligation_id")
    for parameter,lookup in {"modality":"modality","applicability_level":"applicability_level","norm_number":"source_provenance__norm_number"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    return paginated(request,queryset,LegalObligationVersionSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_obligation_detail(request,pk):return Response(LegalObligationVersionSerializer(get_object_or_404(LegalObligationVersion.objects.filter(obligation_id=pk,state="active").select_related("obligation").prefetch_related("criteria"))).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_obligation_version_detail(request,pk):return Response(LegalObligationVersionSerializer(get_object_or_404(LegalObligationVersion.objects.select_related("obligation").prefetch_related("criteria"),pk=pk)).data)


def _evidence_version(pk):
    return get_object_or_404(
        LegalEvidenceRequirementVersion.objects.select_related(
            "requirement__obligation", "legal_obligation_version__obligation"
        ),
        pk=pk,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_evidence_requirements(request):
    queryset = LegalEvidenceRequirementVersion.objects.filter(state="active").select_related(
        "requirement__obligation", "legal_obligation_version__obligation"
    ).order_by("requirement_id")
    if request.query_params.get("obligation_code"):
        queryset = queryset.filter(requirement__obligation__code=request.query_params["obligation_code"])
    if request.query_params.get("temporal_scope"):
        queryset = queryset.filter(temporal_scope=request.query_params["temporal_scope"])
    items = list(queryset)
    if request.query_params.get("evidence_class"):
        value = request.query_params["evidence_class"]
        items = [item for item in items if value in item.evidence_classes]
    if request.query_params.get("freshness"):
        value = request.query_params["freshness"]
        items = [item for item in items if get_legal_evidence_requirement_freshness(item) == value]
    return paginated(request, items, LegalEvidenceRequirementVersionSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_evidence_requirement_detail(request, pk):
    version = get_object_or_404(
        LegalEvidenceRequirementVersion.objects.filter(requirement_id=pk, state="active").select_related(
            "requirement__obligation", "legal_obligation_version__obligation"
        )
    )
    return Response(LegalEvidenceRequirementVersionSerializer(version).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def legal_evidence_requirement_version_detail(request, pk):
    return Response(LegalEvidenceRequirementVersionSerializer(_evidence_version(pk)).data)


def _evidence_fields(data):
    return {field: data[field] for field in EDITABLE_EVIDENCE_FIELDS if field in data}


EVIDENCE_CREATE_FIELDS = EDITABLE_EVIDENCE_FIELDS | {"legal_obligation_version_id"}


@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_create(request, obligation_id):
    if set(request.data) - EVIDENCE_CREATE_FIELDS:
        return Response({"detail": "Campos no permitidos."}, status=400)
    try:
        legal_version = get_object_or_404(LegalObligationVersion, pk=request.data.get("legal_obligation_version_id"))
        requirement, version = create_legal_evidence_requirement(
            get_object_or_404(LegalObligation, pk=obligation_id), legal_version, request.user, **_evidence_fields(request.data)
        )
        return Response(LegalEvidenceRequirementVersionSerializer(version).data, status=201)
    except Exception as exc:
        return _error(exc)


@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_new_version(request, pk):
    if set(request.data) - EVIDENCE_CREATE_FIELDS:
        return Response({"detail": "Campos no permitidos."}, status=400)
    try:
        version = create_legal_evidence_requirement_version(
            get_object_or_404(LegalEvidenceRequirement, pk=pk),
            get_object_or_404(LegalObligationVersion, pk=request.data.get("legal_obligation_version_id")),
            request.user,
            **_evidence_fields(request.data),
        )
        return Response(LegalEvidenceRequirementVersionSerializer(version).data, status=201)
    except Exception as exc:
        return _error(exc)


@api_view(["PATCH"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_draft(request, pk):
    forbidden = set(request.data) - EDITABLE_EVIDENCE_FIELDS
    if forbidden:
        return Response({"detail": "Campos no editables."}, status=400)
    try:
        return Response(LegalEvidenceRequirementVersionSerializer(update_legal_evidence_requirement_draft(_evidence_version(pk), request.user, **_evidence_fields(request.data))).data)
    except Exception as exc:
        return _error(exc)


def _evidence_transition(request, pk, service):
    try:
        return Response(LegalEvidenceRequirementVersionSerializer(service(_evidence_version(pk), request.user)).data)
    except Exception as exc:
        return _error(exc)


@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_validate(request, pk):return _evidence_transition(request, pk, validate_legal_evidence_requirement_version)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_activate(request, pk):return _evidence_transition(request, pk, activate_legal_evidence_requirement_version)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def legal_evidence_requirement_obsolete(request, pk):return _evidence_transition(request, pk, obsolete_legal_evidence_requirement_version)


def _provenance(fact):
    snapshot=fact.snapshot;source=snapshot.source
    return {"source_code":source.codigo,"source_name":source.nombre,"source_url":snapshot.source_url,"snapshot_id":snapshot.id,"retrieved_at":snapshot.retrieved_at,"upstream_updated_at":snapshot.upstream_updated_at,"content_hash":snapshot.content_hash,"source_freshness":source_freshness(source)}
def _snifa_dataset_data(item):return {"id":item.id,"dataset_code":item.dataset_code,"title":item.title,"description":item.description,"publisher":item.publisher,**_provenance(item)}
def _snifa_reference_data(item):return {"id":item.id,"reference_type":item.reference_type,"external_key":item.external_key,"expediente":item.expediente,"unit_external_key":item.unit_external_key,"unit_name":item.unit_name,"holder_name":item.holder_name,"category":item.category,"region":item.region,"commune":item.commune,"status_raw":item.status_raw,"event_date":item.event_date,"sanction_amount_raw":item.sanction_amount_raw,"payment_status_raw":item.payment_status_raw,"instrument_references":item.instrument_references,**_provenance(item)}
def _sea_project_data(item):return {"id":item.id,"project_key":item.project_key,"folio":item.folio,"name":item.name,"holder_name":item.holder_name,"region":item.region,"communes":item.communes,"presentation_type_raw":item.presentation_type_raw,"status_raw":item.status_raw,"sector_raw":item.sector_raw,"project_type_raw":item.project_type_raw,"admission_reason_raw":item.admission_reason_raw,"submission_date":item.submission_date,"qualification_date":item.qualification_date,"project_url":item.project_url,"expediente_url":item.expediente_url,"rca_references":[{"id":rca.id,"document_key":rca.document_key,"rca_number_raw":rca.rca_number_raw,"title":rca.title,"document_date":rca.document_date,"qualification_result_raw":rca.qualification_result_raw,"document_url":rca.document_url,"metadata":rca.metadata} for rca in item.rca_references.all()],**_provenance(item)}
def _geo_provenance(item):return _provenance(item)
def _simbio_data(item):
    fields=("service_code","service_name","service_url","layer_id","layer_name","layer_url","geometry_type","spatial_reference_wkid","display_field","object_id_field","max_record_count","supports_pagination","supports_distance_query","query_formats","fields_schema","service_item_id","provider_metadata")
    return {"id":item.id,**{field:getattr(item,field) for field in fields},"provider":"SIMBIO/MMA","biodiversity_data_responsibility_note":item.snapshot.source.sync_state.metadata.get("biodiversity_data_responsibility_note",""),**_geo_provenance(item)}
def _ide_dataset_data(item):
    fields=("dataset_key","title","summary","metadata_standard","metadata_date","resource_date","organization_name","role_raw","status_raw","resource_type_raw","language_raw","geometry_type_raw","feature_count","size_raw","keywords","categories","bbox_west","bbox_east","bbox_south","bbox_north","metadata_url")
    state=item.snapshot.source.sync_state
    return {"id":item.id,**{field:getattr(item,field) for field in fields},"interoperability_available":bool(state.metadata.get("interoperability_available")),"usage_context":"referential",**_geo_provenance(item)}
def _ide_download_data(item):
    fields=("resource_key","title","category_raw","declared_size_raw","download_url")
    state=item.snapshot.source.sync_state
    return {"id":item.id,**{field:getattr(item,field) for field in fields},"interoperability_available":bool(state.metadata.get("interoperability_available")),"usage_context":"referential",**_geo_provenance(item)}
def _page_dicts(request,items):
    paginator=KnowledgePagination();page=paginator.paginate_queryset(items,request);return paginator.get_paginated_response(list(page))
def _current_geo(model,source_code):return model.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo=source_code).select_related("snapshot__source","snapshot__source__sync_state")
def _current_okobaudat(model):return _current_geo(model,"okobaudat").filter(snapshot__current_for__estado="activo")
def _ok_provenance(item):
    metadata=item.snapshot.source.sync_state.metadata;return {"source_code":"okobaudat","selected_current_datastock":str(item.datastock_uuid)==metadata.get("selected_datastock_uuid"),"snapshot_id":item.snapshot_id,"content_hash":item.snapshot.content_hash,"retrieved_at":item.snapshot.retrieved_at,"source_freshness":source_freshness(item.snapshot.source),"source_url":item.source_url,"intended_use":"building_lca","not_designed_for_product_lca":True}
def _ok_stock_data(item):
    fields=("datastock_uuid","short_name","display_name","description","release_label","version_label","source_url","upstream_metadata");return {"id":item.id,**{field:getattr(item,field) for field in fields},**_ok_provenance(item)}
def _ok_process_data(item):
    fields=("datastock_uuid","process_uuid","dataset_version","name","base_name","location_raw","dataset_type_raw","owner_raw","classification","languages","compliance_standard_raw","compliance_source_uuid","permanent_uri","source_url","process_metadata");return {"id":item.id,**{field:getattr(item,field) for field in fields},**_ok_provenance(item)}
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def okobaudat_datastocks(request):return _page_dicts(request,[_ok_stock_data(item) for item in _current_okobaudat(OekobaudatDataStockFact).order_by("short_name")])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def okobaudat_datastock_detail(request,pk):return Response(_ok_stock_data(get_object_or_404(_current_okobaudat(OekobaudatDataStockFact),pk=pk)))
def _ok_process_queryset(request):
    qs=_current_okobaudat(OekobaudatProcessFact).order_by("name","process_uuid","dataset_version")
    for parameter,lookup in {"q":"name__icontains","name":"name__icontains","datastock_uuid":"datastock_uuid","location":"location_raw__iexact","dataset_type":"dataset_type_raw__iexact","compliance":"compliance_standard_raw__iexact","owner":"owner_raw__icontains"}.items():
        if request.query_params.get(parameter):qs=qs.filter(**{lookup:request.query_params[parameter]})
    classification=request.query_params.get("classification");language=request.query_params.get("language")
    return [item for item in qs if (not classification or classification.casefold() in str(item.classification).casefold()) and (not language or language in item.languages)]
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def okobaudat_processes(request):return _page_dicts(request,[_ok_process_data(item) for item in _ok_process_queryset(request)])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def okobaudat_process_detail(request,pk):
    item=next((item for item in _ok_process_queryset(request) if item.pk==pk),None)
    if not item:raise Http404
    return Response(_ok_process_data(item))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def simbio_layers(request):
    qs=_current_geo(SimbioGeoLayerFact,"simbio").order_by("service_code","layer_id")
    for parameter,lookup in {"service_code":"service_code__iexact","layer_name":"layer_name__icontains","geometry_type":"geometry_type__iexact"}.items():
        if request.query_params.get(parameter):qs=qs.filter(**{lookup:request.query_params[parameter]})
    distance=request.query_params.get("supports_distance_query")
    if distance is not None:qs=qs.filter(supports_distance_query=distance.lower() in ("1","true","yes"))
    return _page_dicts(request,[_simbio_data(item) for item in qs])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def simbio_layer_detail(request,pk):return Response(_simbio_data(get_object_or_404(_current_geo(SimbioGeoLayerFact,"simbio"),pk=pk)))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ide_datasets(request):
    qs=_current_geo(IdeMmaDatasetFact,"ide-mma").order_by("title")
    for parameter,lookup in {"title":"title__icontains","geometry_type":"geometry_type_raw__iexact","status":"status_raw__iexact"}.items():
        if request.query_params.get(parameter):qs=qs.filter(**{lookup:request.query_params[parameter]})
    category=request.query_params.get("category");keyword=request.query_params.get("keyword")
    items=[item for item in qs if (not category or category.casefold() in {str(v).casefold() for v in item.categories}) and (not keyword or keyword.casefold() in {str(v).casefold() for v in item.keywords})]
    return _page_dicts(request,[_ide_dataset_data(item) for item in items])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ide_dataset_detail(request,pk):return Response(_ide_dataset_data(get_object_or_404(_current_geo(IdeMmaDatasetFact,"ide-mma"),pk=pk)))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ide_downloads(request):
    qs=_current_geo(IdeMmaDownloadResourceFact,"ide-mma").order_by("title")
    for parameter,lookup in {"title":"title__icontains","category":"category_raw__iexact"}.items():
        if request.query_params.get(parameter):qs=qs.filter(**{lookup:request.query_params[parameter]})
    return _page_dicts(request,[_ide_download_data(item) for item in qs])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def snifa_datasets(request):
    items=SnifaOpenDatasetFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="snifa").select_related("snapshot__source").order_by("dataset_code");return _page_dicts(request,[_snifa_dataset_data(item) for item in items])
def _snifa_queryset(request):
    queryset=SnifaRegulatoryReferenceFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="snifa").select_related("snapshot__source").order_by("id")
    for parameter,lookup in {"reference_type":"reference_type","region":"region__iexact","commune":"commune__iexact","expediente":"expediente__iexact","status":"status_raw__iexact"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    return queryset
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def snifa_references(request):return _page_dicts(request,[_snifa_reference_data(item) for item in _snifa_queryset(request)])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def snifa_reference_detail(request,pk):return Response(_snifa_reference_data(get_object_or_404(_snifa_queryset(request),pk=pk)))
def _sea_queryset(request):
    queryset=SeaProjectFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="sea-seia").select_related("snapshot__source").prefetch_related("rca_references").order_by("id")
    for parameter,lookup in {"region":"region__iexact","presentation_type":"presentation_type_raw__iexact","status":"status_raw__iexact","sector":"sector_raw__iexact","folio":"folio__iexact"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    commune=request.query_params.get("commune");return [item for item in queryset if not commune or commune.casefold() in {str(value).casefold() for value in item.communes}]
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sea_projects(request):return _page_dicts(request,[_sea_project_data(item) for item in _sea_queryset(request)])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sea_project_detail(request,pk):
    item=next((item for item in _sea_queryset(request) if item.pk==pk),None)
    if not item:raise Http404
    return Response(_sea_project_data(item))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sea_discover(request):
    from .connectors.sea import discover_sea_projects
    allowed={"project_name","holder_name","folio","region","commune","presentation_type","status","sector"}
    if set(request.query_params)-allowed:return Response({"detail":"Filtros no permitidos."},status=400)
    try:return Response(discover_sea_projects(**{key:request.query_params[key] for key in allowed if request.query_params.get(key)}))
    except Exception as exc:return _error(exc)
def _subscriptions(request,model,source_code,allowed):
    source=get_object_or_404(EnvironmentalSource,codigo=source_code)
    if request.method=="GET":return Response(list(model.objects.filter(source=source).order_by("id").values("id",*sorted(allowed))))
    if set(request.data)-allowed:return Response({"detail":"Campos no permitidos."},status=400)
    try:
        item=model(source=source,**{key:request.data[key] for key in allowed if key in request.data});item.save();return Response({"id":item.id},status=201)
    except Exception as exc:return _error(exc)
@api_view(["GET","POST"])
@permission_classes([IsSuperUser])
def snifa_subscriptions(request):return _subscriptions(request,SnifaReferenceSubscription,"snifa",{"reference_type","external_key","source_url","label","scope_tags","active"})
@api_view(["GET","POST"])
@permission_classes([IsSuperUser])
def sea_subscriptions(request):return _subscriptions(request,SeaProjectSubscription,"sea-seia",{"project_key","project_url","label","scope_tags","active"})
def _subscription_detail(request,model,pk,allowed):
    item=get_object_or_404(model,pk=pk)
    if request.method=="GET":return Response({"id":item.id,**{key:getattr(item,key) for key in sorted(allowed)}})
    if set(request.data)-allowed:return Response({"detail":"Campos no permitidos."},status=400)
    try:
        for key,value in request.data.items():setattr(item,key,value)
        item.save();return Response({"id":item.id})
    except Exception as exc:return _error(exc)
@api_view(["GET","PATCH"])
@permission_classes([IsSuperUser])
def snifa_subscription_detail(request,pk):return _subscription_detail(request,SnifaReferenceSubscription,pk,{"reference_type","external_key","source_url","label","scope_tags","active"})
@api_view(["GET","PATCH"])
@permission_classes([IsSuperUser])
def sea_subscription_detail(request,pk):return _subscription_detail(request,SeaProjectSubscription,pk,{"project_key","project_url","label","scope_tags","active"})
