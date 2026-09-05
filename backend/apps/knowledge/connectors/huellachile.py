import os
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .base import ConnectorBatch, ConnectorRecord, EnvironmentalConnector
from ..downloads import download_external_file, remove_download, validate_external_url

HUELLACHILE_BASE_URL="https://huellachile.mma.gob.cl"
HUELLACHILE_DISCOVERY_URL=f"{HUELLACHILE_BASE_URL}/recursos-material-de-apoyo/"
HUELLACHILE_HOSTS={"huellachile.mma.gob.cl"}


class LinkParser(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.href=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="a": self.href=dict(attrs).get("href");self.text=[]
    def handle_data(self,data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.href is not None:
            self.links.append((" ".join("".join(self.text).split()),self.href));self.href=None;self.text=[]


def _fold(value): return "".join(character for character in unicodedata.normalize("NFKD",value).lower() if not unicodedata.combining(character))
def _filename_version(filename):
    match=re.search(r"(?:^|[_-])(v\d+)(?:[_-]|\.)",filename,re.I);return match.group(1).lower() if match else ""


def discover_factor_publications(html):
    parser=LinkParser();parser.feed(html);records=[]
    for title,href in parser.links:
        folded=_fold(title)
        if "base de datos factores de emision" not in folded: continue
        url=urljoin(HUELLACHILE_DISCOVERY_URL,href);validate_external_url(url,HUELLACHILE_HOSTS)
        filename=Path(urlparse(url).path).name
        if not filename.lower().endswith(".xlsx"): continue
        if "ambito comunal" in folded:
            scope="comunal";year=None;edition="completa";identity="huellachile:factores-emision:comunal"
        else:
            year_match=re.search(r"\b(20\d{2})\b",title);edition="completa" if "version completa" in folded else "resumen" if "version resumen" in folded else None
            if not year_match or not edition: continue
            scope="organizaciones_eventos";year=int(year_match.group(1));identity=f"huellachile:factores-emision:organizaciones-eventos:{year}:{edition}"
        payload={"scope":scope,"year":year,"edition":edition,"title":title,"url":url,"filename":filename,"filename_version":_filename_version(filename),"logical_resource_id":identity.replace(":","-")}
        records.append(ConnectorRecord(external_id=identity,kind="huellachile_emission_factor_dataset",canonical_key=identity,title=title,source_url=url,payload=payload))
    if not records: raise ValueError("La página HuellaChile no contiene publicaciones reconocibles de factores de emisión.")
    return records


class HuellaChileConnector(EnvironmentalConnector):
    def fetch(self,sync_state):
        download=download_external_file(HUELLACHILE_DISCOVERY_URL,HUELLACHILE_HOSTS,"text/html",{"text/html"},max_bytes=2*1024*1024,suffix=".html")
        try: html=Path(download.path).read_text(encoding="utf-8")
        finally: remove_download(download)
        return ConnectorBatch(records=discover_factor_publications(html),etag=download.etag,last_modified=download.last_modified,authoritative_full_snapshot=False,metadata={"discovery_url":HUELLACHILE_DISCOVERY_URL})
