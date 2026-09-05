import io
import json
import re
import zipfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from .connectors.huellachile import HUELLACHILE_DISCOVERY_URL,discover_factor_publications
from .huellachile_sync import sync_huellachile_factors
from .models import EnvironmentalSource,ExternalFileArtifact,ExternalRecord,ExternalSnapshot,HuellaChileEmissionFactorFact
from .services import sync_environmental_source
from .tabular import HuellaChileEmissionFactorParser


class DownloadResponse:
    def __init__(self,content,url,content_type): self.stream=io.BytesIO(content);self.url=url;self.headers={"Content-Length":str(len(content)),"Content-Type":content_type}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size=-1): return self.stream.read(size)
    def geturl(self): return self.url


def html(url_2025="https://huellachile.mma.gob.cl/files/factores-2025_v2_completa.xlsx",reverse=False):
    links=[("Base de datos factores de emisión 2024 para organizaciones y eventos (Versión completa)","/files/factores-2024-completa.xlsx"),("Base de datos factores de emisión 2025 para organizaciones y eventos (Versión resumen)","/files/factores-2025-resumen.xlsx"),("Base de datos factores de emisión 2025 para organizaciones y eventos (Versión completa)",url_2025),("Base de datos factores de emisión para ámbito comunal","/files/factores-comunal.xlsx")]
    if reverse: links.reverse()
    return ("<html><body>"+"".join(f'<a href="{url}">{title}</a>' for title,url in links)+"</body></html>").encode()


def workbook_bytes(value=2.5,formula=False,unexpected=False):
    workbook=Workbook();summary=workbook.active;summary.title="RESUMEN";aux=workbook.create_sheet("AUXILIAR");aux.sheet_state="hidden"
    headers=list(HuellaChileEmissionFactorParser.HEADERS);summary.append([])
    for _ in range(6): summary.append([])
    summary.append([None,*(headers if not unexpected else ["Otro",*headers[1:]])])
    summary.append([None,"Emisiones directas","1.1 Combustión estacionaria","Caldera/Generador/General","Petróleo 2 (Diésel)","-","litros",("=1+1" if formula else value),"kgCO2e/litros","IPCC 2006","CNE BNE 2024","-"])
    output=io.BytesIO();workbook.save(output);content=output.getvalue()
    if formula:
        source=zipfile.ZipFile(io.BytesIO(content));target=io.BytesIO()
        with zipfile.ZipFile(target,"w") as destination:
            for item in source.infolist():
                data=source.read(item.filename)
                if item.filename=="xl/worksheets/sheet1.xml": data=re.sub(br'(<c r="H9"[^>]*><f>[^<]+</f><v>)[^<]*(</v>)',br'\g<1>2.5\2',data)
                destination.writestr(item,data)
        source.close();content=target.getvalue()
    return content


class HuellaChileKnowledgeTests(TestCase):
    def setUp(self): self.source=EnvironmentalSource.objects.get(codigo="huellachile")

    def test_discovery_distingue_year_edicion_comunal_y_orden(self):
        first=discover_factor_publications(html().decode());second=discover_factor_publications(html(reverse=True).decode())
        self.assertEqual({record.external_id for record in first},{record.external_id for record in second})
        self.assertIn("huellachile:factores-emision:organizaciones-eventos:2025:completa",{record.external_id for record in first})
        self.assertIn("huellachile:factores-emision:organizaciones-eventos:2025:resumen",{record.external_id for record in first})
        self.assertIn("huellachile:factores-emision:organizaciones-eventos:2024:completa",{record.external_id for record in first})
        self.assertIn("huellachile:factores-emision:comunal",{record.external_id for record in first})

    def test_link_off_domain_y_html_inesperado_se_rechazan(self):
        bad='<a href="https://evil.example/f.xlsx">Base de datos factores de emisión 2025 para organizaciones y eventos (Versión completa)</a>'
        with self.assertRaisesRegex(ValueError,"no permitida"): discover_factor_publications(bad)
        with self.assertRaisesRegex(ValueError,"publicaciones reconocibles"): discover_factor_publications("<html></html>")

    @patch("apps.knowledge.downloads._open_url")
    def test_href_cambia_snapshot_no_identidad_logica(self,mocked):
        mocked.side_effect=[DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(html("https://huellachile.mma.gob.cl/files/v3.xlsx"),HUELLACHILE_DISCOVERY_URL,"text/html")]
        sync_environmental_source(self.source);sync_environmental_source(self.source)
        record=ExternalRecord.objects.get(source=self.source,external_id="huellachile:factores-emision:organizaciones-eventos:2025:completa")
        self.assertEqual(self.source.records.filter(external_id=record.external_id).count(),1);self.assertEqual(ExternalSnapshot.objects.filter(source=self.source,external_id=record.external_id).count(),2);self.assertTrue(record.source_url.endswith("v3.xlsx"))

    @patch("apps.knowledge.downloads._open_url")
    def test_pagina_inesperada_no_elimina_anterior(self,mocked):
        mocked.side_effect=[DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(b"<html></html>",HUELLACHILE_DISCOVERY_URL,"text/html")]
        sync_environmental_source(self.source);run=sync_environmental_source(self.source)
        self.assertEqual(run.estado,"error");self.assertFalse(self.source.records.filter(estado="no_observado").exists())

    @patch("apps.knowledge.downloads._open_url")
    def test_sync_end_to_end_formula_cached_publisher_y_idempotencia(self,mocked):
        book=workbook_bytes(formula=True);file_url="https://huellachile.mma.gob.cl/files/factores-2025_v2_completa.xlsx"
        mocked.side_effect=[DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(book,file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(book,file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")]
        first=sync_huellachile_factors();second=sync_huellachile_factors();fact=HuellaChileEmissionFactorFact.objects.get()
        self.assertEqual((first.estado,first.factors_imported,second.estado,second.factors_imported),("importado",1,"sin_cambios",0));self.assertEqual(ExternalFileArtifact.objects.count(),1)
        self.assertEqual(str(fact.factor_value),"2.500000000000000");self.assertEqual(fact.formula_original,"=1+1");self.assertTrue(fact.cached_value_available);self.assertEqual(fact.publisher,"Programa HuellaChile / Ministerio del Medio Ambiente");self.assertEqual(fact.technical_source_1,"IPCC 2006");self.assertIn("formula",fact.raw_row["Factor de emisión"])

    @patch("apps.knowledge.downloads._open_url")
    def test_href_nuevo_con_misma_sha_no_duplica_facts(self,mocked):
        book=workbook_bytes();first_url="https://huellachile.mma.gob.cl/files/factores-2025_v2_completa.xlsx";second_url="https://huellachile.mma.gob.cl/files/factores-2025_v3_completa.xlsx"
        mocked.side_effect=[DownloadResponse(html(first_url),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(book,first_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),DownloadResponse(html(second_url),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(book,second_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")]
        sync_huellachile_factors();second=sync_huellachile_factors();self.assertEqual((second.estado,second.factors_imported,ExternalFileArtifact.objects.count(),HuellaChileEmissionFactorFact.objects.count()),("sin_cambios",0,1,1));self.assertEqual(ExternalRecord.objects.get(source=self.source,external_id="huellachile:factores-emision:organizaciones-eventos:2025:completa").source_url,second_url)

    @patch("apps.knowledge.downloads._open_url")
    def test_nueva_sha_versiona_y_fallo_parser_preserva_current(self,mocked):
        file_url="https://huellachile.mma.gob.cl/files/factores-2025_v2_completa.xlsx"
        mocked.side_effect=[DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(workbook_bytes(2.5),file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(workbook_bytes(3.0),file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(workbook_bytes(unexpected=True),file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")]
        first=sync_huellachile_factors();second=sync_huellachile_factors();first.artifact.refresh_from_db();self.assertFalse(first.artifact.is_current);self.assertTrue(second.artifact.is_current);self.assertEqual(HuellaChileEmissionFactorFact.objects.count(),2)
        with self.assertRaisesRegex(ValueError,"esquema RESUMEN"): sync_huellachile_factors()
        second.artifact.refresh_from_db();self.assertTrue(second.artifact.is_current);self.assertEqual(ExternalFileArtifact.objects.count(),2)

    @patch("apps.knowledge.downloads._open_url")
    def test_api_current_paginacion_filtros_y_permisos(self,mocked):
        file_url="https://huellachile.mma.gob.cl/files/factores-2025_v2_completa.xlsx";mocked.side_effect=[DownloadResponse(html(),HUELLACHILE_DISCOVERY_URL,"text/html"),DownloadResponse(workbook_bytes(),file_url,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")];sync_huellachile_factors()
        client=APIClient();self.assertIn(client.get("/api/knowledge/huellachile/emission-factors/").status_code,(401,403));client.force_authenticate(User.objects.create_user("hc-user"));data=client.get("/api/knowledge/huellachile/emission-factors/?dataset_year=2025&alcance=Emisiones%20directas&page_size=1").data;self.assertEqual((data["count"],len(data["results"])),(1,1));metadata=client.get("/api/knowledge/huellachile/emission-factors/metadata/").data;self.assertEqual((metadata["year"],metadata["fact_count"],metadata["filename_version"]),(2025,1,"v2"))

    @patch("apps.knowledge.downloads._open_url")
    def test_redirect_externo_content_type_y_headers_sin_auth_cookie(self,mocked):
        mocked.return_value=DownloadResponse(html(),"https://evil.example/page","text/html")
        run=sync_environmental_source(self.source);self.assertEqual(run.estado,"error")
        request=mocked.call_args.args[0];self.assertIsNone(request.get_header("Authorization"));self.assertIsNone(request.get_header("Cookie"))

    def test_bootstrap_huellachile_real_no_pisa_divergencia(self):
        self.assertEqual((self.source.connector_key,self.source.base_url),("huellachile_web","https://huellachile.mma.gob.cl"));self.source.connector_key="local-hc";self.source.save();from .bootstrap import ensure_environmental_source_registry;ensure_environmental_source_registry();self.source.refresh_from_db();self.assertEqual(self.source.connector_key,"local-hc")
