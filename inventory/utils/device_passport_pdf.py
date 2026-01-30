from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from django.conf import settings
import os

def build_device_passport_pdf(device, out_path):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>БАГАЖНЫ ТЕХНИК ПАСПОРТ</b>", styles["Title"]))
    story.append(Spacer(1, 8))

    # QR
    if device.qr_image and os.path.exists(device.qr_image.path):
        story.append(Image(device.qr_image.path, 40*mm, 40*mm))
        story.append(Spacer(1, 6))

    # Basic info
    table_data = [
        ["Нэр", device.name],
        ["Серийн №", device.serial_number],
        ["Төрөл", device.catalog.kind if device.catalog else ""],
        ["Байршил", str(device.location) if device.location else ""],
        ["Байгууллага", str(device.owner_org) if device.owner_org else ""],
        ["Төлөв", device.status],
    ]
    t = Table(table_data, colWidths=[50*mm, 120*mm])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Maintenance (last 5)
    maint = device.maintenances.all().order_by("-date")[:5]
    story.append(Paragraph("<b>Сүүлийн засвар / калибровка</b>", styles["Heading2"]))
    for m in maint:
        story.append(Paragraph(
            f"- {m.date}: {m.kind} / {m.result}", styles["Normal"]
        ))

    doc = SimpleDocTemplate(out_path, pagesize=A4)
    doc.build(story)
