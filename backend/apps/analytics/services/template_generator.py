"""Generador de plantillas XLSX descargables para importacion de datos."""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation


UNIT_TYPES = [
    "Fundo Forestal",
    "Transporte",
    "Aserradero",
    "Acopio",
    "Secado",
    "Administracion",
    "Bodega",
    "Planta Industrial",
]
UNIT_STATUSES = ["activa", "inactiva", "suspendida", "en_mantenimiento"]


def _style_header(ws):
    fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border


def _style_example(ws, row_num):
    fill = PatternFill(start_color="E7F5F2", end_color="E7F5F2", fill_type="solid")
    font = Font(italic=True, size=10)
    for cell in ws[row_num]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _autosize(ws, width=22):
    ws.freeze_panes = "A2"
    for column in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(column)].width = width


def _add_date_comment(ws, column_letter):
    for row in range(2, 200):
        ws[f"{column_letter}{row}"].number_format = "@"
    ws[f"{column_letter}1"].comment = Comment(
        "Formato obligatorio: YYYY-MM-DD. Ejemplo: 2025-03-18.",
        "Carbono Zero",
    )


def _add_list_validation(ws, column_letter, values):
    validation = DataValidation(type="list", formula1=f'"{",".join(values)}"', allow_blank=False)
    ws.add_data_validation(validation)
    validation.add(f"{column_letter}2:{column_letter}500")


def _add_instructions_sheet(workbook):
    ws = workbook.create_sheet("Instrucciones", 0)
    rows = [
        ["PLANTILLA DE IMPORTACION COMPLETA"],
        [""],
        ["Usa las hojas empresa, factores, unidades, lotes y actividades sin cambiar sus nombres."],
        ["Las fechas deben venir como texto en formato YYYY-MM-DD, por ejemplo 2025-03-18."],
        ["Tipos de unidad permitidos: " + ", ".join(UNIT_TYPES) + "."],
        ["Estados de unidad permitidos: " + ", ".join(UNIT_STATUSES) + "."],
        ["Cada lote debe referenciar un ID Unidad existente en la hoja unidades."],
        ["Cada actividad debe referenciar un ID Lote existente y tener un factor compatible por Actividad + Unidad + Fuente + Ano."],
    ]
    for row in rows:
        ws.append(row)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 120


def _add_sheet(workbook, name, headers, examples):
    ws = workbook.create_sheet(name)
    ws.append(headers)
    _style_header(ws)
    for row_number, row in enumerate(examples, start=2):
        ws.append(row)
        _style_example(ws, row_number)
    _autosize(ws)
    return ws


def generate_complete_import_template() -> BytesIO:
    """Genera una plantilla XLSX descargable para importacion completa de empresa."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    _add_instructions_sheet(workbook)

    _add_sheet(
        workbook,
        "empresa",
        [
            "ID Empresa",
            "Nombre",
            "RUT",
            "Region",
            "Comuna",
            "Direccion",
            "Rubro",
            "Email",
            "Telefono",
            "Contacto",
            "Observaciones",
        ],
        [
            [
                "EMP-001",
                "Forestal Demo SpA",
                "77.123.456-8",
                "Los Rios",
                "Valdivia",
                "Ruta T-350 km 12",
                "Forestal y madera",
                "operaciones@forestaldemo.cl",
                "+56 63 245 8890",
                "Camila Rivas",
                "Datos de ejemplo para importacion anual 2025.",
            ]
        ],
    )

    unidades = _add_sheet(
        workbook,
        "unidades",
        ["ID Unidad", "ID Empresa", "Nombre", "Tipo", "Region", "Comuna", "Direccion", "Estado"],
        [
            ["UNI-001", "EMP-001", "Fundo Las Nalcas", "Fundo Forestal", "Los Rios", "Valdivia", "Ruta T-340 km 18", "activa"],
            ["UNI-002", "EMP-001", "Base Transporte Valdivia", "Transporte", "Los Rios", "Valdivia", "Parque Industrial Sur", "activa"],
            ["UNI-003", "EMP-001", "Planta Aserradero Norte", "Aserradero", "Los Rios", "Mariquina", "Camino Industrial km 4", "activa"],
        ],
    )
    _add_list_validation(unidades, "D", UNIT_TYPES)
    _add_list_validation(unidades, "H", UNIT_STATUSES)

    lotes = _add_sheet(
        workbook,
        "lotes",
        ["ID Lote", "ID Unidad", "Fecha", "Especie", "Volumen (m3)", "Origen"],
        [
            ["LOT-2025-001", "UNI-001", "2025-01-04", "Pino Radiata", 184.5, "Rodal 14-B / Sector Quebrada Norte"],
            ["LOT-2025-002", "UNI-003", "2025-01-10", "Pino Radiata", 126.0, "Recepcion patio norte"],
        ],
    )
    _add_date_comment(lotes, "C")

    actividades = _add_sheet(
        workbook,
        "actividades",
        ["ID Actividad", "ID Lote", "ID Unidad", "Actividad", "Cantidad", "Unidad", "Fecha", "Observacion", "Fuente de dato"],
        [
            ["ACT-001", "LOT-2025-001", "UNI-001", "Cosecha mecanizada", 12.5, "hora", "2025-01-04", "Faena sector norte", "Parte diario"],
            ["ACT-002", "LOT-2025-001", "UNI-002", "Transporte a planta", 86.0, "km", "2025-01-05", "Traslado a planta", "Guia despacho"],
            ["ACT-003", "LOT-2025-002", "UNI-003", "Aserrado", 126.0, "m3", "2025-01-10", "Proceso de aserradero", "Registro planta"],
        ],
    )
    _add_date_comment(actividades, "G")

    _add_sheet(
        workbook,
        "factores",
        ["Actividad", "Unidad", "Factor de Emision", "Fuente", "Ano"],
        [
            ["Cosecha mecanizada", "hora", 18.7, "Inventario interno 2025", 2025],
            ["Transporte a planta", "km", 0.95, "DEFRA / IPCC 2025", 2025],
            ["Aserrado", "m3", 6.2, "Inventario energetico planta 2025", 2025],
        ],
    )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
