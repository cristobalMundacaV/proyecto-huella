from django.shortcuts import get_object_or_404

from ..models import Organizacion


def organization_available_to_user(user, organization_id):
    queryset = Organizacion.objects.all()
    if not user.is_superuser:
        queryset = queryset.filter(usuarios__user=user, usuarios__activo=True)
    return get_object_or_404(queryset.distinct(), organizacion_id=organization_id)
