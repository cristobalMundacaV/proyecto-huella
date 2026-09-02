import logging

from .services.construction_sources import ensure_existing_construction_v1_sources
from .services.system_environmental_catalog import ensure_system_environmental_catalog


logger = logging.getLogger(__name__)


def ensure_environmental_catalog_after_migrate(**kwargs):
    try:
        result = ensure_system_environmental_catalog()
        construction_sources_created = ensure_existing_construction_v1_sources()
    except Exception:
        logger.exception(
            "No fue posible verificar los catalogos ambientales despues de migrate."
        )
        raise
    logger.info(
        "Catalogo ambiental global v%s verificado despues de migrate; "
        "%s fuentes Construction V1 agregadas a tenants existentes.",
        result["catalog_version"],
        construction_sources_created,
    )
