from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from django.conf import settings
import os

def generate_device_passport(device, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph("<b>DEVICE PASSPORT</b>", styles["Title"]))
    elems.append(Spacer(1, 12))

    elems.append(Paragraph(f"Serial: {device.serial_number}", styles["Normal"]))
    elems.append(Paragraph(f"Type: {device.get_kind_display()}", styles["Normal"]))
    elems.append(Paragraph(f"Status: {device.get_status_display()}", styles["Normal"]))
    elems.append(Spacer(1, 12))

    if device.qr_image:
        qr_path = os.path.join(settings.MEDIA_ROOT, device.qr_image.name)
        elems.append(Image(qr_path, width=120, height=120))
        elems.append(Spacer(1, 12))
        elems.append(Paragraph(
            f"QR URL: /qr/device/{device.qr_token}/",
            styles["Small"],
        ))

    doc.build(elems)
