# inventory/pdf/pdf_passport.py
from __future__ import annotations

import io
import uuid

import qrcode
from django.urls import reverse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from inventory.models import DeviceMovement, MaintenanceService, ControlAdjustment
from inventory.pdf_passport import register_fonts


def build_device_timeline(device, limit: int = 15):
    rows = []

    # DeviceMovement
    try:
        qs = DeviceMovement.objects.filter(device=device).order_by("-moved_at")[:limit]
        for m in qs:
            dt = getattr(m, "moved_at", None) or getattr(m, "date", None)
            dt = dt.date().isoformat() if dt else ""
            rows.append([dt, "Шилжилт", getattr(m, "reason", "") or ""])
    except Exception:
        pass

    # MaintenanceService
    try:
        qs = MaintenanceService.objects.filter(device=device).order_by("-service_date")[:limit]
        for s in qs:
            dt = getattr(s, "service_date", None)
            dt = dt.isoformat() if dt else ""
            title = getattr(s, "service_type", "") or "Засвар"
            note = getattr(s, "notes", "") or ""
            rows.append([dt, title, note])
    except Exception:
        pass

    # ControlAdjustment
    try:
        qs = ControlAdjustment.objects.filter(device=device).order_by("-adjusted_at")[:limit]
        for c in qs:
            dt = getattr(c, "adjusted_at", None) or getattr(c, "date", None)
            dt = dt.date().isoformat() if dt else ""
            rows.append([dt, "Тохируулга", getattr(c, "notes", "") or ""])
    except Exception:
        pass

    rows.sort(key=lambda r: r[0], reverse=True)
    return rows[:limit]


def _make_qr_png_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_device_passport_pdf_bytes(device, request=None) -> bytes:
    font, font_bold = register_fonts()

    # base URL
    if request is not None:
        base_url = request.build_absolute_uri("/").rstrip("/")
    else:
        base_url = "http://127.0.0.1:8000"

    # ✅ token байхгүй бол үүсгээд хадгал
    token = getattr(device, "qr_token", None)
    if not token:
        token = uuid.uuid4()
        device.qr_token = token
        try:
            device.save(update_fields=["qr_token"])
        except Exception:
            device.save()

    # ✅ URL-аа urls.py-ийн нэрээр гаргана (meteo_config/urls.py: name="qr_public")
    try:
        public_path = reverse("qr_public", args=[str(token)])
    except Exception:
        public_path = f"/qr/{token}/"

    qr_url = f"{base_url}{public_path}"

    # styles
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font
    styles["Normal"].fontSize = 10
    styles["Title"].fontName = font_bold
    styles["Title"].fontSize = 16

    style_title = ParagraphStyle(
        "TitleMN",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=16,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    style_h = ParagraphStyle(
        "HeaderMN",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=11,
        spaceBefore=8,
        spaceAfter=6,
        textColor=colors.HexColor("#1f4e79"),
    )

    # PDF build
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    elements = []
    elements.append(Paragraph("ТЕХНИКИЙН ПАСПОРТ", style_title))

    # QR + Summary row
    qr_png = _make_qr_png_bytes(qr_url)
    qr_img = Image(io.BytesIO(qr_png), width=35 * mm, height=35 * mm)

    kind = getattr(device, "kind", "") or ""
    inv = getattr(device, "inventory_code", "") or getattr(device, "inventory_no", "") or ""
    status = getattr(device, "status", "") or ""

    summary = [
        [Paragraph(f"<b>Төрөл:</b> {kind}", styles["Normal"])],
        [Paragraph(f"<b>Инв №:</b> {inv}", styles["Normal"])],
        [Paragraph(f"<b>Төлөв:</b> {status}", styles["Normal"])],
    ]
    summary_tbl = Table(summary, colWidths=[12 * cm])
    summary_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    top_tbl = Table([[qr_img, summary_tbl]], colWidths=[4 * cm, 12 * cm])
    top_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(top_tbl)
    elements.append(Spacer(1, 10))

    # Device details
    elements.append(Paragraph("ҮНДСЭН МЭДЭЭЛЭЛ", style_h))
    rows = [
        ["ID", str(getattr(device, "id", "") or "")],
        ["Төрөл", kind],
        ["Инв №", inv],
        ["Серийн дугаар", str(getattr(device, "serial_number", "") or getattr(device, "serial_no", "") or "")],
        ["Байршил", str(getattr(getattr(device, "location", None), "name", "") or "")],
    ]
    t = Table(rows, colWidths=[5 * cm, 11 * cm])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTNAME", (0, 0), (0, -1), font_bold),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Timeline
    elements.append(Paragraph("ҮЙЛЧИЛГЭЭНИЙ ТҮҮХ (СҮҮЛИЙН 15)", style_h))
    timeline = build_device_timeline(device, limit=15)
    if not timeline:
        elements.append(Paragraph("Бичлэг олдсонгүй.", styles["Normal"]))
    else:
        tr = [["Огноо", "Төрөл", "Тайлбар"]] + timeline
        tt = Table(tr, colWidths=[3 * cm, 4 * cm, 9 * cm])
        tt.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTNAME", (0, 0), (-1, 0), font_bold),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(tt)

    doc.build(elements)
    return buf.getvalue()
