import io
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_device_passport_pdf(device):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Багажны техник паспорт")

    y -= 35
    p.setFont("Helvetica", 11)

    rows = [
        ("Нэр", getattr(device, "name", "")),
        ("Серийн дугаар", getattr(device, "serial_number", "")),
        ("Төлөв", getattr(device, "status", "")),
        ("Байршил", str(getattr(device, "location", ""))),
        ("Сүүлд калибровка", str(getattr(device, "last_verification_date", ""))),
        ("Дараагийн калибровка", str(getattr(device, "next_verification_date", ""))),
    ]

    for label, value in rows:
        p.drawString(50, y, f"{label}: {value}")
        y -= 22

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


def download_device_passport(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(request, "1 төхөөрөмж сонгоно уу.")
        return

    device = queryset.first()
    pdf_buffer = build_device_passport_pdf(device)

    response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="device_passport_{device.pk}.pdf"'
    return response


download_device_passport.short_description = "Техник паспорт PDF татах"