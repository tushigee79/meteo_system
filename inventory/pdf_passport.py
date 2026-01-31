from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.utils import timezone


# ---------------------------------------------------------------------
# Timeline helpers
# ---------------------------------------------------------------------
def _pick_order_field(model, preferred: Sequence[str]) -> Optional[str]:
    try:
        field_names = {f.name for f in model._meta.fields}
    except Exception:
        return None
    for name in preferred:
        if name in field_names:
            return name
    return None


def build_device_timeline(device, limit: int = 20) -> List[Dict[str, Any]]:
    """Unified lifecycle timeline: movements + maintenance + control adjustments.

    This function is defensive about field names to avoid FieldError when your models
    use slightly different date fields.
    """
    from .models import DeviceMovement, MaintenanceService, ControlAdjustment

    items: List[Dict[str, Any]] = []

    # Maintenance
    m_order = _pick_order_field(MaintenanceService, ["date", "created_at"])
    m_qs = MaintenanceService.objects.filter(device=device)
    if m_order:
        m_qs = m_qs.order_by(f"-{m_order}")
    for s in m_qs[:limit]:
        items.append({
            "ts": getattr(s, "date", None) or getattr(s, "created_at", None) or timezone.now(),
            "type": "Засвар/Калибровка",
            "title": (getattr(s, "reason", "") or "").strip() or (getattr(s, "performer_type", "") or "").strip() or "Service",
            "note": (getattr(s, "note", "") or "").strip(),
        })

    # Control adjustments
    c_order = _pick_order_field(ControlAdjustment, ["date", "created_at", "approved_at", "submitted_at"])
    c_qs = ControlAdjustment.objects.filter(device=device)
    if c_order:
        c_qs = c_qs.order_by(f"-{c_order}")
    for c in c_qs[:limit]:
        items.append({
            "ts": getattr(c, "date", None) or getattr(c, "created_at", None) or getattr(c, "approved_at", None) or timezone.now(),
            "type": "Тохируулга",
            "title": (getattr(c, "reason", "") or "").strip() or "Control",
            "note": (getattr(c, "note", "") or "").strip(),
        })

    # Movements
    mv_qs = DeviceMovement.objects.filter(device=device)
    mv_order = _pick_order_field(DeviceMovement, ["moved_at", "created_at"])
    if mv_order:
        mv_qs = mv_qs.order_by(f"-{mv_order}")
    for m in mv_qs[:limit]:
        items.append({
            "ts": getattr(m, "moved_at", None) or getattr(m, "created_at", None) or timezone.now(),
            "type": "Шилжилт",
            "title": f"{getattr(m, 'from_location', None) or '—'} → {getattr(m, 'to_location', None) or '—'}",
            "note": (getattr(m, "reason", "") or "").strip(),
        })

    # Newest first
    items.sort(key=lambda x: x.get("ts") or timezone.now(), reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------
# Font helpers (Cyrillic-safe, never crash)
# ---------------------------------------------------------------------
def _register_mn_font():
    """Register a Cyrillic-capable font and return its internal name.

    Never raises; if no TTF is found, returns Helvetica (PDF still generated).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 1) Project-local fonts directory (create if possible)
    project_fonts_dir: Optional[str]
    try:
        project_fonts_dir = os.path.join(settings.BASE_DIR, "inventory", "static", "fonts")
        os.makedirs(project_fonts_dir, exist_ok=True)
    except Exception:
        project_fonts_dir = None

    candidates: List[Tuple[str, str]] = []
    if project_fonts_dir:
        candidates += [
            ("DejaVuSans", os.path.join(project_fonts_dir, "DejaVuSans.ttf")),
            ("NotoSans", os.path.join(project_fonts_dir, "NotoSans-Regular.ttf")),
            ("NotoSans", os.path.join(project_fonts_dir, "NotoSans.ttf")),
        ]

    # Windows system fonts
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates += [
        ("SegoeUI", os.path.join(windir, "Fonts", "segoeui.ttf")),
        ("Arial", os.path.join(windir, "Fonts", "arial.ttf")),
        ("Tahoma", os.path.join(windir, "Fonts", "tahoma.ttf")),
    ]

    # Linux
    candidates += [
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("DejaVuSans", "/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        ("NotoSans", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        ("NotoSans", "/usr/share/fonts/noto/NotoSans-Regular.ttf"),
    ]

    # macOS
    candidates += [
        ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"),
        ("Arial", "/Library/Fonts/Arial.ttf"),
    ]

    for font_name, font_path in candidates:
        try:
            if font_path and os.path.exists(font_path):
                # Already registered?
                try:
                    pdfmetrics.getFont(font_name)
                    return font_name
                except Exception:
                    pass
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
        except Exception:
            continue

    return "Helvetica"


# ---------------------------------------------------------------------
# PDF generator
# ---------------------------------------------------------------------
def generate_device_passport_pdf_bytes(device) -> bytes:
    """Generate A4 passport PDF including QR and last lifecycle events."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    # QR image bytes
    qr_bytes: Optional[bytes] = None
    if getattr(device, "qr_image", None):
        try:
            f = device.qr_image
            if hasattr(f, "open"):
                f.open("rb")
            qr_bytes = f.read()
        except Exception:
            qr_bytes = None

    # If missing qr_image, generate a QR from token/public URL
    if qr_bytes is None:
        try:
            import qrcode

            base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
            path = f"/qr/public/{getattr(device, 'qr_token', '')}/"
            qr_data = (base + path) if base else path

            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_Q,
                box_size=6,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            b = io.BytesIO()
            img.save(b, format="PNG")
            qr_bytes = b.getvalue()
        except Exception:
            qr_bytes = None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mn_font = _register_mn_font()

    margin = 15 * mm
    x0 = margin
    y0 = h - margin

    # Title
    c.setFont(mn_font, 14)
    c.drawString(x0, y0, "Багажны техник паспорт")

    # QR top-right
    if qr_bytes:
        try:
            img = ImageReader(io.BytesIO(qr_bytes))
            qr_size = 30 * mm
            c.drawImage(img, w - margin - qr_size, h - margin - qr_size, qr_size, qr_size, mask="auto")
        except Exception:
            pass

    c.setFont(mn_font, 10)
    y = y0 - 18 * mm

    def line(label: str, value: Any):
        nonlocal y
        c.setFont(mn_font, 10)
        c.drawString(x0, y, f"{label}:")
        c.drawString(x0 + 45 * mm, y, str(value) if value not in (None, "") else "—")
        y -= 6 * mm

    # Core fields (use your real model names)
    line("ID", getattr(device, "pk", "—"))
    line("Serial", getattr(device, "serial_number", "—"))
    line("Kind", getattr(device, "kind", "—"))
    line("Status", getattr(device, "status", "—"))

    loc = getattr(device, "location", None)
    line("Location", getattr(loc, "name", "—") if loc else "—")

    cat = getattr(device, "catalog_item", None)
    if cat:
        line("Catalog", str(cat))
    other_name = getattr(device, "other_name", "")
    if other_name:
        line("Other name", other_name)

    token = getattr(device, "qr_token", None)
    if token:
        line("QR token", token)

    y -= 4 * mm
    c.setFont(mn_font, 11)
    c.drawString(x0, y, "Lifecycle timeline (last events)")
    y -= 7 * mm

    timeline = build_device_timeline(device, limit=12)
    c.setFont(mn_font, 9)

    for it in timeline:
        ts = it.get("ts")
        if isinstance(ts, datetime):
            ts_str = ts.strftime("%Y-%m-%d")
        else:
            ts_str = str(ts)[:10] if ts else ""
        row = f"{ts_str} • {it.get('type')} • {it.get('title')}"
        c.drawString(x0, y, row[:110])
        y -= 5 * mm

        note = (it.get("note") or "").strip()
        if note:
            c.setFont(mn_font, 8)
            c.drawString(x0 + 5 * mm, y, note[:120])
            c.setFont(mn_font, 9)
            y -= 5 * mm

        if y < 20 * mm:
            c.showPage()
            c.setFont(mn_font, 9)
            y = h - margin

    c.showPage()
    c.save()
    return buf.getvalue()
