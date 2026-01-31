# inventory/qr_passport.py
from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass
from typing import Optional

from django.http import HttpRequest
from django.conf import settings

import uuid

# ReportLab is installed in your environment (used elsewhere in your project)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


@dataclass
class PassportRenderOptions:
    title_mn: str = "БАГАЖНЫ ТЕХНИК ПАСПОРТ"
    title_en: str = "DEVICE PASSPORT"
    # Optional logo: put a PNG at static/logo_namem.png (or change path below)
    logo_static_path: str = "static/logo_namem.png"
    show_public_url: bool = True


def _absolute_logo_path(opts: PassportRenderOptions) -> Optional[str]:
    # Tries BASE_DIR/static/... first; if not found, returns None.
    try:
        base_dir = getattr(settings, "BASE_DIR", None)
        if not base_dir:
            return None
        p = str(base_dir / opts.logo_static_path)
        return p if p and __import__("os").path.exists(p) else None
    except Exception:
        return None


def _build_public_url(request: HttpRequest, token: uuid.UUID) -> str:
    # Uses request.build_absolute_uri so it works on dev/prod.
    return request.build_absolute_uri(f"/qr/public/{token}/")


def render_device_passport_pdf(
    *,
    request: HttpRequest,
    device,
    opts: PassportRenderOptions | None = None,
) -> bytes:
    """
    Returns PDF bytes (A4) for a given Device instance.
    Assumes device has: serial_number, kind, status, qr_token, qr_image (optional),
    location (optional), catalog_item (optional), other_name (optional).
    """
    opts = opts or PassportRenderOptions()

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # --- header ---
    c.setTitle(f"passport_{getattr(device, 'serial_number', device.pk)}")

    # logo (optional)
    logo_path = _absolute_logo_path(opts)
    if logo_path:
        try:
            c.drawImage(ImageReader(logo_path), 15*mm, h - 30*mm, width=22*mm, height=22*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 14)
    c.drawString(45*mm, h - 18*mm, opts.title_mn)
    c.setFont("Helvetica", 11)
    c.drawString(45*mm, h - 26*mm, opts.title_en)

    # --- device fields ---
    y = h - 45*mm
    line = 7*mm

    def row(label_mn: str, label_en: str, value: str):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, y, f"{label_mn}:")
        c.setFont("Helvetica", 10)
        c.drawString(60*mm, y, str(value or ""))
        y -= line
        c.setFont("Helvetica", 8)
        c.drawString(15*mm, y+2.2*mm, f"{label_en}")
        y -= (line - 2*mm)

    serial = getattr(device, "serial_number", "") or ""
    kind = getattr(device, "kind", "") or ""
    status = getattr(device, "status", "") or ""

    # display name
    cat = getattr(device, "catalog_item", None)
    other_name = getattr(device, "other_name", "") or ""
    disp = ""
    try:
        if cat:
            disp = getattr(cat, "name_mn", "") or getattr(cat, "name", "") or ""
    except Exception:
        disp = ""
    if not disp:
        disp = other_name

    loc = getattr(device, "location", None)
    loc_name = getattr(loc, "name", "") if loc else ""

    row("Серийн дугаар", "Serial number", serial)
    row("Нэр", "Name", disp)
    row("Төрөл", "Type", kind)
    row("Төлөв", "Status", status)
    row("Байршил", "Location", loc_name)

    # --- QR block ---
    # right side box
    box_x = w - 65*mm
    box_y = h - 105*mm
    box_w = 50*mm
    box_h = 60*mm
    c.setLineWidth(0.6)
    c.rect(box_x, box_y, box_w, box_h, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(box_x + 5*mm, box_y + box_h - 10*mm, "QR / Link")

    token = getattr(device, "qr_token", None)
    public_url = _build_public_url(request, token) if (token and opts.show_public_url) else ""

    # draw QR image if exists
    qr_img_field = getattr(device, "qr_image", None)
    qr_path = None
    try:
        if qr_img_field and getattr(qr_img_field, "path", None):
            qr_path = qr_img_field.path
    except Exception:
        qr_path = None

    if qr_path:
        try:
            c.drawImage(ImageReader(qr_path), box_x + 7*mm, box_y + 17*mm, width=36*mm, height=36*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # show URL text (wrapped)
    if public_url:
        c.setFont("Helvetica", 7)
        # manual wrap
        max_chars = 38
        lines = [public_url[i:i+max_chars] for i in range(0, len(public_url), max_chars)]
        yy = box_y + 12*mm
        for ln in lines[:3]:
            c.drawString(box_x + 5*mm, yy, ln)
            yy -= 3.5*mm

    # footer
    c.setFont("Helvetica", 7)
    c.drawRightString(w - 15*mm, 12*mm, "NAMEM / БҮРТГЭЛ – generated")

    c.showPage()
    c.save()
    return buf.getvalue()
