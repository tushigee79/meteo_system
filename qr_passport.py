"""QR public page + passport PDF endpoints.

⚠️ This file appears to be an early standalone prototype.
The maintained implementation for the Device Passport is in:
- inventory/pdf/passport.py (build_device_passport_pdf)

We keep this module minimal and import-safe so it can't break Django startup
(e.g. during `python manage.py check` or `migrate`) if it is imported.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin

from inventory.models import Device, MaintenanceService, DeviceMovement
from inventory.pdf.passport import build_device_passport_pdf


@xframe_options_sameorigin
def qr_public(request, token):
    """Very small public HTML view; links to the passport PDF."""
    device = get_object_or_404(Device, qr_token=token)
    pdf_url = reverse("qr_device_public_passport_pdf", args=[str(token)])
    html = f"""
    <html><head><meta charset=\"utf-8\"></head>
    <body style=\"font-family: Arial; padding:16px;\">
      <h3>Device Public</h3>
      <p><b>Inventory code:</b> {device.inventory_code}</p>
      <p><b>Serial:</b> {device.serial_number}</p>
      <p><a href=\"{pdf_url}\" target=\"_blank\">Passport PDF татах</a></p>
    </body></html>
    """
    return HttpResponse(html)


def qr_passport_pdf(request, token):
    """Generate passport PDF using the maintained builder."""
    device = get_object_or_404(Device, qr_token=token)

    public_path = reverse("qr_device_public", args=[str(token)])
    public_url = request.build_absolute_uri(public_path)

    # Last 5 maintenance rows (fallback-safe field picks)
    maint_rows = []
    for m in MaintenanceService.objects.filter(device=device).order_by("-id")[:5]:
        date = (
            getattr(m, "created_at", None)
            or getattr(m, "created", None)
            or getattr(m, "submitted_at", None)
            or ""
        )
        workflow = getattr(m, "workflow_status", "") or getattr(m, "status", "") or ""
        note = (
            getattr(m, "comment", "")
            or getattr(m, "notes", "")
            or getattr(m, "description", "")
            or ""
        )
        maint_rows.append(
            {
                "date": date,
                "workflow": workflow,
                "reason": getattr(m, "reason", ""),
                "note": note,
            }
        )

    # Last 5 movement rows
    move_rows = []
    for mv in (
        DeviceMovement.objects.filter(device=device)
        .select_related("from_location", "to_location", "moved_by")
        .order_by("-moved_at")[:5]
    ):
        prof = getattr(mv, "moved_by", None)
        u = getattr(prof, "user", None) if prof else None
        by = getattr(u, "username", "") if u else _safe(prof)

        move_rows.append(
            {
                "date": getattr(mv, "moved_at", ""),
                "from": getattr(getattr(mv, "from_location", None), "name", ""),
                "to": getattr(getattr(mv, "to_location", None), "name", ""),
                "reason": getattr(mv, "reason", ""),
                "by": by,
            }
        )

    pdf_bytes = build_device_passport_pdf(
        device=device,
        public_url=public_url,
        maint_rows=maint_rows,
        move_rows=move_rows,
    )

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    inv = device.inventory_code or str(device.id)
    resp["Content-Disposition"] = f'inline; filename="passport_{inv}.pdf"'
    return resp


def _safe(v) -> str:
    return "" if v is None else str(v)
