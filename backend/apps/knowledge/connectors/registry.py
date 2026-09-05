from .fake import FakeEnvironmentalConnector
CONNECTOR_REGISTRY={"fake":FakeEnvironmentalConnector}
def connector_for(source):
    connector=CONNECTOR_REGISTRY.get(source.connector_key)
    if not connector: raise LookupError(f"Conector no registrado: {source.connector_key}")
    return connector(source)
