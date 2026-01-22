# inventory/middleware.py
from django.shortcuts import redirect
from django.urls import reverse


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
