import hashlib,json,re
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .connectors.registry import connector_for
from .models import EnvironmentalSource,ExternalRecord,ExternalSnapshot,SourceState,SyncRun

MAX_PAYLOAD_BYTES=262144; MAX_TEXT_CHARS=65536; SECRET=re.compile(r"authorization|token|api.?key|cookie|secret",re.I)
def sanitize(value):
    if isinstance(value,dict): return {k:sanitize(v) for k,v in value.items() if not SECRET.search(str(k))}
    if isinstance(value,list): return [sanitize(v) for v in value]
    return value
def canonical_content(record):
    payload=sanitize(record.payload)
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode() if payload is not None else record.text.encode()
    if len(encoded)>MAX_PAYLOAD_BYTES or len(record.text)>MAX_TEXT_CHARS: raise ValidationError("El contenido externo excede el limite de persistencia.")
    return payload,hashlib.sha256(encoded).hexdigest()
def sanitized_error(exc):
    message=re.sub(r"(?i)bearer\s+\S+","Bearer [redactado]",str(exc))
    message=re.sub(r"(?i)(token|api.?key|authorization|cookie|secret)(\s*[:=]\s*|\s+)\S+",r"\1=[redactado]",message)
    return message[:1000]
def source_freshness(source, now=None):
    state=SourceState.objects.get(source=source); now=now or timezone.now()
    if not state.last_successful_sync_at: return "nunca_sincronizado" if state.estado!="error" else "error_con_ultima_version_disponible"
    age=now-state.last_successful_sync_at; limit=timedelta(hours=source.stale_after_hours)
    if state.estado=="error": return "error_con_ultima_version_disponible"
    if age>limit:return "desactualizado"
    if age>limit*0.8:return "proximo_a_vencer"
    return "actualizado"
def _begin(source,trigger):
    with transaction.atomic():
        state=SourceState.objects.select_for_update().get(source=source)
        if state.estado==SourceState.Status.SYNCING: raise ValidationError("La fuente ya se esta sincronizando.")
        now=timezone.now(); state.estado=SourceState.Status.SYNCING;state.last_attempt_at=now;state.last_error="";state.save()
        return SyncRun.objects.create(source=source,trigger=trigger,started_at=now,initial_cursor=state.cursor)
def _fail(source,run,exc):
    message=sanitized_error(exc)
    with transaction.atomic():
        state=SourceState.objects.select_for_update().get(source=source);state.estado="error";state.last_error=message;state.save()
        SyncRun.objects.filter(pk=run.pk).update(finished_at=timezone.now(),estado="error",errors=1,message=message)
    return SyncRun.objects.get(pk=run.pk)
def sync_environmental_source(source,trigger="manual"):
    run=_begin(source,trigger); state=source.sync_state
    try: batch=connector_for(source).fetch(state)
    except Exception as exc: return _fail(source,run,exc)
    try: prepared=[(item,*canonical_content(item)) for item in batch.records]
    except Exception as exc: return _fail(source,run,exc)
    now=timezone.now(); created=modified=unchanged=disappeared=0; seen=[]
    with transaction.atomic():
        for item,payload,digest in prepared:
            seen.append(item.external_id)
            current=ExternalRecord.objects.filter(source=source,external_id=item.external_id).first()
            snapshot=ExternalSnapshot.objects.filter(source=source,external_id=item.external_id,content_hash=digest).first()
            if snapshot: unchanged+=1
            else:
                snapshot=ExternalSnapshot.objects.create(source=source,sync_run=run,external_id=item.external_id,record_kind=item.kind,source_url=item.source_url,published_at=item.published_at,upstream_updated_at=item.upstream_updated_at,retrieved_at=now,content_hash=digest,raw_payload=payload,raw_text=item.text,metadata=sanitize(item.metadata),content_type=item.content_type)
                modified+=bool(current);created+=not bool(current)
            if not current: ExternalRecord.objects.create(source=source,external_id=item.external_id,kind=item.kind,canonical_key=item.canonical_key,title=item.title,source_url=item.source_url,current_snapshot=snapshot,published_at=item.published_at,upstream_updated_at=item.upstream_updated_at,metadata=sanitize(item.metadata),first_seen_at=now,last_seen_at=now)
            elif current.current_snapshot_id!=snapshot.id: current.current_snapshot=snapshot;current.title=item.title;current.upstream_updated_at=item.upstream_updated_at;current.last_seen_at=now;current.estado=ExternalRecord.Status.ACTIVE;current.save()
            else: ExternalRecord.objects.filter(pk=current.pk).update(last_seen_at=now,estado=ExternalRecord.Status.ACTIVE)
        if batch.authoritative_full_snapshot:
            missing=ExternalRecord.objects.filter(source=source).exclude(external_id__in=seen).exclude(estado=ExternalRecord.Status.MISSING)
            disappeared=missing.count();missing.update(estado=ExternalRecord.Status.MISSING)
        upstream_dates=[item.upstream_updated_at for item in batch.records if item.upstream_updated_at]
        state=SourceState.objects.select_for_update().get(source=source);state.estado="actualizada" if created or modified or disappeared else "sin_cambios";state.last_successful_sync_at=now;state.retrieved_at=now;state.upstream_updated_at=max(upstream_dates) if upstream_dates else state.upstream_updated_at;state.upstream_version=batch.upstream_version;state.cursor=batch.cursor;state.etag=batch.etag;state.last_modified=batch.last_modified;state.metadata=sanitize(batch.metadata);state.last_error="";state.save()
        SyncRun.objects.filter(pk=run.pk).update(finished_at=now,estado=state.estado,upstream_version=batch.upstream_version,received=len(batch.records),created=created,modified=modified,unchanged=unchanged,disappeared=disappeared,final_cursor=batch.cursor,metadata=sanitize(batch.metadata))
    return SyncRun.objects.get(pk=run.pk)
