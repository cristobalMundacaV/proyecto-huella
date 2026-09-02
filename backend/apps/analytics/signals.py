import logging

from .services.system_environmental_catalog import ensure_system_environmental_catalog


logger = logging.getLogger(__name__)


def ensure_environmental_catalog_after_migrate(**kwargs):
    try:
        result = ensure_system_environmental_catalog()
    except Exception:
        logger.exception(
            "No fue posible verificar el catalogo ambiental global despues de migrate."
        )
        raise
    logger.info(
        "Catalogo ambiental global v%s verificado despues de migrate.",
        result["catalog_version"],
    )
