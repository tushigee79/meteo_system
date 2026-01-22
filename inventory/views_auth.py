# inventory/views_auth.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse

from inventory.models import AuthAuditLog


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
def force_password_change(request):
    """
    must_change_password=True хэрэглэгчийг нууц үг солиулна.
    Амжилттай болсны дараа:
      - must_change_password=False
      - session hash update
      - audit log бичнэ
    """
    profile = getattr(request.user, "profile", None)

    # profile байхгүй бол шууд dashboard руу
    if not profile:
        return redirect("/admin/dashboard/")

    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)

            # ✅ flag reset
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])

            # ✅ audit log
            AuthAuditLog.objects.create(
                user=request.user,
                username=request.user.get_username(),
                action="PASSWORD_CHANGED",
                ip_address=_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
                extra={"forced": True, "at": timezone.now().isoformat()},
            )

            return redirect("/admin/dashboard/")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "auth/force_password_change.html", {"form": form})
