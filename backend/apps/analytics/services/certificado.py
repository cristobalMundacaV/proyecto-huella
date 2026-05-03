from io import BytesIO

import qrcode
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .carbono import calcular_balance_lote, calcular_carbono_almacenado
from .pasaporte import calcular_pasaporte_lote


def format_number(value, decimals=1):
    return f"{float(value):,.{decimals}f}".replace(",", ".")


def build_qr_image(payload):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def draw_label_value(pdf, x, y, label, value):
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(x, y, label.upper())
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x, y - 13, str(value))


def generar_certificado_lote_pdf(lote, verification_url):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    emitted_at = timezone.now()
    carbono = calcular_carbono_almacenado(lote)
    balance = calcular_balance_lote(lote)
    pasaporte = calcular_pasaporte_lote(lote)
    qr_image = build_qr_image(verification_url)

    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.rect(0, height - 52 * mm, width, 52 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor("#34D399"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, height - 22 * mm, "PASAPORTE VERDE")
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(margin, height - 34 * mm, f"Certificado digital {lote.id_lote}")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        margin,
        height - 43 * mm,
        "Certificado verificable de trazabilidad, carbono almacenado y balance neto.",
    )

    pdf.setFillColor(colors.HexColor("#DCFCE7"))
    pdf.roundRect(width - margin - 58 * mm, height - 42 * mm, 58 * mm, 18 * mm, 6, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#14532D"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(
        width - margin - 29 * mm,
        height - 32 * mm,
        pasaporte["estado_pasaporte"],
    )

    y = height - 72 * mm
    col_width = (width - (2 * margin) - 10 * mm) / 2
    draw_label_value(pdf, margin, y, "ID del lote", lote.id_lote)
    draw_label_value(pdf, margin + col_width + 10 * mm, y, "Aserradero", lote.empresa_aserradero)
    y -= 24 * mm
    draw_label_value(pdf, margin, y, "Especie", lote.especie)
    draw_label_value(pdf, margin + col_width + 10 * mm, y, "Volumen", f"{format_number(lote.volumen_m3)} m3")
    y -= 24 * mm
    draw_label_value(pdf, margin, y, "Origen", lote.origen)

    y -= 36 * mm
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(margin, y + 12 * mm, "Resumen climatico")

    metric_width = (width - 2 * margin - 12 * mm) / 3
    metrics = [
        ("Emisiones generadas", f"{format_number(balance['emisiones_generadas_kg_co2e'])} kg CO2e"),
        ("CO2 almacenado", f"{format_number(balance['co2_almacenado_kg'])} kg"),
        ("Balance neto", f"{format_number(balance['balance_neto_kg_co2e'])} kg CO2e"),
    ]

    for index, (label, value) in enumerate(metrics):
        x = margin + index * (metric_width + 6 * mm)
        pdf.setFillColor(colors.white)
        pdf.roundRect(x, y - 22 * mm, metric_width, 26 * mm, 6, fill=1, stroke=0)
        draw_label_value(pdf, x + 6 * mm, y - 5 * mm, label, value)

    y -= 58 * mm
    pdf.setFillColor(colors.white)
    pdf.roundRect(margin, y - 28 * mm, width - 2 * margin, 44 * mm, 6, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin + 8 * mm, y + 4 * mm, "Regla de elegibilidad")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        margin + 8 * mm,
        y - 7 * mm,
        f"Trazabilidad {pasaporte['trazabilidad_score']}% | Completitud {pasaporte['completitud_score']}% | Factores {pasaporte['factor_score']}%",
    )
    pdf.drawString(margin + 8 * mm, y - 18 * mm, pasaporte["razon_pasaporte"][:95])

    qr_size = 34 * mm
    pdf.drawImage(qr_image, width - margin - qr_size, y - 24 * mm, qr_size, qr_size)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - margin, y - 28 * mm, "Escanea para verificar")

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin, 18 * mm, f"Fecha de emision: {emitted_at:%Y-%m-%d %H:%M UTC}")
    pdf.drawRightString(width - margin, 18 * mm, verification_url)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
