# inventory/pdf_passport.py
from __future__ import annotations

import os
from typing import Tuple, Optional

from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_DONE = False
_FONT_PAIR: Optional[Tuple[str, str]] = None


def register_fonts() -> Tuple[str, str]:
    """
    Unicode-capable font registration for ReportLab.
    Priority: NotoSans (recommended) -> DejaVu -> Helvetica fallback.
    Put your fonts under: <BASE_DIR>/static/fonts/
      - NotoSans-Regular.ttf, NotoSans-Bold.ttf  (best)
      - DejaVuSans.ttf, DejaVuSans-Bold.ttf      (ok)
    """
    global _FONT_DONE, _FONT_PAIR
    if _FONT_DONE and _FONT_PAIR:
        return _FONT_PAIR

    font_dir = os.path.join(settings.BASE_DIR, "static", "fonts")

    candidates = [
        ("Noto", "Noto-Bold", "NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
        ("DejaVu", "DejaVu-Bold", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ]

    for name, name_bold, reg_file, bold_file in candidates:
        reg_path = os.path.join(font_dir, reg_file)
        bold_path = os.path.join(font_dir, bold_file)
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont(name, reg_path))
                pdfmetrics.registerFont(TTFont(name_bold, bold_path))
                _FONT_PAIR = (name, name_bold)
                _FONT_DONE = True
                return _FONT_PAIR
            except Exception:
                # try next candidate
                pass

    _FONT_PAIR = ("Helvetica", "Helvetica-Bold")
    _FONT_DONE = True
    return _FONT_PAIR


def generate_device_passport_pdf_bytes(device, request=None) -> bytes:
    """
    Public API used by admin.py / views.
    Delegates to implementation under inventory/pdf/pdf_passport.py
    """
    try:
        from inventory.pdf.pdf_passport import generate_device_passport_pdf_bytes as impl
    except Exception as e:
        raise ImportError(
            "PDF generator implementation not found. "
            "Expected: inventory.pdf.pdf_passport.generate_device_passport_pdf_bytes"
        ) from e

    try:
        return impl(device, request=request)
    except TypeError:
        return impl(device)
