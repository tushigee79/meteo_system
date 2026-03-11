from django.shortcuts import redirect
from django.urls import reverse
from django.db import DatabaseError, OperationalError


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return self.get_response(request)

        path = request.path or ""

        if path.startswith("/static/") or path.startswith("/media/") or path == "/favicon.ico":
            return self.get_response(request)

        exempt_paths = set()
        for name in ("admin:login", "admin:logout", "admin_password_change"):
            try:
                exempt_paths.add(reverse(name))
            except Exception:
                pass

        if path in exempt_paths:
            return self.get_response(request)

        try:
            profile = getattr(user, "profile", None)
        except (DatabaseError, OperationalError):
            return self.get_response(request)

        if not profile:
            return self.get_response(request)

        if getattr(profile, "must_change_password", False):
            try:
                return redirect("admin_password_change")
            except Exception:
                return self.get_response(request)

        return self.get_response(request)