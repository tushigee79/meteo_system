from __future__ import annotations

import logging

from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from inventory.utils.safe_db import safe_get_profile

logger = logging.getLogger(__name__)


class UserProfileMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        profile = safe_get_profile(user)

        request.user_profile = profile
        request.user_role = getattr(profile, "role", None) if profile else None
        request.user_aimag = getattr(profile, "aimag", None) if profile else None
        request.user_aimag_ref = getattr(profile, "aimag_ref", None) if profile else None
        return None


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    EXEMPT_URLS = (
        "/admin/login/",
        "/admin/logout/",
        "/admin/password_change/",
    )

    def process_request(self, request):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return None

        path = request.path
        for url in self.EXEMPT_URLS:
            if path.startswith(url):
                return None

        try:
            profile = getattr(user, "profile", None)
        except Exception:
            profile = None

        must_change = getattr(profile, "must_change_password", False) if profile else False
        if must_change:
            return redirect("/admin/password_change/")

        return None