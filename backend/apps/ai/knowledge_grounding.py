"""AI INTELLIGENCE macrofase — knowledge grounding classification.

Every piece of information the assistant surfaces must be tagged into
exactly one of four categories, so the model can never blur them:

* `dato_operacional`   — an observed/recorded fact (a reception, a
  consumption reading) — from `EventoMaterial`/`Observacion`.
* `factor_cientifico`  — a governed environmental factor/EPD used to
  compute impact — from `FactorAmbiental`/`VersionFactorAmbiental`/EC3.
* `fuente_normativa`   — a regulatory/authoritative reference — only ever
  populated from `apps.knowledge` (SOURCE-WATCH: RETC, SNIFA, SEA, ...),
  reached via the existing `search_environmental_knowledge` tool; this
  system has NO compliance engine, so this is `None` unless a real
  knowledge-base record is attached — never fabricated.
* `interpretacion`     — anything added by the LLM (a reading of the
  facts, a recommendation) — this backend NEVER fills this key; it is
  reserved so the model is structurally reminded to label its own
  additions separately from what the backend actually found.
"""


def classify_provenance_entry(entry):
    """Splits one `ledger_entry_provenance`-shaped dict (see
    `apps.analytics.services.material_ledger.ledger_entry_provenance`)
    into the four grounding categories. Never invents a `fuente_normativa`
    — this system has no normative/compliance engine attached here."""
    return {
        "dato_operacional": {
            "evento_recepcion_id": entry.get("evento_recepcion_id"),
            "actividad_id": entry.get("actividad_id"),
            "resultado": entry.get("resultado"),
            "unidad": entry.get("unidad_resultado"),
            "fecha_calculo": entry.get("fecha_calculo"),
        },
        "factor_cientifico": {
            "factor_id": entry.get("factor_id"),
            "version_factor_id": entry.get("version_factor_id"),
            "standard": entry.get("standard"),
            "boundary": entry.get("boundary"),
            "dataset_version": entry.get("dataset_version"),
            "calidad": entry.get("quality"),
        },
        "fuente_normativa": None,
        "interpretacion": None,
    }
