# inventory/admin_passport_snippet.py
"""
Paste into your inventory/admin.py.

✅ Fixes NameError: download_device_passport not defined
✅ Adds:
  - QR thumbnail column (click to public page)
  - Action: "Device Passport PDF" (single -> PDF, multi -> ZIP)
  - Per-object button on change form (needs template override in this patch zip)
"""

from __future__ import annotations

from io import BytesIO
import zipfile

from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from .qr_passport import render_device_passport_pdf
from .models import Device


def _public_qr_url(obj: Device) -> str:
    token = getattr(obj, "qr_token", None)
    return f"/qr/public/{token}/" if token else "#"


def download_device_passport(modeladmin, request: HttpRequest, queryset):
    """
    Admin Action: Download device passport PDF(s).
    - If 1 selected => returns a single PDF.
    - If multiple selected => returns a ZIP of PDFs.
    """
    qs = list(queryset)
    if not qs:
        return None

    if len(qs) == 1:
        d = qs[0]
        pdf_bytes = render_device_passport_pdf(request=request, device=d)
        filename = f"device_passport_{getattr(d,'serial_number',d.pk)}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    # Multi => ZIP
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for d in qs:
            pdf_bytes = render_device_passport_pdf(request=request, device=d)
            filename = f"device_passport_{getattr(d,'serial_number',d.pk)}.pdf"
            zf.writestr(filename, pdf_bytes)

    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = 'attachment; filename="device_passports.zip"'
    return resp

download_device_passport.short_description = "Device Passport PDF (A4)"


def qr_preview(self, obj: Device):
    """
    list_display column: small QR image clickable to public QR page.
    """
    if not getattr(obj, "qr_image", None):
        return "-"
    try:
        url = obj.qr_image.url
    except Exception:
        return "-"
    return format_html(
        '<a href="{}" target="_blank" rel="noopener"><img src="{}" style="height:48px;width:48px;border:1px solid #ddd;border-radius:4px;background:#fff;"/></a>',
        _public_qr_url(obj),
        url,
    )

qr_preview.short_description = "QR"
