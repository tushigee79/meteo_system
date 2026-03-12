import io
import uuid

from django.contrib import messages
from django.http import HttpResponse
from django.utils.html import format_html

try:
    import qrcode
except Exception:  # pragma: no cover
    qrcode = None


def generate_qr_token(modeladmin, request, queryset):
    updated = 0
    for obj in queryset:
        if hasattr(obj, "qr_token") and not obj.qr_token:
            obj.qr_token = uuid.uuid4()
            obj.save(update_fields=["qr_token"])
            updated += 1
    modeladmin.message_user(
        request,
        f"{updated} мөр дээр QR token үүсгэлээ.",
        level=messages.SUCCESS,
    )


generate_qr_token.short_description = "QR token үүсгэх"


def revoke_qr_token(modeladmin, request, queryset):
    updated = 0
    for obj in queryset:
        if hasattr(obj, "qr_token") and obj.qr_token:
            obj.qr_token = None
            obj.save(update_fields=["qr_token"])
            updated += 1
    modeladmin.message_user(
        request,
        f"{updated} мөрийн QR token-г цуцаллаа.",
        level=messages.WARNING,
    )


revoke_qr_token.short_description = "QR token цуцлах"


def qr_preview(obj):
    if not getattr(obj, "qr_token", None):
        return "—"
    return format_html("<code>{}</code>", obj.qr_token)


qr_preview.short_description = "QR token"


def qr_image_response(token_text: str):
    if qrcode is None:
        return HttpResponse("qrcode package суусангүй.", status=500, content_type="text/plain")

    img = qrcode.make(token_text)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type="image/png")