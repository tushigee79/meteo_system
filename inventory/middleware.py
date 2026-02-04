# inventory/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

class CalibrationAlertMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            # Өдөрт нэг удаа л шалгахын тулд session ашиглаж болно
            if not request.session.get('calibration_alert_sent'):
                from .views_dashboard_general import _scope_device_qs
                expired = _scope_device_qs(request).filter(next_verification_date__lt=timezone.localdate()).count()
                
                if expired > 0:
                    messages.error(request, f"АНХААР: Калибровкийн хугацаа хэтэрсэн {expired} багаж байна!")
                    # Email илгээх (settings.py-д тохиргоо хийгдсэн бол)
                    if getattr(settings, 'SEND_CALIBRATION_EMAILS', False):
                        send_mail(
                            'Калибровкийн хугацаа хэтэрлээ',
                            f'Системд {expired} багажийн хугацаа хэтэрсэн байна.',
                            'admin@meteo.gov.mn',
                            [request.user.email],
                            fail_silently=True,
                        )
                request.session['calibration_alert_sent'] = True
        return self.get_response(request)
class ForcePasswordChangeMiddleware:
    """
    must_change_password=True үед зөвхөн force-password-change хуудсыг нээж болно.
    Loop/asset асуудал үүсгэхгүйгээр allowlist хийсэн.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)

            if profile and profile.must_change_password:
                force_url = reverse("inventory_force_password_change")

                # allowlist
                if (
                    request.path == force_url
                    or request.path.startswith("/django-admin/logout/")
                    or request.path.startswith("/static/")
                    or request.path.startswith("/media/")
                ):
                    return self.get_response(request)

                return redirect(force_url)

        return self.get_response(request)
