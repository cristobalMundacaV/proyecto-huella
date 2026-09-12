from apps.knowledge.connectors.base import EnvironmentalConnector


class Ec3Connector(EnvironmentalConnector):
    def fetch(self, sync_state):
        raise ValueError("EC3 requiere ingestión dirigida por ID; use ingest_ec3_epd.")
