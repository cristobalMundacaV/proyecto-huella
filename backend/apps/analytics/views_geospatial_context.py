from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Organizacion,Obra,UsuarioOrganizacion,WorkGeolocationRevision,WorkTerritorialObservationRevision
from .permissions import Permission,has_tenant_permission,require_tenant_permission,require_work_access
from .services.geospatial_context import get_work_territorial_observation_freshness,get_work_territorial_readiness,observe_work_territorial_context,set_work_geolocation
def _scope(request,org_id,work_id,permission):
    org=get_object_or_404(Organizacion,organizacion_id=org_id)
    if not request.user.is_superuser and not UsuarioOrganizacion.objects.filter(user=request.user,organizacion=org,activo=True).exists():
        from django.http import Http404
        raise Http404("Recurso no encontrado.")
    require_tenant_permission(request.user,org,permission)
    work=get_object_or_404(Obra,pk=work_id,organizacion=org);require_work_access(request.user,org,work);return org,work
def _location(item):return None if not item else {"revision":item.revision,"latitude":item.latitude,"longitude":item.longitude,"srid":item.srid,"capture_method":item.capture_method,"accuracy_m":item.accuracy_m,"source_reference":item.source_reference,"note":item.note,"coordinate_hash":item.coordinate_hash,"created_by":item.created_by_id,"created_at":item.created_at}
@api_view(["GET","POST"])
@permission_classes([IsAuthenticated])
def work_geolocation(request,organization_id,work_id):
    org,work=_scope(request,organization_id,work_id,Permission.WORK_VIEW if request.method=="GET" else Permission.WORK_UPDATE)
    if request.method=="GET":return Response(_location(WorkGeolocationRevision.objects.filter(work=work,is_latest=True).first()))
    try:item,created=set_work_geolocation(request.user,org,work,**request.data)
    except ValidationError as exc:return Response({"detail":exc.messages},status=400)
    return Response({**_location(item),"created":created},status=201 if created else 200)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def work_geolocation_history(request,organization_id,work_id):
    _,work=_scope(request,organization_id,work_id,Permission.WORK_VIEW);return Response([_location(item) for item in WorkGeolocationRevision.objects.filter(work=work).order_by("-revision")])
def _observation(item,detail=False):
    if not item:return None
    data={"revision":item.revision,"location_revision":item.geolocation_revision.revision,"observed_at":item.observed_at,"source_checksum":item.source_snapshot.get("last_checksum"),"layer_snapshots":item.layer_catalog_snapshot,"summary":item.summary_snapshot,"result_hash":item.result_hash,"freshness":get_work_territorial_observation_freshness(item.work,item)}
    if detail:data["results_snapshot"]=item.results_snapshot
    return data
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def work_territorial_context(request,organization_id,work_id):
    org,work=_scope(request,organization_id,work_id,Permission.PROFILE_VIEW);require_tenant_permission(request.user,org,Permission.WORK_VIEW);latest=WorkTerritorialObservationRevision.objects.filter(work=work,is_latest=True).select_related("work","geolocation_revision").first();return Response({"readiness":get_work_territorial_readiness(work),"location":_location(WorkGeolocationRevision.objects.filter(work=work,is_latest=True).first()),"source":latest.source_snapshot if latest else None,"latest_observation":_observation(latest)})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def observe_work_context(request,organization_id,work_id):
    org,work=_scope(request,organization_id,work_id,Permission.PROFILE_MANAGE)
    if request.data:return Response({"detail":"El cuerpo debe estar vacio."},status=400)
    try:item,changed=observe_work_territorial_context(request.user,org,work)
    except ValidationError as exc:return Response({"detail":exc.messages},status=400)
    except Exception as exc:
        from apps.knowledge.services import sanitized_error
        return Response({"detail":sanitized_error(exc)},status=502)
    return Response({**_observation(item,True),"changed_from_previous":changed},status=201)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def work_territorial_history(request,organization_id,work_id):
    _,work=_scope(request,organization_id,work_id,Permission.PROFILE_VIEW);return Response([_observation(item) for item in WorkTerritorialObservationRevision.objects.filter(work=work).select_related("work","geolocation_revision").order_by("-revision")])
