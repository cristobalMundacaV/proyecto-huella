import re

from django.http import JsonResponse

from .models import Organizacion, SuscripcionSaaS


class SaaSAccessMiddleware:
    """Bloquea el plano operacional sin eliminar ni alterar información tenant."""

    organization_pattern = re.compile(r"^/api/organizaciones/([^/]+)/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        match = self.organization_pattern.match(request.path)
        if match and user and user.is_authenticated and not user.is_superuser:
            blocked = SuscripcionSaaS.objects.filter(
                organizacion__organizacion_id=match.group(1),
                disponibilidad=SuscripcionSaaS.Disponibilidad.BLOQUEADO,
            ).select_related("organizacion").first()
            if blocked:
                return JsonResponse({
                    "detail": "El acceso operativo de esta organización está temporalmente suspendido.",
                    "code": "saas_access_blocked",
                    "organization": blocked.organizacion.nombre,
                    "state": blocked.estado,
                }, status=423)
        return self.get_response(request)
