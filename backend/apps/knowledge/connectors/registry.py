from .fake import FakeEnvironmentalConnector
from .retc import RetcCkanConnector
from .huellachile import HuellaChileConnector
CONNECTOR_REGISTRY={"fake":FakeEnvironmentalConnector,"retc_ckan":RetcCkanConnector,"huellachile_web":HuellaChileConnector}
def connector_for(source):
    connector=CONNECTOR_REGISTRY.get(source.connector_key)
    if not connector: raise LookupError(f"Conector no registrado: {source.connector_key}")
    return connector(source)
