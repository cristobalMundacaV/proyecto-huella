import hashlib
import re
from dataclasses import dataclass

from django.db import models, transaction
from django.utils import timezone

from .bcn_text import get_current_bcn_legal_text
from .models import (
    BcnLegalNormFact,
    BcnLegalNormSubscription,
    BcnLegalObligationCandidate,
    BcnLegalObligationExtractionRun,
)

BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION = "rules-1"
BCN_LEGAL_OBLIGATION_EXTRACTOR_METHOD = "deterministic_rules"

PROHIBITION = re.compile(
    r"\b(?:se\s+proh[ií]be|qued(?:a|an)\s+prohibid(?:o|os|a|as)|no\s+podr[aá](?:n)?|no\s+deber[aá](?:n)?)\b",
    re.IGNORECASE,
)
OBLIGATION = re.compile(
    r"\b(?:deber[aá](?:n)?|debe(?:n)?|estar[aá](?:n)?\s+obligad(?:o|os|a|as)\s+a|qued(?:a|an)\s+obligad(?:o|os|a|as))\b",
    re.IGNORECASE,
)
BOUNDARY = re.compile(r"[.;:]")


@dataclass
class ObligationExtractionResult:
    norms: int = 0
    articles: int = 0
    processed: int = 0
    unchanged: int = 0
    articles_with_candidates: int = 0
    candidates: int = 0
    failed: int = 0


def _clause_span(text, start, end):
    previous = max((match.end() for match in BOUNDARY.finditer(text, 0, start)), default=0)
    following = BOUNDARY.search(text, end)
    limit = following.start() if following else len(text)
    while previous < limit and text[previous].isspace():
        previous += 1
    while limit > previous and text[limit - 1].isspace():
        limit -= 1
    return previous, limit


def extract_obligation_candidates(article):
    text = article.text_plain
    matches = [(match, BcnLegalObligationCandidate.Modality.PROHIBITION) for match in PROHIBITION.finditer(text)]
    prohibited_ranges = [(match.start(), match.end()) for match, _ in matches]
    for match in OBLIGATION.finditer(text):
        if any(start <= match.start() < end for start, end in prohibited_ranges):
            continue
        prefix = text[max(0, match.start() - 3):match.start()].casefold()
        if prefix.endswith("no "):
            continue
        matches.append((match, BcnLegalObligationCandidate.Modality.OBLIGATION))
    clauses = {}
    for match, modality in sorted(matches, key=lambda item: item[0].start()):
        source_start, source_end = _clause_span(text, match.start(), match.end())
        key = (modality, source_start, source_end)
        clauses.setdefault(key, (match, modality))
    candidates = []
    for order, ((modality, source_start, source_end), (match, _)) in enumerate(clauses.items(), 1):
        quote = text[source_start:source_end]
        material = f"{BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION}|{article.text_hash}|{modality}|{source_start}|{source_end}"
        candidates.append({
            "candidate_key": hashlib.sha256(material.encode()).hexdigest(),
            "order_index": order,
            "modality_hint": modality,
            "trigger_text": text[match.start():match.end()],
            "trigger_start": match.start(),
            "trigger_end": match.end(),
            "source_quote": quote,
            "source_start": source_start,
            "source_end": source_end,
            "source_quote_hash": hashlib.sha256(quote.encode()).hexdigest(),
            "metadata": {"rule": "explicit_deontic_trigger"},
        })
    return candidates


def current_bcn_norm_facts():
    active_keys = [
        f"{kind.upper()}:{number.upper()}"
        for kind, number in BcnLegalNormSubscription.objects.filter(
            source__codigo="bcn-leychile", active=True
        ).values_list("norm_type", "number")
    ]
    return BcnLegalNormFact.objects.filter(
        snapshot__current_for__current_snapshot=models.F("snapshot"),
        snapshot__current_for__canonical_key__in=active_keys,
        snapshot__source__codigo="bcn-leychile",
    ).distinct()


def extract_bcn_legal_obligation_candidates():
    result = ObligationExtractionResult()
    for fact in current_bcn_norm_facts():
        result.norms += 1
        try:
            _, parse = get_current_bcn_legal_text(fact)
        except Exception:
            result.failed += 1
            continue
        for article in parse.articles.all():
            result.articles += 1
            existing = article.obligation_extraction_runs.filter(
                extractor_version=BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION
            ).first()
            if existing:
                if existing.status == BcnLegalObligationExtractionRun.Status.SUCCESS and existing.source_text_hash == article.text_hash:
                    result.unchanged += 1
                else:
                    result.failed += 1
                continue
            try:
                candidates = extract_obligation_candidates(article)
                with transaction.atomic():
                    run = BcnLegalObligationExtractionRun.objects.create(
                        article=article,
                        extractor_version=BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION,
                        extractor_method=BCN_LEGAL_OBLIGATION_EXTRACTOR_METHOD,
                        status=BcnLegalObligationExtractionRun.Status.SUCCESS,
                        executed_at=timezone.now(),
                        source_text_hash=article.text_hash,
                        candidate_count=len(candidates),
                    )
                    for candidate in candidates:
                        BcnLegalObligationCandidate.objects.create(
                            extraction_run=run, **candidate
                        )
                result.processed += 1
                result.candidates += len(candidates)
                result.articles_with_candidates += bool(candidates)
            except Exception as exc:
                BcnLegalObligationExtractionRun.objects.create(
                    article=article,
                    extractor_version=BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION,
                    extractor_method=BCN_LEGAL_OBLIGATION_EXTRACTOR_METHOD,
                    status=BcnLegalObligationExtractionRun.Status.ERROR,
                    executed_at=timezone.now(),
                    source_text_hash=article.text_hash,
                    error_message=str(exc),
                )
                result.failed += 1
    return result
