import hashlib
import json
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook

from .services import sanitize


@dataclass(frozen=True)
class ParsedTabularResource:
    sheets: list
    headers: list
    rows_read: int
    rows: list
    rejected: list


class TabularResourceParser:
    def parse(self, path, **context):
        raise NotImplementedError

    def read_xlsx(self, path):
        if not zipfile.is_zipfile(path):
            raise ValueError("El recurso no es un archivo XLSX válido.")
        try:
            workbook=load_workbook(path,read_only=True,data_only=True)
        except Exception as exc:
            raise ValueError("No fue posible abrir el workbook XLSX.") from exc
        if not workbook.sheetnames:
            raise ValueError("El workbook XLSX no contiene hojas.")
        worksheet=workbook[workbook.sheetnames[0]]
        iterator=worksheet.iter_rows(values_only=True)
        try: headers=[str(value).strip() if value is not None else "" for value in next(iterator)]
        except StopIteration as exc: raise ValueError("El workbook XLSX está vacío.") from exc
        return workbook,worksheet,headers,iterator


class RetcHazardousWasteParser(TabularResourceParser):
    HEADERS=("año","id_vu","id_rol_establecimiento","rol_establecimiento","rut_razon_social","razon_social","ciiu6_id","ciiu6","ciiu4_id","ciiu4","rubro","rubro_id","codigo_unico_territorial","comuna","provincia","region","latitud","longitud","cantidad_kilos","cantidad_toneladas","id_contaminantes","contaminantes","id_peligrosidad","peligrosidad","id_lista_a","lista_a","id_estado_materia","estado_materia")
    INTEGER_FIELDS=("año","id_vu","id_rol_establecimiento","rubro_id","codigo_unico_territorial","id_estado_materia")
    DECIMAL_FIELDS=("cantidad_kilos","cantidad_toneladas")

    def parse(self,path,year,**context):
        workbook,worksheet,headers,iterator=self.read_xlsx(path)
        if tuple(headers)!=self.HEADERS:
            iterator.close();workbook.close();raise ValueError("El esquema XLSX RETC no coincide con el contrato conocido.")
        rows=[];rejected=[];rows_read=0
        try:
            for row_number,values in enumerate(iterator,start=2):
                rows_read+=1
                if all(value is None or str(value).strip()=="" for value in values):
                    rejected.append({"row_number":row_number,"reason":"fila_vacia"});continue
                raw=sanitize({header:value for header,value in zip(headers,values)})
                try: normalized=self._normalize(raw,year)
                except (ValueError,TypeError,InvalidOperation) as exc:
                    rejected.append({"row_number":row_number,"reason":str(exc)});continue
                encoded=json.dumps(raw,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
                rows.append({"source_row_number":row_number,"row_hash":hashlib.sha256(encoded).hexdigest(),"raw_row":raw,**normalized})
        finally: iterator.close();workbook.close()
        return ParsedTabularResource([worksheet.title],headers,rows_read,rows,rejected)

    def _normalize(self,raw,expected_year):
        normalized={}
        for field in self.INTEGER_FIELDS:
            if raw.get(field) is None: raise ValueError(f"campo_obligatorio_ausente:{field}")
            normalized[field if field!="año" else "year"]=int(raw[field])
        if normalized["year"]!=expected_year: raise ValueError("año_fuera_del_recurso")
        for field in self.DECIMAL_FIELDS:
            normalized[field]=Decimal(str(raw[field])) if raw.get(field) is not None else None
        if normalized["cantidad_toneladas"] is None: raise ValueError("campo_obligatorio_ausente:cantidad_toneladas")
        text_fields=("rol_establecimiento","rut_razon_social","razon_social","ciiu6_id","ciiu6","ciiu4_id","ciiu4","rubro","comuna","provincia","region","id_contaminantes","contaminantes","id_peligrosidad","peligrosidad","id_lista_a","lista_a","estado_materia")
        for field in text_fields: normalized[field]="" if raw.get(field) is None else str(raw[field]).strip()
        for field in ("latitud","longitud"): normalized[f"{field}_raw"]="" if raw.get(field) is None else str(raw[field])
        return normalized
