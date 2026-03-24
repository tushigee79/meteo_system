# inventory/admin/admin_filters.py
from django.contrib import admin

from inventory.models import Aimag, SumDuureg


class AimagListFilter(admin.SimpleListFilter):
    title = "Аймаг"
    parameter_name = "aimag"

    def lookups(self, request, model_admin):
        return [(str(a.pk), a.name) for a in Aimag.objects.all().order_by("name")]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        # Device -> location__aimag_ref
        if hasattr(queryset.model, "location"):
            return queryset.filter(location__aimag_ref_id=value)

        # Location -> aimag_ref
        if hasattr(queryset.model, "aimag_ref"):
            return queryset.filter(aimag_ref_id=value)

        return queryset


class SumListFilter(admin.SimpleListFilter):
    title = "Сум / Дүүрэг"
    parameter_name = "sum"

    def lookups(self, request, model_admin):
        aimag_id = request.GET.get("aimag")
        qs = SumDuureg.objects.all().order_by("name")
        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)
        return [(str(s.pk), s.name) for s in qs]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        if hasattr(queryset.model, "location"):
            return queryset.filter(location__sum_ref_id=value)

        if hasattr(queryset.model, "sum_ref"):
            return queryset.filter(sum_ref_id=value)

        return queryset


class VerificationBucketFilter(admin.SimpleListFilter):
    title = "Калибровка төлөв"
    parameter_name = "verification_bucket"

    def lookups(self, request, model_admin):
        return (
            ("expired", "Хугацаа дууссан"),
            ("30", "30 хоногт дуусна"),
            ("90", "90 хоногт дуусна"),
            ("ok", "Хэвийн"),
            ("empty", "Огноо байхгүй"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        today = timezone.now().date()
        d30 = today + timedelta(days=30)
        d90 = today + timedelta(days=90)

        if not hasattr(queryset.model, "next_verification_date"):
            return queryset

        if value == "expired":
            return queryset.filter(next_verification_date__lt=today)
        if value == "30":
            return queryset.filter(next_verification_date__gte=today, next_verification_date__lte=d30)
        if value == "90":
            return queryset.filter(next_verification_date__gt=d30, next_verification_date__lte=d90)
        if value == "ok":
            return queryset.filter(next_verification_date__gt=d90)
        if value == "empty":
            return queryset.filter(next_verification_date__isnull=True)
        return queryset