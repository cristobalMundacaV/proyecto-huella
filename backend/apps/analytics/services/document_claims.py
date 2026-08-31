from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class DocumentClaims:
    tipo_documento: str = "otro"
    relevancia_detectada: str = "indeterminado"
    confianza: float = 0.0
    texto_extraido: str = ""
    claims: dict = field(default_factory=dict)
    claims_trazables: dict = field(default_factory=dict)
    origen_extraccion: str = "fallback_seguro"
    motivo_relevancia: str = ""
    legibilidad: str = ""
    confianza_extraccion: float | None = None
    execution_status: str = "empty"
    extractor_used: str = "safe_fallback"
    provider_used: str = "none"
    failure_code: str = "no_claims_detected"
    claims_count: int = 0
    extraction_metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def safe_document_claims(
    *, text="", origin="fallback_seguro", status="empty",
    extractor="safe_fallback", provider="none", failure_code="no_claims_detected",
    metadata=None,
):
    return DocumentClaims(
        texto_extraido=text or "",
        origen_extraccion=origin,
        execution_status=status,
        extractor_used=extractor,
        provider_used=provider,
        failure_code=failure_code,
        claims_count=0,
        extraction_metadata=metadata or {},
    )
