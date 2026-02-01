import os
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse

# ReportLab сангууд
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing

def register_mongolian_font():
    """Монгол фонтыг бүртгэх функц"""
    # Төслийн static хавтас дотор fonts/Arial.ttf байгаа гэж үзэв
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial.ttf')
    
    # Хэрэв static дотор байхгүй бол Windows/Linux системийн фонтыг шалгах (fallback)
    if not os.path.exists(font_path):
        # Хөгжүүлэлтийн үед түр зуур хэрэглэх зам (өөрийнхөөрөө солино уу)
        font_path = r"C:\Windows\Fonts\arial.ttf" 

    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            return 'Arial'
        else:
            print(f"Warning: Font not found at {font_path}. Using default Helvetica.")
            return 'Helvetica' # Кирилл үсэг танихгүй
    except Exception as e:
        print(f"Font registration error: {e}")
        return 'Helvetica'

def generate_qr_code(data_string):
    """QR код үүсгэж Drawing объект буцаана"""
    qr_code = qr.QrCodeWidget(data_string)
    qr_code.barWidth = 35 * mm
    qr_code.barHeight = 35 * mm
    qr_code.qrVersion = 1
    
    d = Drawing(45 * mm, 45 * mm)
    d.add(qr_code)
    return d

def render_device_passport_pdf(request, device):
    """Төхөөрөмжийн паспортыг PDF хэлбэрээр үүсгэх"""
    
    # 1. Тохиргоо
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"Passport - {device.serial_number}"
    )
    
    elements = []
    
    # 2. Фонт болон Стайл бэлтгэх
    font_name = register_mongolian_font()
    styles = getSampleStyleSheet()
    
    # Гарчгийн стайл
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        alignment=1, # Center
        spaceAfter=10*mm
    )
    
    # Энгийн текстийн стайл
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14, # Мөр хоорондын зай
    )
    
    # Хүснэгтийн толгой стайл
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        textColor=colors.whitesmoke,
        alignment=1, # Center
        fontName_bold=font_name # Bold байхгүй бол энгийнээр
    )

    # 3. QR Код болон Гарчиг
    # QR URL үүсгэх (Танай домайн тохиргооноос хамаарна)
    domain = request.build_absolute_uri('/')[:-1]
    qr_url = f"{domain}/qr/public/{getattr(device, 'qr_token', '')}/"
    qr_drawing = generate_qr_code(qr_url)

    # Гарчиг болон QR кодыг зэрэгцүүлж тавих (Table ашиглана)
    title_text = f"ТӨХӨӨРӨМЖИЙН ПАСПОРТ<br/><font size=12>{device.name}</font>"
    
    header_data = [
        [Paragraph(title_text, title_style), qr_drawing]
    ]
    
    header_table = Table(header_data, colWidths=[120*mm, 50*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10*mm))

    # 4. Төхөөрөмжийн мэдээллийн хүснэгт
    # None утгуудыг хоосон мөр болгох
    def check(val): return str(val) if val else "-"

    data = [
        # Толгой
        ["Үзүүлэлт", "Утга"],
        # Мэдээлэл
        ["Төхөөрөмжийн нэр", Paragraph(check(device.name), normal_style)],
        ["Сериал дугаар", Paragraph(check(device.serial_number), normal_style)],
        ["Төрөл (Kind)", Paragraph(check(device.kind), normal_style)],
        ["Модель", Paragraph(check(device.model), normal_style)],
        ["Үйлдвэрлэгч", Paragraph(check(device.manufacturer), normal_style)],
        ["Суурилуулсан огноо", check(device.installation_date)],
        ["Төлөв", check(device.status)],
        ["Байршил", Paragraph(str(device.location) if device.location else "Тодорхойгүй", normal_style)],
    ]

    # Хүснэгтийн дизайн
    table = Table(data, colWidths=[60*mm, 110*mm])
    table.setStyle(TableStyle([
        # Толгой хэсгийн дизайн
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)), # Цэнхэр дэвсгэр
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Их биеийн дизайн
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), # Хүрээ
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), # Текстийг дээр нь шахах
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 10*mm))

    # 5. Нэмэлт тайлбар (Description)
    if device.description:
        elements.append(Paragraph("<b>Нэмэлт тайлбар:</b>", normal_style))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(check(device.description), normal_style))

    # 6. PDF үүсгэх
    doc.build(elements)
    
    # Bytes буцаах
    pdf = buffer.getvalue()
    buffer.close()
    return pdf