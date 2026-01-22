# inventory/dashboard.py
from datetime import date
from django.db.models import Count, Q
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import json

from .models import Device, Aimag


AIMAG_ENGINEER_GROUP = "AimagEngineer"


def is_aimag_engineer(user) -> bool:
    return user.is_authenticated and user.groups.filter(name=AIMAG_ENGINEER_GROUP).exists()


def get_user_aimag(user):
    prof = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    return getattr(prof, "aimag", None)


def scoped_devices_qs(user):
    qs = Device.objects.all().select_related("catalog_item", "location", "location__aimag_ref")
    if user.is_superuser:
        return qs
    aimag = get_user_aimag(user)
    if aimag:
        return qs.filter(location__aimag_ref=aimag)
    if is_aimag_engineer(user):
        return qs.none()
    return qs


def build_dashboard_context(user):
    """
    templates/inventory/dashboard.html-д шаардлагатай context-ууд:
    - title, total_devices, active_devices, broken_devices, expired_count
    - status_stats_json, aimag_stats_json
    """
    today: date = timezone.localdate()
    devices = scoped_devices_qs(user)

    # 1) Тоонууд
    total_devices = devices.count()
    active_devices = devices.filter(status="Active").count()
    broken_devices = devices.filter(status__in=["Broken", "Repair"]).count()

    # 2) Lifespan expired (installation_date + lifespan_years)
    expired_count = 0
    for installation_date, lifespan_years in devices.values_list("installation_date", "lifespan_years"):
        if not installation_date:
            continue

        years = int(lifespan_years or 0)
        if years <= 0:
            continue

        try:
            exp = installation_date.replace(year=installation_date.year + years)
        except ValueError:
            exp = installation_date.replace(month=2, day=28, year=installation_date.year + years)

        if exp < today:
            expired_count += 1

    # 3) Status stats (Chart.js)
    status_stats = list(
        devices.values("status").annotate(count=Count("id")).order_by("-count")
    )

    # 4) Aimag stats (Top 10 эвдрэлтэй)
    if user.is_superuser:
        aimag_qs = Aimag.objects.all()
    else:
        aimag = get_user_aimag(user)
        aimag_qs = Aimag.objects.filter(id=getattr(aimag, "id", None)) if aimag else Aimag.objects.none()

    aimag_stats = list(
        aimag_qs.annotate(
            broken_count=Count(
                "location__devices",
                filter=Q(location__devices__status__in=["Broken", "Repair"]),
                distinct=True,
            )
        )
        .filter(broken_count__gt=0)
        .order_by("-broken_count")[:10]
        .values("name", "broken_count")
    )

    return {
        "title": "График тайлан",
        "total_devices": total_devices,
        "active_devices": active_devices,
        "broken_devices": broken_devices,
        "expired_count": expired_count,
        "status_stats_json": json.dumps(status_stats, cls=DjangoJSONEncoder, ensure_ascii=False),
        "aimag_stats_json": json.dumps(aimag_stats, cls=DjangoJSONEncoder, ensure_ascii=False),
        "is_scoped": (not user.is_superuser) and is_aimag_engineer(user),
        "aimag": get_user_aimag(user),
    }
