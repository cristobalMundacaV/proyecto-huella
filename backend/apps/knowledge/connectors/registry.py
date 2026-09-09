from .fake import FakeEnvironmentalConnector
from .retc import RetcCkanConnector
from .huellachile import HuellaChileConnector
from .bcn import BcnLeyChileSparqlConnector
from .snifa import SnifaPublicConnector
from .sea import SeaSeiaPublicConnector
from .simbio import SimbioArcgisConnector
from .ide_mma import IdeMmaCatalogConnector
from .okobaudat import OekobaudatSoda4LcaConnector
CONNECTOR_REGISTRY={"fake":FakeEnvironmentalConnector,"retc_ckan":RetcCkanConnector,"huellachile_web":HuellaChileConnector,"bcn_leychile_sparql":BcnLeyChileSparqlConnector,"snifa_public":SnifaPublicConnector,"sea_seia_public":SeaSeiaPublicConnector,"simbio_arcgis":SimbioArcgisConnector,"ide_mma_catalog":IdeMmaCatalogConnector,"okobaudat_soda4lca":OekobaudatSoda4LcaConnector}
def connector_for(source):
    connector=CONNECTOR_REGISTRY.get(source.connector_key)
    if not connector: raise LookupError(f"Conector no registrado: {source.connector_key}")
    return connector(source)
