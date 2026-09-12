"""SOURCE-WATCH-01A — watch policy authority.

`EnvironmentalSource` already carries the tenant-free registry identity and
governance fields (`activa`, `stale_after_hours`, `connector_key`,
`tipo_acceso`, `cadencia_sugerida`). This module adds only what was
genuinely missing: a machine-actionable cadence (`cadencia_horas`), an
explicit "safe for unattended automatic polling" flag distinct from
`activa` (`permite_poll_automatico`), and a read-only capability lookup per
connector — because whether a connector's fetch is an authoritative full
snapshot, supports an incremental cursor, or captures conditional HTTP
metadata is a property of the connector's *implementation*, not per-source
instance data, and must never be invented per source.

Capability values below are not guesses: they describe exactly what each
connector's `fetch()` does today (see each connector module). None of the
nine registered connectors currently narrows its request using a stored
cursor — they always re-fetch fully and rely on `ExternalSnapshot`'s
content-hash dedup — so `supports_cursor` is `False` everywhere; this is
reported truthfully rather than aspirationally.
"""

from .connectors.registry import CONNECTOR_REGISTRY

CONNECTOR_CAPABILITIES = {
    "fake": {
        "authoritative_full_snapshot": None,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "retc_ckan": {
        "authoritative_full_snapshot": True,
        "supports_cursor": False,
        "captures_conditional_http_metadata": True,
    },
    "huellachile_web": {
        "authoritative_full_snapshot": False,
        "supports_cursor": False,
        "captures_conditional_http_metadata": True,
    },
    "bcn_leychile_sparql": {
        "authoritative_full_snapshot": False,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "snifa_public": {
        "authoritative_full_snapshot": False,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "sea_seia_public": {
        "authoritative_full_snapshot": False,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "simbio_arcgis": {
        "authoritative_full_snapshot": True,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "ide_mma_catalog": {
        "authoritative_full_snapshot": True,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
    "okobaudat_soda4lca": {
        "authoritative_full_snapshot": True,
        "supports_cursor": False,
        "captures_conditional_http_metadata": False,
    },
}

UNKNOWN_CAPABILITIES = {
    "authoritative_full_snapshot": None,
    "supports_cursor": False,
    "captures_conditional_http_metadata": False,
}


def connector_capabilities(connector_key):
    """None when the connector is not registered at all (fail closed —
    never assume capabilities for an unknown/unsupported connector)."""
    if connector_key not in CONNECTOR_REGISTRY:
        return None
    return CONNECTOR_CAPABILITIES.get(connector_key, dict(UNKNOWN_CAPABILITIES))


def describe_watch_policy(source):
    """The single, explicit answer to "how should this source be watched,
    how stale may it become, and what does its connector actually
    support?" — never invented, always derived from governed fields plus
    the connector's own real capabilities."""

    capabilities = connector_capabilities(source.connector_key)
    connector_registered = capabilities is not None
    if capabilities is None:
        capabilities = dict(UNKNOWN_CAPABILITIES)

    safe_to_auto_watch = bool(
        source.activa and source.permite_poll_automatico and connector_registered
    )

    return {
        "source_id": source.pk,
        "codigo": source.codigo,
        "activa": source.activa,
        "connector_key": source.connector_key,
        "connector_registered": connector_registered,
        "tipo_acceso": source.tipo_acceso,
        "stale_after_hours": source.stale_after_hours,
        "cadencia_sugerida": source.cadencia_sugerida,
        "cadencia_horas": source.cadencia_horas,
        "permite_poll_automatico": source.permite_poll_automatico,
        "safe_to_auto_watch": safe_to_auto_watch,
        "capabilities": capabilities,
    }
