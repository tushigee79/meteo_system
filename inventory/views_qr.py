# inventory/views_qr.py
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from inventory.models import Device
from inventory.pdf_passport import generate_device_passport_pdf_bytes


@xframe_options_sameorigin
def device_passport_pdf_view(request, device_id: int):
    """Internal admin helper: render passport PDF by Device PK."""
    device = get_object_or_404(Device, pk=device_id)
    pdf_bytes = generate_device_passport_pdf_bytes(device, request=request)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="device_passport.pdf"'
    return resp


@xframe_options_sameorigin
def qr_public(request, token):
    """Public QR landing page (very small HTML) that links to the passport PDF."""
    device = get_object_or_404(Device, qr_token=token)
    pdf_url = reverse("qr_device_public_passport_pdf", args=[str(token)])

    html = f"""
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: Arial; padding:16px;">
      <h3>Device Public</h3>
      <p><b>Inventory code:</b> {getattr(device, 'inventory_code', '') or ''}</p>
      <p><b>Serial:</b> {getattr(device, 'serial_number', '') or ''}</p>
      <p><a href="{pdf_url}" target="_blank">Passport PDF татах</a></p>
    </body></html>
    """
    return HttpResponse(html)


def qr_passport_pdf(request, token):
    """Public passport PDF by QR token."""
    device = get_object_or_404(Device, qr_token=token)
    pdf_bytes = generate_device_passport_pdf_bytes(device, request=request)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    inv = getattr(device, "inventory_code", None) or str(device.id)
    resp["Content-Disposition"] = f'inline; filename="passport_{inv}.pdf"'
    return resp
