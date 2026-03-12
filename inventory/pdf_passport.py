import io
import os
import qrcode
from datetime import datetime
from django.conf import settings
from django.utils import timezone

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ---------------------------------------------------------------------
# 1. Timeline helpers (Таны хуучин код хэвээрээ)
# ---------------------------------------------------------------------
def _pick_order_field(model, preferred):
    try:
        field_names = {f.name for f in model._meta.fields}
    except Exception:
        return None
    for name in preferred:
        if name in field_names:
            return name
    return None

def build_device_timeline(device, limit: int = 20):
    from .models import DeviceMovement, MaintenanceService, ControlAdjustment
    items = []

    # Maintenance
    m_order = _pick_order_field(MaintenanceService, ["date", "created_at"])
    m_qs = MaintenanceService.objects.filter(device=device)
    if m_order: m_qs = m_qs.order_by(f"-{m_order}")
    for s in m_qs[:limit]:
        items.append({
            "ts": getattr(s, "date", None) or getattr(s, "created_at", None) or timezone.now(),
            "type": "Засвар/Калибровка",
            "title": (getattr(s, "reason", "") or "").strip() or "Service",
            "note": (getattr(s, "note", "") or "").strip(),
        })

    # Control
    c_order = _pick_order_field(ControlAdjustment, ["date", "created_at", "approved_at"])
    c_qs = ControlAdjustment.objects.filter(device=device)
    if c_order: c_qs = c_qs.order_by(f"-{c_order}")
    for c in c_qs[:limit]:
        items.append({
            "ts": getattr(c, "date", None) or getattr(c, "created_at", None) or timezone.now(),
            "type": "Тохируулга",
            "title": (getattr(c, "reason", "") or "").strip() or "Control",
            "note": (getattr(c, "note", "") or "").strip(),
        })

    # Movements
    mv_qs = DeviceMovement.objects.filter(device=device)
    mv_order = _pick_order_field(DeviceMovement, ["moved_at", "created_at"])
    if mv_order: mv_qs = mv_qs.order_by(f"-{mv_order}")
    for m in mv_qs[:limit]:
        items.append({
            "ts": getattr(m, "moved_at", None) or getattr(m, "created_at", None) or timezone.now(),
            "type": "Шилжилт",
            "title": f"{getattr(m, 'from_location', None) or '-'} -> {getattr(m, 'to_location', None) or '-'}",
            "note": (getattr(m, "reason", "") or "").strip(),
        })

    items.sort(key=lambda x: x.get("ts") or timezone.now(), reverse=True)
    return items[:limit]

# ---------------------------------------------------------------------
# 2. Font & Setup
# ---------------------------------------------------------------------
def register_fonts():
    """Фонтыг олон газраас хайж бүртгэх функц."""
    
    # Хайх файлын нэрс
    font_names = ['Roboto-Regular.ttf', 'arial.ttf', 'Arimo-Regular.ttf']
    
    # Хайх замууд (Таны заасан замыг эхэнд нь орууллаа)
    search_paths = [
        # 1. D:\meteo_system\static\fonts\ (Таны үүсгэсэн зам)
        os.path.join(settings.BASE_DIR, 'static', 'fonts'),
        
        # 2. inventory/static/fonts/ (App доторх)
        os.path.join(settings.BASE_DIR, 'inventory', 'static', 'fonts'),
        
        # 3. STATIC_ROOT (Хэрэв collectstatic хийсэн бол)
        os.path.join(settings.STATIC_ROOT if settings.STATIC_ROOT else '', 'fonts'),
    ]

    target_font_path = None

    # Замуудаар гүйж хайна
    for path in search_paths:
        for fname in font_names:
            full_path = os.path.join(path, fname)
            if os.path.exists(full_path):
                target_font_path = full_path
                break
        if target_font_path:
            break

    # Олдсон бол бүртгэнэ
    if target_font_path:
        try:
            pdfmetrics.registerFont(TTFont('Roboto', target_font_path))
            # Bold хувилбар байхгүй бол Regular-ийг ашиглана
            pdfmetrics.registerFont(TTFont('Roboto-Bold', target_font_path))
            return 'Roboto', 'Roboto-Bold'
        except Exception:
            pass
    
    # Олдохгүй бол default руу шилжинэ (Дөрвөлжин гарах эрсдэлтэй)
    print("Warning: Mongolian font not found in:", search_paths)
    return 'Helvetica', 'Helvetica-Bold'

MAIN_FONT, MAIN_FONT_BOLD = register_fonts()

# ---------------------------------------------------------------------
# 3. PDF Components
# ---------------------------------------------------------------------

def draw_header_footer(canvas, doc):
    """Хуудас бүрийн толгой болон хөл"""
    canvas.saveState()
    w, h = A4
    
    # --- ЛОГО (Таны явуулсан зураг) ---
    # Логоны нэрийг 'logo.png' болгож static/images/ дотор хадгалаарай
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    
    if os.path.exists(logo_path):
        # Лого зүүн дээд буланд (өндөр=25мм)
        canvas.drawImage(logo_path, 20*mm, h - 35*mm, width=40*mm, height=20*mm, preserveAspectRatio=True, mask='auto')
    
    # --- Толгой текст ---
    canvas.setFont(MAIN_FONT_BOLD, 12)
    canvas.drawRightString(w - 20*mm, h - 25*mm, "ЦАГ УУР, ОРЧНЫ ШИНЖИЛГЭЭНИЙ ГАЗАР")
    canvas.setFont(MAIN_FONT, 10)
    canvas.drawRightString(w - 20*mm, h - 30*mm, "Техник хяналт, бүртгэлийн паспорт")
    
    # --- Хөх өнгийн тусгаарлах зураас ---
    canvas.setStrokeColor(colors.HexColor('#0056b3')) # Таны логоны цэнхэр өнгө
    canvas.setLineWidth(2)
    canvas.line(20*mm, h - 38*mm, w - 20*mm, h - 38*mm)
    
    # --- Хөл (Footer) ---
    canvas.setFont(MAIN_FONT, 8)
    canvas.setFillColor(colors.gray)
    canvas.drawCentredString(w/2, 10*mm, f"Хэвлэсэн: {timezone.now().strftime('%Y-%m-%d %H:%M')} | Хуудас {doc.page}")
    
    canvas.restoreState()

def generate_qr_buffer(data):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ---------------------------------------------------------------------
# 4. Main Generator
# ---------------------------------------------------------------------
def generate_device_passport_pdf_bytes(device) -> bytes:
    buffer = io.BytesIO()
    
    # Document Setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=45*mm, bottomMargin=20*mm, # Header-т зай үлдээх
        title=f"Passport {device.serial_number}"
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontName=MAIN_FONT_BOLD, fontSize=16, alignment=TA_CENTER, spaceAfter=15, textColor=colors.HexColor('#1e293b'))
    style_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName=MAIN_FONT_BOLD, fontSize=12, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#0056b3'))
    style_normal = ParagraphStyle('Norm', parent=styles['Normal'], fontName=MAIN_FONT, fontSize=10, leading=12)

    # --- Гарчиг ---
    elements.append(Paragraph("ТЕХНИКИЙН ПАСПОРТ", style_title))
    
    # --- 1. QR ба Үндсэн мэдээлэл (Зэрэгцээ байрлал) ---
    
    # QR Код бэлтгэх
    base_url = getattr(settings, "SITE_BASE_URL", "") or "http://127.0.0.1:8000"
    token = getattr(device, 'qr_token', '')
    qr_data = f"{base_url}/qr/public/{token}/"
    qr_img = Image(generate_qr_buffer(qr_data), width=35*mm, height=35*mm)
    
    # Текстэн мэдээлэл
    info_text = [
        [Paragraph(f"<b>Нэр / Төрөл:</b> {device.kind}", style_normal)],
        [Paragraph(f"<b>Сериал №:</b> {device.serial_number}", style_normal)],
        [Paragraph(f"<b>Төлөв:</b> {device.status}", style_normal)],
        [Paragraph(f"<b>Байршил:</b> {device.location.name if device.location else '-'}", style_normal)],
    ]
    
    # QR болон Текстийг зэрэгцүүлэх хүснэгт
    # [QR Зураг] | [Текст жагсаалт]
    header_data = [[qr_img, Table(info_text, colWidths=[10*cm])]]
    t_header = Table(header_data, colWidths=[4*cm, 11*cm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # Босоо тэнхлэгт голлуулах
        ('ALIGN', (0,0), (0,0), 'CENTER'),    # QR кодыг голлуулах
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 5*mm))

    # --- 2. Дэлгэрэнгүй мэдээллийн хүснэгт ---
    elements.append(Paragraph("ҮНДСЭН ҮЗҮҮЛЭЛТҮҮД", style_h2))
    
    table_data = [
        ["Үзүүлэлт", "Утга"], # Header row
        ["ID", str(device.pk)],
        ["Төхөөрөмжийн нэр", str(device.kind)],
        ["Сериал дугаар", str(device.serial_number)],
        ["Бараа материалын код", getattr(device, 'inventory_code', '-')], # Model дээр байгаа бол
        ["Үйлдвэрлэгч", getattr(device, 'manufacturer', '-')],
        ["Ашиглалтад орсон", getattr(device, 'commissioned_date', '-')],
        ["Хариуцагч байгууллага", str(device.location.owner_org.name) if device.location and device.location.owner_org else "-"],
        ["Аймаг / Дүүрэг", str(device.location.aimag_ref.name) if device.location and device.location.aimag_ref else "-"],
    ]
    
    t_main = Table(table_data, colWidths=[6*cm, 10*cm])
    t_main.setStyle(TableStyle([
        # Толгой хэсэг
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e6f2ff')), # Цайвар цэнхэр
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('FONTNAME', (0,0), (-1,0), MAIN_FONT_BOLD),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        # Бие хэсэг
        ('FONTNAME', (0,1), (-1,-1), MAIN_FONT),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        # Эхний багана (Label)
        ('FONTNAME', (0,1), (0,-1), MAIN_FONT_BOLD),
    ]))
    elements.append(t_main)
    elements.append(Spacer(1, 10*mm))

    # --- 3. Түүх (Timeline) ---
    timeline = build_device_timeline(device, limit=15)
    if timeline:
        elements.append(Paragraph("АШИГЛАЛТЫН ТҮҮХ (Сүүлийн үйл явдлууд)", style_h2))
        
        # Timeline Table Header
        tl_data = [["Огноо", "Төрөл", "Тайлбар"]]
        for item in timeline:
            ts = item['ts']
            if isinstance(ts, datetime):
                ts_str = ts.strftime("%Y-%m-%d")
            else:
                ts_str = str(ts)[:10]
            
            # Тайлбарыг богиносгох
            full_note = f"{item['title']} {item.get('note', '')}"
            
            tl_data.append([
                ts_str,
                Paragraph(item['type'], style_normal), # Paragraph ашиглавал текст урт бол автоматаар нугарна
                Paragraph(full_note, style_normal)
            ])
            
        t_hist = Table(tl_data, colWidths=[3*cm, 4*cm, 9*cm])
        t_hist.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), MAIN_FONT_BOLD),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTNAME', (0,1), (-1,-1), MAIN_FONT),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_hist)

    # Generate PDF
    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf