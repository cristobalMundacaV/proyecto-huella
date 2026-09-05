from .base import ConnectorBatch, EnvironmentalConnector
class FakeEnvironmentalConnector(EnvironmentalConnector):
    batch = ConnectorBatch(records=[])
    error = None
    def fetch(self, sync_state):
        if self.error: raise self.error
        return self.batch
