"""Incremental per-identity hydration. Observations commit before atomic facts.

PostgreSQL session advisory locks serialize downloads as well as publication;
they are released by PostgreSQL on worker disconnect, including hard crashes.
"""
import base64
import hashlib
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import connection, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .bootstrap import OKOBAUDAT_TERMS
from .connectors.okobaudat_detail import DetailError, UpstreamDeferred, dataset_url, fetch_detail_bytes, parse_profile
from .models import (EnvironmentalSource, ExternalSnapshot, SyncRun, OekobaudatProcessFact,
                     OekobaudatEnvironmentalProfileFact, OekobaudatEnvironmentalIndicatorFact)

_materializing = ContextVar("okobaudat_materializing", default=False)
_local_lock = threading.Lock()


def materialization_allowed():
    return _materializing.get()


@contextmanager
def identity_lock(identity):
    key = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "big", signed=True)
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [key])
            acquired = cursor.fetchone()[0]
        try:
            yield acquired
        finally:
            if acquired:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [key])
    else:
        # Development SQLite only; command requires PostgreSQL for multiple workers.
        acquired = _local_lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                _local_lock.release()


def snapshot_bytes(snapshot):
    try:
        body = base64.b64decode(snapshot.raw_payload["bytes_base64"], validate=True)
    except (KeyError, TypeError, ValueError):
        raise DetailError("Snapshot de detalle incompatible.") from None
    if hashlib.sha256(body).hexdigest() != snapshot.content_hash:
        raise DetailError("Hash del snapshot incompatible.")
    return body


def hydrate_process(process, run, *, delay=1.0, refetch_reason=""):
    identity = f"{process.process_uuid}:{process.dataset_version}"
    result = {"status": "skipped", "downloaded": 0, "indicators": 0}
    with identity_lock(identity) as acquired:
        if not acquired:
            return result
        if OekobaudatEnvironmentalProfileFact.objects.filter(process_uuid=process.process_uuid, dataset_version=process.dataset_version).exists():
            return {**result, "status": "already_hydrated"}

        def observe(kind, uuid, version, parent_hash=""):
            external_id = f"okobaudat:detail:{identity}" if kind == "processes" else f"okobaudat:detail-ref:{identity}:{parent_hash}:{kind}:{uuid}:{version or 'unversioned'}"
            existing = ExternalSnapshot.objects.filter(source=run.source, external_id=external_id).order_by("-retrieved_at", "-id").first()
            if existing and not refetch_reason:
                return existing
            url = dataset_url(kind, uuid, version)
            body = fetch_detail_bytes(url)
            result["downloaded"] += int(kind == "processes")
            snapshot, _ = ExternalSnapshot.objects.get_or_create(
                source=run.source, external_id=external_id, content_hash=hashlib.sha256(body).hexdigest(),
                defaults={"sync_run": run, "record_kind": "okobaudat_process_detail" if kind == "processes" else "okobaudat_detail_reference",
                          "source_url": url, "retrieved_at": timezone.now(), "content_type": "application/xml",
                          "raw_payload": {"bytes_base64": base64.b64encode(body).decode("ascii")},
                          "metadata": {"process_uuid": str(process.process_uuid), "dataset_version": process.dataset_version,
                                       "requested_uuid": uuid, "requested_version": version, "resource_kind": kind,
                                       "refetch_reason": refetch_reason, "contract": "ILCD 1.1 / EPD 2013",
                                       "source_terms": OKOBAUDAT_TERMS}})
            if delay:
                time.sleep(delay)
            return snapshot

        try:
            snapshot = observe("processes", str(process.process_uuid), process.dataset_version)
            dependencies = []

            def resolve(kind, uuid, version):
                observed = observe(kind, uuid, version, snapshot.content_hash)
                dependencies.append(observed)
                return snapshot_bytes(observed)

            parsed = parse_profile(snapshot_bytes(snapshot), str(process.process_uuid), process.dataset_version, resolve)
            if process.compliance_standard_raw != parsed["standard"]:
                raise DetailError("Estandar del catalogo y detalle contradictorio.")
            indicators = parsed.pop("indicators")
            from .connectors.okobaudat_detail import document, text
            provenance = []
            for item in dependencies:
                metadata = item.metadata
                root = document(snapshot_bytes(item), metadata["resource_kind"], metadata["requested_uuid"], metadata["requested_version"])
                provenance.append({"snapshot_id": item.pk, "content_hash": item.content_hash, "source_url": item.source_url,
                                   "retrieved_at": item.retrieved_at.isoformat(), "uuid": metadata["requested_uuid"],
                                   "dataset_version": text(root, ".//c:dataSetVersion"), "requested_version": metadata["requested_version"]})
            token = _materializing.set(True)
            try:
                with transaction.atomic():
                    profile = OekobaudatEnvironmentalProfileFact.objects.create(
                        process=process, snapshot=snapshot, process_uuid=process.process_uuid, dataset_version=process.dataset_version,
                        provenance={"references": provenance, "reference_resolution": "explicit version or first observed official UUID; frozen snapshot"}, **parsed)
                    for row in indicators:
                        OekobaudatEnvironmentalIndicatorFact.objects.create(profile=profile, snapshot=snapshot,
                            process_uuid=process.process_uuid, dataset_version=process.dataset_version, standard=profile.standard, **row)
            finally:
                _materializing.reset(token)
            return {**result, "status": "materialized", "indicators": len(indicators)}
        except Exception as exc:
            # Never persist arbitrary exception text (HTTP URLs, SQL, tokens, XML).
            return {**result, "status": "failed", "deferred": isinstance(exc, UpstreamDeferred),
                    "error": str(exc) if type(exc) in (DetailError, UpstreamDeferred) else "Fallo de materializacion de detalle."}


def hydrate_details(*, process_uuid=None, dataset_version=None, limit=None, batch_size=100, delay=1.0, refetch_reason="", progress=None):
    if batch_size < 1 or (limit is not None and limit < 1) or delay < 0:
        raise ValueError("Parametros de hidratacion invalidos.")
    source = EnvironmentalSource.objects.get(codigo="okobaudat")
    qs = OekobaudatProcessFact.objects.filter(snapshot__source=source)
    if process_uuid:
        qs = qs.filter(process_uuid=process_uuid)
    if dataset_version:
        qs = qs.filter(dataset_version=dataset_version)
    identities = qs.order_by("process_uuid", "dataset_version").values_list("process_uuid", "dataset_version").distinct()
    hydrated = OekobaudatEnvironmentalProfileFact.objects.filter(process_uuid=OuterRef("process_uuid"), dataset_version=OuterRef("dataset_version"))
    candidates = identities.count()
    already = identities.filter(Exists(hydrated)).count()
    identities = identities.filter(~Exists(hydrated))
    pending = candidates - already
    scheduled = min(pending, limit) if limit else pending
    if limit:
        identities = identities[:limit]
    summary = {"candidates": candidates, "already_hydrated": already, "downloaded": 0, "materialized": 0,
               "skipped": max(0, pending - limit) if limit else 0, "failed": 0, "indicators_created": 0}
    run = SyncRun.objects.create(source=source, trigger="manual", started_at=timezone.now(), metadata={"scope": "okobaudat_process_detail", "refetch_reason": refetch_reason})
    interrupted = False
    try:
        for processed, (uuid, version) in enumerate(identities.iterator(chunk_size=batch_size), start=1):
            process = qs.filter(process_uuid=uuid, dataset_version=version).order_by("id").first()
            result = hydrate_process(process, run, delay=delay, refetch_reason=refetch_reason)
            summary[result["status"]] += 1
            summary["downloaded"] += result["downloaded"]
            summary["indicators_created"] += result["indicators"]
            if result.get("deferred"):
                summary["skipped"] += scheduled - processed
            SyncRun.objects.filter(pk=run.pk).update(final_cursor={"process_uuid": str(uuid), "dataset_version": version}, metadata={"scope": "okobaudat_process_detail", **summary}, message=result.get("error", ""))
            if progress:
                progress(str(uuid), version, result)
            if result.get("deferred"):
                break
    except BaseException:
        interrupted = True
        raise
    finally:
        SyncRun.objects.filter(pk=run.pk).update(finished_at=timezone.now(), estado="parcial" if interrupted or summary["failed"] or summary["skipped"] else "actualizada",
            received=summary["downloaded"], created=summary["materialized"], unchanged=summary["already_hydrated"], errors=summary["failed"],
            metadata={"scope": "okobaudat_process_detail", "interrupted": interrupted, "refetch_reason": refetch_reason, **summary})
    return summary
