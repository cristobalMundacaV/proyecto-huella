"""AI-INTELLIGENCE-02 — tenant-scoped name resolution.

Nothing here existed before this macrophase (confirmed by audit: every
existing selector — `material_for_organization`, `work_for_organization`,
`asset_for_organization` — is strict ID-only). This lets the assistant
accept a natural-language reference ("agua", "hormigón", an obra's name,
an asset's name) instead of demanding an internal numeric ID, while never
guessing across tenants and always surfacing ambiguity explicitly rather
than silently picking one match.

Each `resolve_*` function returns:
    {"status": "resolved", "match": {...}}
    {"status": "ambiguous", "candidates": [{...}, ...]}
    {"status": "not_found"}
Never raises for "no match" or "many matches" — those are normal,
expected outcomes a tool result communicates, not errors.
"""
from django.db.models import Q

from apps.analytics.models import MaterialOperacional, Obra
from apps.analytics.models.assets import ActivoOperacional
from apps.analytics.permissions import filter_works_for_user

MAX_CANDIDATES = 8


def _outcome(matches, serialize):
    if not matches:
        return {"status": "not_found"}
    if len(matches) == 1:
        return {"status": "resolved", "match": serialize(matches[0])}
    return {"status": "ambiguous", "candidates": [serialize(row) for row in matches[:MAX_CANDIDATES]]}


def resolve_obra(organization, user, query):
    query = (query or "").strip()
    if not query:
        return {"status": "not_found"}
    obras = filter_works_for_user(Obra.objects.filter(organizacion=organization), user, organization)
    matches = list(obras.filter(nombre__icontains=query).order_by("nombre")[:MAX_CANDIDATES + 1])
    if not matches:
        # Fall back to an exact-code match — never widen the tenant scope.
        matches = list(obras.filter(codigo_obra__iexact=query)[:MAX_CANDIDATES + 1])
    return _outcome(matches, lambda obra: {"id": obra.pk, "nombre": obra.nombre, "estado": obra.estado})


def resolve_material(organization, query):
    query = (query or "").strip()
    if not query:
        return {"status": "not_found"}
    materials = MaterialOperacional.objects.filter(organizacion=organization).filter(
        Q(nombre__icontains=query) | Q(categoria__icontains=query) | Q(codigo__icontains=query)
    ).order_by("nombre")
    matches = list(materials[:MAX_CANDIDATES + 1])
    return _outcome(matches, lambda material: {
        "id": material.pk, "nombre": material.nombre, "categoria": material.categoria,
        "codigo": material.codigo, "unidad_base": material.unidad_base,
    })


def resolve_activo(organization, query):
    query = (query or "").strip()
    if not query:
        return {"status": "not_found"}
    activos = ActivoOperacional.objects.filter(organizacion=organization).filter(
        Q(nombre__icontains=query) | Q(codigo__icontains=query)
    ).order_by("nombre")
    matches = list(activos[:MAX_CANDIDATES + 1])
    return _outcome(matches, lambda activo: {
        "id": activo.pk, "nombre": activo.nombre, "codigo": activo.codigo, "tipo": activo.tipo,
    })


RESOLVERS = {
    "obra": lambda organization, user, query: resolve_obra(organization, user, query),
    "material": lambda organization, user, query: resolve_material(organization, query),
    "activo": lambda organization, user, query: resolve_activo(organization, query),
}
