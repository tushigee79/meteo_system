from django.http import HttpResponse
from django.utils.timezone import now
from django.conf import settings
import os, tempfile

from .utils.device_passport_pdf import generate_device_passport

def download_device_passport(modeladmin, request, queryset):
    device = queryset.first()
    if not device:
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        generate_device_passport(device, tmp.name)
        tmp.seek(0)
        pdf = tmp.read()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="device_passport_{device.serial_number}.pdf"'
    return response

download_device_passport.short_description = "📄 Device Passport (PDF)"
