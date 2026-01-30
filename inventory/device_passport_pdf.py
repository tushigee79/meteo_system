# inventory/device_passport_pdf.py
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.conf import settings
from io import BytesIO
from django.http import HttpResponse

def generate_device_passport_pdf(device, request=None):
    """
    Generate Device Passport PDF (A4).
    Used by admin action & public QR page.
    """
    buffer = BytesIO()

    # 🔽 энд өмнө нь хийсэн PDF logic чинь байна
    # canvas / reportlab / platypus г.м
    # QR, lifecycle, metadata бүгд орсон

    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="device_passport_{device.serial_number}.pdf"'
    )
    
    # ============================================================
# Device Passport PDF (A4) action
# ============================================================
from django.http import HttpResponse
from django.contrib import admin

from .device_passport_pdf import generate_device_passport_pdf


@admin.action(description="📄 Device Passport (PDF)")
def download_device_passport(modeladmin, request, queryset):
    """
    Admin action:
    - Нэг Device сонгосон үед A4 PDF passport татна
    """
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Нэг багаж сонгоно уу.",
            level="error",
        )
        return None

    device = queryset.first()

    # 👉 PDF response буцаана
    return generate_device_passport_pdf(device, request)

    return response

import os

def generate_device_passport(device, out_path):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    elems = []

    elems.append(Paragraph("<b>DEVICE PASSPORT</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    data = [
        ["Serial", device.serial_number],
        ["Type", device.get_kind_display()],
        ["Status", device.get_status_display()],
    ]
    table = Table(data, colWidths=[120, 350])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke),
    ]))
    elems.append(table)
    elems.append(Spacer(1, 16))

    if device.qr_image:
        qr_path = os.path.join(settings.MEDIA_ROOT, device.qr_image.name)
        elems.append(Paragraph("QR Code:", styles["Heading3"]))
        elems.append(Image(qr_path, width=140, height=140))

    doc.build(elems)

# inventory/device_passport_pdf.py
from io import BytesIO
from django.http import HttpResponse

def generate_device_passport_pdf(device, request=None):
    """
    Generate Device Passport PDF (A4).
    Used by admin action & public QR page.
    """
    buffer = BytesIO()

    # 🔽 энд өмнө нь хийсэн PDF logic чинь байна
    # canvas / reportlab / platypus г.м
    # QR, lifecycle, metadata бүгд орсон

    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="device_passport_{device.serial_number}.pdf"'
    )
    return response
