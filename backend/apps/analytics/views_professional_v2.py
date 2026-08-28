from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    ActividadOperacional,
    ExpedienteAmbiental,
    Obra,
    Organizacion,
    ProblematicaAmbiental,
    ResultadoIntervencion,
)
from .selectors.professional import (
    audit_events,
    dossier_for_organization,
    dossiers_for_organization,
    problem_for_dossier,
    report_for_organization,
    report_reference,
    review_for_organization,
    reviews_for_organization,
)
from .permissions import (
    Permission,
    filter_works_for_user,
    get_membership,
    has_tenant_permission,
    require_resource_work_access,
)
from .serializers_professional_v2 import (
    EventoAuditoriaSerializer,
    ExpedienteSerializer,
    HallazgoSerializer,
    InformeSerializer,
    RevisionProfesionalSerializer,
)
from .services.professional_v2 import (
    audit,
    can_review,
    close_dossier,
    create_dossier,
    decide_review,
    generate_report,
    reopen_dossier,
    validate_report,
)


def _organization(request, value, permission=Permission.REVIEW_PROFESSIONAL):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    if not request.user.is_superuser and not get_membership(request.user, organization):
        return None
    if not has_tenant_permission(request.user, organization, permission):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("No tienes permisos para realizar esta acción.")
    return organization


def _work(
    request,
    organization,
):
    work_id = request.query_params.get("obra")

    if not work_id:
        return None

    return get_object_or_404(
        filter_works_for_user(Obra.objects.all(), request.user, organization),
        id=work_id,
    )


def _error(exc):
    return Response({"detail": getattr(exc, "messages", [str(exc)])}, status=400)


def _missing():
    return Response({"detail": "Recurso no encontrado."}, status=404)


@api_view(["GET", "POST"])
def revisiones_profesionales(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return _missing()
    if request.method == "GET":
        work = _work(
            request,
            organization,
        )

        queryset = reviews_for_organization(
            organization,
            work,
            request.query_params.get("estado"),
            request.query_params.get("tipo"),
        )
        return Response(RevisionProfesionalSerializer(queryset, many=True).data)
    serializer = RevisionProfesionalSerializer(
        data=request.data, context={"organizacion": organization}
    )
    serializer.is_valid(raise_exception=True)
    reference = next(
        (
            serializer.validated_data.get(field)
            for field in (
                "evidencia",
                "observacion",
                "calculo",
                "indicador",
                "problematica",
                "intervencion",
                "expediente",
            )
            if serializer.validated_data.get(field)
        ),
        None,
    )
    version = (
        organization.revisiones_profesionales.filter(
            tipo=serializer.validated_data["tipo"],
            **{
                field: reference
                for field in (
                    "evidencia",
                    "observacion",
                    "calculo",
                    "indicador",
                    "problematica",
                    "intervencion",
                    "expediente",
                )
                if serializer.validated_data.get(field)
            },
        ).count()
        + 1
    )
    review = serializer.save(organizacion=organization, version=version)
    audit(
        organization,
        "creacion_revision_profesional",
        request.user,
        "RevisionProfesionalAmbiental",
        review.id,
        "Revision profesional creada.",
        {"version": version},
    )
    return Response(RevisionProfesionalSerializer(review).data, status=201)


@api_view(["GET", "PATCH"])
def revision_profesional_detail(request, organizacion_id, revision_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return _missing()
    review = get_object_or_404(review_for_organization(organization, revision_id))
    require_resource_work_access(request.user, organization, review)
    if request.method == "GET":
        return Response(RevisionProfesionalSerializer(review).data)
    if not can_review(request.user, organization):
        return Response({"detail": "Sin capacidad profesional."}, status=403)
    serializer = RevisionProfesionalSerializer(
        review, data=request.data, partial=True, context={"organizacion": organization}
    )
    serializer.is_valid(raise_exception=True)
    try:
        serializer.save()
    except ValidationError as exc:
        return _error(exc)
    return Response(serializer.data)


@api_view(["POST"])
def revision_hallazgos(request, organizacion_id, revision_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return _missing()
    if not can_review(request.user, organization):
        return Response({"detail": "Sin capacidad profesional."}, status=403)
    review = get_object_or_404(
        review_for_organization(organization, revision_id, "pendiente"),
    )
    require_resource_work_access(request.user, organization, review)
    serializer = HallazgoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    finding = serializer.save(revision=review)
    return Response(HallazgoSerializer(finding).data, status=201)


@api_view(["POST"])
def revision_decision(request, organizacion_id, revision_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return _missing()
    review = get_object_or_404(review_for_organization(organization, revision_id))
    require_resource_work_access(request.user, organization, review)
    try:
        decided = decide_review(
            review,
            request.data.get("estado"),
            request.data.get("conclusion", ""),
            request.data.get("observaciones", ""),
            request.data.get("antecedentes_solicitados", []),
            request.user,
        )
        return Response(RevisionProfesionalSerializer(decided).data)
    except ValidationError as exc:
        return _error(exc)


@api_view(["GET"])
def auditoria(request, organizacion_id):
    organization = _organization(request, organizacion_id, Permission.AUDIT_VIEW)
    if not organization:
        return _missing()
    queryset = audit_events(organization, request.query_params.get("tipo"))
    return Response(EventoAuditoriaSerializer(queryset[:200], many=True).data)


@api_view(["GET", "POST"])
def expedientes(request, organizacion_id):
    permission = (
        Permission.PROBLEM_VIEW
        if request.method == "GET"
        else Permission.PROBLEM_MANAGE
    )
    organization = _organization(request, organizacion_id, permission)
    if not organization:
        return _missing()
    if request.method == "GET":
        work = _work(
            request,
            organization,
        )

        queryset = dossiers_for_organization(organization, work)

        return Response(
            ExpedienteSerializer(
                queryset,
                many=True,
            ).data
        )
    work = _work(
        request,
        organization,
    )

    problem = get_object_or_404(
        problem_for_dossier(organization, request.data.get("problematica"), work)
    )
    return Response(
        ExpedienteSerializer(create_dossier(problem, request.user)).data, status=201
    )


@api_view(["GET"])
def expediente_detail(
    request,
    organizacion_id,
    expediente_id,
):
    organization = _organization(
        request,
        organizacion_id,
    )

    if not organization:
        return _missing()

    work = _work(
        request,
        organization,
    )

    item = get_object_or_404(
        dossier_for_organization(organization, expediente_id, work, detailed=True)
    )

    return Response(ExpedienteSerializer(item).data)


@api_view(["POST"])
def expediente_close(
    request,
    organizacion_id,
    expediente_id,
):
    organization = _organization(
        request,
        organizacion_id,
    )

    if not organization:
        return _missing()

    work = _work(
        request,
        organization,
    )

    item = get_object_or_404(
        dossier_for_organization(organization, expediente_id, work)
    )

    try:
        return Response(
            ExpedienteSerializer(
                close_dossier(
                    item,
                    request.user,
                )
            ).data
        )

    except ValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def expediente_reopen(
    request,
    organizacion_id,
    expediente_id,
):
    organization = _organization(
        request,
        organizacion_id,
    )

    if not organization:
        return _missing()

    work = _work(
        request,
        organization,
    )

    item = get_object_or_404(
        dossier_for_organization(organization, expediente_id, work)
    )

    try:
        return Response(
            ExpedienteSerializer(
                reopen_dossier(
                    item,
                    request.user,
                    request.data.get(
                        "motivo",
                        "",
                    ),
                )
            ).data
        )

    except ValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def informes(request, organizacion_id):
    organization = _organization(request, organizacion_id, Permission.REPORT_GENERATE)
    if not organization:
        return _missing()
    report_type = request.data.get("tipo")
    activity = (
        get_object_or_404(
            report_reference(
                organization, ActividadOperacional, request.data["actividad"]
            )
        )
        if request.data.get("actividad")
        else None
    )
    problem = (
        get_object_or_404(
            report_reference(
                organization, ProblematicaAmbiental, request.data["problematica"]
            )
        )
        if request.data.get("problematica")
        else None
    )
    intervention = (
        get_object_or_404(
            report_reference(
                organization, ResultadoIntervencion, request.data["intervencion"]
            )
        )
        if request.data.get("intervencion")
        else None
    )
    dossier = (
        get_object_or_404(
            report_reference(
                organization, ExpedienteAmbiental, request.data["expediente"]
            )
        )
        if request.data.get("expediente")
        else None
    )
    primary = {
        "actividad": activity,
        "problematica": problem,
        "intervencion": intervention,
        "expediente": dossier,
    }.get(report_type)
    if not primary:
        return Response(
            {"detail": "El tipo requiere su objeto principal correspondiente."},
            status=400,
        )
    require_resource_work_access(request.user, organization, primary)
    try:
        report = generate_report(
            organization,
            report_type,
            request.user,
            activity,
            problem,
            intervention,
            dossier,
        )
    except ValidationError as exc:
        return _error(exc)
    return Response(InformeSerializer(report).data, status=201)


@api_view(["GET"])
def informe_detail(request, organizacion_id, informe_id):
    organization = _organization(request, organizacion_id, Permission.REPORT_VIEW)
    if not organization:
        return _missing()
    return Response(
        InformeSerializer(
            get_object_or_404(
                report_for_organization(organization, informe_id, detailed=True),
            )
        ).data
    )


@api_view(["GET"])
def informe_pdf(request, organizacion_id, informe_id):
    organization = _organization(request, organizacion_id, Permission.REPORT_VIEW)
    if not organization:
        return _missing()
    report = get_object_or_404(report_for_organization(organization, informe_id))
    return FileResponse(
        report.archivo.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename=f"informe-{report.id}-v{report.version}.pdf",
    )


@api_view(["POST"])
def informe_validate(request, organizacion_id, informe_id):
    organization = _organization(request, organizacion_id, Permission.REPORT_APPROVE)
    if not organization:
        return _missing()
    report = get_object_or_404(report_for_organization(organization, informe_id))
    try:
        return Response(InformeSerializer(validate_report(report, request.user)).data)
    except ValidationError as exc:
        return _error(exc)
