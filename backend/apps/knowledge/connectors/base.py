from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class ConnectorRecord:
    external_id:str; kind:str; source_url:str=""; payload:Any=None; text:str=""; published_at:Any=None; upstream_updated_at:Any=None; metadata:dict=field(default_factory=dict); title:str=""; canonical_key:str=""; content_type:str="application/json"
@dataclass(frozen=True)
class ConnectorBatch:
    records:list; cursor:Any=None; upstream_version:str=""; etag:str=""; last_modified:str=""; authoritative_full_snapshot:bool=False; metadata:dict=field(default_factory=dict)
class EnvironmentalConnector:
    def __init__(self, source): self.source=source
    def fetch(self, sync_state): raise NotImplementedError
