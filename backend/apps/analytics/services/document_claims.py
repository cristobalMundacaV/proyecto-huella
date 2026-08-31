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

    def to_dict(self):
        return asdict(self)


def safe_document_claims(*, text="", origin="fallback_seguro"):
    return DocumentClaims(texto_extraido=text or "", origen_extraccion=origin)
