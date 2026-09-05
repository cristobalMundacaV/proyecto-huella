from .fake import FakeEnvironmentalConnector
from .retc import RetcCkanConnector
CONNECTOR_REGISTRY={"fake":FakeEnvironmentalConnector,"retc_ckan":RetcCkanConnector}
def connector_for(source):
    connector=CONNECTOR_REGISTRY.get(source.connector_key)
    if not connector: raise LookupError(f"Conector no registrado: {source.connector_key}")
    return connector(source)
