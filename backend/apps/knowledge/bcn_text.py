import hashlib, re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from defusedxml import ElementTree as ET
from django.db import models, transaction
from django.utils import timezone
from .downloads import download_external_file, remove_download
from .models import (
    BcnLegalArticleFact,
    BcnLegalNormFact,
    BcnLegalNormSubscription,
    BcnLegalTextParse,
    BcnLegalTextSourceDocument,
    ExternalFileArtifact,
)

BCN_LEGAL_XML_PARSER_VERSION = "1"
BCN_XML_HOSTS = {"www.leychile.cl"}
BCN_XML_TYPES = {"text/xml", "application/xml"}
SPACE = re.compile(r"\s+")


@dataclass
class TextSyncResult:
    normas: int = 0
    downloaded: int = 0
    imported: int = 0
    unchanged: int = 0
    failed: int = 0
    articles: int = 0


def get_current_bcn_legal_text(fact):
    """Resolve only the parser declared current for current legal knowledge."""
    if not fact.snapshot.current_for.filter(current_snapshot=fact.snapshot).exists():
        raise BcnLegalTextParse.DoesNotExist
    artifact = ExternalFileArtifact.objects.get(
        parent_record__current_snapshot=fact.snapshot,
        is_current=True,
        metadata__version_uri=fact.latest_version_uri,
    )
    parse = artifact.bcn_legal_source_document.parses.get(
        parser_version=BCN_LEGAL_XML_PARSER_VERSION,
        status=BcnLegalTextParse.Status.SUCCESS,
    )
    return artifact, parse


def _https(url):
    parsed = urlparse(url)
    if parsed.hostname not in BCN_XML_HOSTS or parsed.username or parsed.password:
        raise ValueError("URL XML BCN no permitida.")
    return urlunparse(
        ("https", parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _text(node):
    return SPACE.sub(" ", " ".join(node.itertext())).strip()


def parse_bcn_legal_xml(raw):
    root = ET.fromstring(raw)
    if _local(root.tag) != "Norma":
        raise ValueError("Raíz XML BCN inesperada.")
    articles = []

    def walk(node, path):
        children = list(node)
        for index, child in enumerate(children, 1):
            child_path = f"{path}/{_local(child.tag)}[{index}]"
            if _local(child.tag) == "EstructuraFuncional" and child.attrib.get(
                "tipoParte", ""
            ).casefold() in {"artículo", "articulo"}:
                text_node = next((x for x in child if _local(x.tag) == "Texto"), None)
                metadata_node = next(
                    (x for x in child if _local(x.tag) == "Metadatos"), None
                )
                text = _text(text_node) if text_node is not None else ""
                if not text:
                    raise ValueError("Artículo BCN vacío.")
                number = ""
                heading = ""
                if metadata_node is not None:
                    for item in metadata_node:
                        if _local(item.tag) == "NombreParte":
                            number = _text(item)
                        if (
                            _local(item.tag) == "TituloParte"
                            and item.attrib.get("presente") == "si"
                        ):
                            heading = _text(item)
                key = (
                    f"idParte:{child.attrib['idParte']}"
                    if child.attrib.get("idParte")
                    else child_path
                )
                articles.append(
                    {
                        "article_key": key,
                        "article_number": number,
                        "article_label": text.split(".-", 1)[0].strip(),
                        "heading": heading,
                        "source_path": child_path,
                        "text_plain": text,
                        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
                        "raw_fragment": ET.tostring(child, encoding="unicode"),
                        "metadata": {"attributes": dict(child.attrib)},
                    }
                )
            walk(child, child_path)

    walk(root, f"/{_local(root.tag)}[1]")
    if not articles:
        raise ValueError("XML BCN sin artículos reconocibles.")
    if len({a["article_key"] for a in articles}) != len(articles):
        raise ValueError("Identidad de artículo BCN duplicada.")
    return articles


def _publish_artifact(artifact):
    with transaction.atomic():
        siblings = ExternalFileArtifact.objects.select_for_update().filter(
            source=artifact.source,
            external_resource_id=artifact.external_resource_id,
        )
        siblings.filter(is_current=True).exclude(pk=artifact.pk).update(is_current=False)
        if not artifact.is_current:
            artifact.is_current = True
            artifact.save(update_fields=["is_current"])


def _parse_and_publish(document, artifact, result):
    existing_parse = document.parses.filter(
        parser_version=BCN_LEGAL_XML_PARSER_VERSION
    ).first()
    if existing_parse:
        if existing_parse.status != BcnLegalTextParse.Status.SUCCESS:
            raise ValueError(
                "El artifact ya tiene un parse fallido para la version actual; "
                "incremente BCN_LEGAL_XML_PARSER_VERSION para reprocesarlo."
            )
        _publish_artifact(artifact)
        result.unchanged += 1
        return

    raw = bytes(document.raw_bytes)
    try:
        articles = parse_bcn_legal_xml(raw)
    except Exception as exc:
        BcnLegalTextParse.objects.create(
            source_document=document,
            parser_version=BCN_LEGAL_XML_PARSER_VERSION,
            status=BcnLegalTextParse.Status.ERROR,
            parsed_at=timezone.now(),
            error_message=str(exc),
        )
        raise
    with transaction.atomic():
        document = BcnLegalTextSourceDocument.objects.select_for_update().get(
            pk=document.pk
        )
        if document.parses.filter(
            parser_version=BCN_LEGAL_XML_PARSER_VERSION
        ).exists():
            raise ValueError("El parser actual ya fue ejecutado para este artifact.")
        parse = BcnLegalTextParse.objects.create(
            source_document=document,
            parser_version=BCN_LEGAL_XML_PARSER_VERSION,
            status=BcnLegalTextParse.Status.SUCCESS,
            parsed_at=timezone.now(),
            article_count=len(articles),
            metadata={"root_tag": "Norma"},
        )
        BcnLegalArticleFact.objects.bulk_create(
            [
                BcnLegalArticleFact(parse=parse, order_index=i, **article)
                for i, article in enumerate(articles, 1)
            ]
        )
        siblings = ExternalFileArtifact.objects.select_for_update().filter(
            source=artifact.source,
            external_resource_id=artifact.external_resource_id,
        )
        siblings.filter(is_current=True).exclude(pk=artifact.pk).update(is_current=False)
        if not artifact.is_current:
            artifact.is_current = True
            artifact.save(update_fields=["is_current"])
    result.imported += 1
    result.articles += len(articles)


def _process(fact, result):
    version = fact.versions.get(is_latest=True)
    if not version.xml_document_url:
        raise ValueError("Versión BCN latest sin xml_document_url.")
    identity = (
        "bcn-legal-text:" + hashlib.sha256(version.version_uri.encode()).hexdigest()
    )
    download = None
    try:
        download = download_external_file(
            _https(version.xml_document_url),
            BCN_XML_HOSTS,
            "application/xml,text/xml",
            BCN_XML_TYPES,
            max_bytes=10 * 1024 * 1024,
            suffix=".xml",
        )
        result.downloaded += 1
        with transaction.atomic():
            artifacts = ExternalFileArtifact.objects.select_for_update().filter(
                source=fact.snapshot.source, external_resource_id=identity
            )
            artifact = artifacts.filter(content_sha256=download.sha256).first()
            if artifact:
                document = artifact.bcn_legal_source_document
            else:
                with open(download.path, "rb") as source_file:
                    raw = source_file.read()
                declaration = re.match(
                    rb"\s*<\?xml[^>]*encoding=[\"']([^\"']+)", raw, re.I
                )
                detected_encoding = (
                    declaration.group(1).decode("ascii") if declaration else "UTF-8"
                )
                artifact = ExternalFileArtifact.objects.create(
                    source=fact.snapshot.source,
                    parent_record=fact.snapshot.current_for.get(),
                    external_resource_id=identity,
                    name=f"BCN {fact.norm_type_name} {fact.number} XML",
                    source_url=download.final_url,
                    format="XML",
                    content_type=download.content_type,
                    byte_size=download.byte_size,
                    retrieved_at=timezone.now(),
                    content_sha256=download.sha256,
                    metadata={
                        "norm_uri": fact.norm_uri,
                        "version_uri": version.version_uri,
                        "version_date": str(version.version_date or ""),
                        "norm_number": fact.number,
                        "norm_type": fact.norm_type_name,
                        "xml_document_url": version.xml_document_url,
                        "etag": download.etag,
                        "last_modified": download.last_modified,
                    },
                    is_current=False,
                    version=(artifacts.order_by("-version").values_list("version", flat=True).first() or 0) + 1,
                )
                document = BcnLegalTextSourceDocument.objects.create(
                    artifact=artifact,
                    raw_bytes=raw,
                    detected_encoding=detected_encoding,
                    byte_size=len(raw),
                )
        _parse_and_publish(document, artifact, result)
    finally:
        remove_download(download)


def sync_bcn_legal_texts():
    active_keys = [
        f"{norm_type.upper()}:{number.upper()}"
        for norm_type, number in BcnLegalNormSubscription.objects.filter(
            source__codigo="bcn-leychile", active=True
        ).values_list("norm_type", "number")
    ]
    facts = (
        BcnLegalNormFact.objects.filter(
            snapshot__current_for__current_snapshot=models.F("snapshot"),
            snapshot__source__codigo="bcn-leychile",
            snapshot__current_for__canonical_key__in=active_keys,
        )
        .distinct()
        .prefetch_related("versions")
    )
    result = TextSyncResult(normas=facts.count())
    for fact in facts:
        try:
            _process(fact, result)
        except Exception:
            result.failed += 1
    return result
