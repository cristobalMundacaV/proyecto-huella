from django.http import JsonResponse

from .models import UsuarioOrganizacion


class OrganizacionTenantMiddleware:
    """Protege toda ruta cuyo tenant venga identificado en la URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        organizacion_id = view_kwargs.get("organizacion_id")
        if not organizacion_id:
            return None
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Autenticacion requerida."}, status=401)
        if request.user.is_superuser:
            return None
        allowed = UsuarioOrganizacion.objects.filter(
            user=request.user,
            activo=True,
            organizacion__organizacion_id=organizacion_id,
            organizacion__activa=True,
        ).exists()
        if not allowed:
            # Un 404 evita revelar la existencia de tenants ajenos.
            return JsonResponse({"error": "Organizacion no encontrada."}, status=404)
        return None
