from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import Permission, has_tenant_permission
from .policies.platform import can_administer_organization
from .selectors.platform import organization_available_to_user
from .serializers import OrganizacionSerializer
from .services.platform import delete_organization_with_related_data

# Public compatibility aliases retained for existing internal imports.
delete_organizacion_with_related_data = delete_organization_with_related_data


def get_organizacion_or_404(request, organizacion_id):
    return organization_available_to_user(request.user, organizacion_id)


def can_administer(user, organization):
    return can_administer_organization(user, organization)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def organizacion_detail_safe(request, organizacion_id):
    organizacion = get_organizacion_or_404(request, organizacion_id)

    if request.method == "GET":
        if not has_tenant_permission(
            request.user, organizacion, Permission.ORGANIZATION_VIEW
        ):
            return Response(
                {"detail": "No tienes permisos para consultar esta organización."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(OrganizacionSerializer(organizacion).data)

    if request.method == "PATCH":
        if not can_administer(request.user, organizacion):
            return Response(
                {"detail": "No tienes permisos para modificar esta organización."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payload = request.data.copy()
        if not request.user.is_superuser:
            payload.pop("activa", None)
            payload.pop("organizacion_id", None)
        serializer = OrganizacionSerializer(organizacion, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    if not request.user.is_superuser:
        return Response(
            {
                "detail": "La eliminación de organizaciones corresponde a la administración de plataforma."
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        deleted_summary = delete_organization_with_related_data(organizacion)
    except ProtectedError as exc:
        protected_objects = [str(obj) for obj in exc.protected_objects][:5]
        return Response(
            {
                "error": "No se pudo eliminar la organizacion porque existen relaciones protegidas.",
                "detalle": protected_objects,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {"deleted": True, "resumen": deleted_summary}, status=status.HTTP_200_OK
    )
