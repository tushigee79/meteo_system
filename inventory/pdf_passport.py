# inventory/pdf_passport.py
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def device_display_name(device) -> str:
    # Device дээр name байхгүй тул fallback
    for attr in ("name", "title", "device_name", "display_name"):
        v = getattr(device, attr, None)
        if v:
            return str(v)
    parts = []
    for attr in ("inventory_code", "serial_number", "model"):
        v = getattr(device, attr, None)
        if v:
            parts.append(str(v))
    return " / ".join(parts) if parts else str(device)


def _safe(getter, default: str = "") -> str:
    try:
        v = getter()
    except Exception:
        v = None
    return default if (v is None) else str(v)


def generate_device_passport_pdf_bytes(device, request=None) -> bytes:
    """
    PDF engine: зөвхөн bytes буцаана. View/Admin нь HttpResponse-оо өөрсдөө үүсгэнэ.
    """
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Device Passport",
    )

    styles = getSampleStyleSheet()
    story = []

    # ---- TITLE ----
    title = f"ТӨХӨӨРӨМЖИЙН ПАСПОРТ<br/><font size=12>{device_display_name(device)}</font>"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 6 * mm))

    # ---- 1) Үндсэн мэдээлэл хүснэгт ----
    info_rows = [
        ["Талбар", "Утга"],
        ["Код (Inventory)", _safe(lambda: getattr(device, "inventory_code", "") or "")],
        ["Серийн дугаар", _safe(lambda: getattr(device, "serial_number", "") or "")],
        ["Загвар/Model", _safe(lambda: getattr(device, "model", "") or "")],
        ["Үйлдвэрлэгч", _safe(lambda: getattr(device, "manufacturer", "") or "")],
        ["Төрөл (Kind)", _safe(lambda: getattr(device, "kind", "") or "")],
        ["Төлөв", _safe(lambda: getattr(device, "status", "") or "")],
        ["Байршил", _safe(lambda: getattr(getattr(device, "location", None), "name", "") or "")],
    ]

    tbl = Table(info_rows, colWidths=[45 * mm, 120 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))

    # TODO: энд QR / Maintenance / Movement хүснэгтүүдээ үргэлжлүүлж нэмнэ

    doc.build(story)

    pdf = buf.getvalue()
    buf.close()
    return pdf
