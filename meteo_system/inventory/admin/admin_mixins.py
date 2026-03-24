from django.utils.html import format_html


class VerificationBadgeMixin:
    @staticmethod
    def verification_badge(obj):
        bucket = obj.verification_bucket()
        label_map = {
            "expired": ("red", "Хугацаа дууссан"),
            "due_30": ("orange", "30 хоногт"),
            "due_90": ("blue", "90 хоногт"),
            "ok": ("green", "Хэвийн"),
            "unknown": ("gray", "Тодорхойгүй"),
        }
        color, label = label_map.get(bucket, ("gray", "Тодорхойгүй"))
        return format_html(
            '<span style="padding:2px 8px;border-radius:10px;background:{};color:white;">{}</span>',
            color,
            label,
        )

    verification_badge.short_description = "Шалгалтын төлөв"


class AimagRestrictedMixin:
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        profile = getattr(request.user, "profile", None)

        if request.user.is_superuser:
            return qs

        if profile and getattr(profile, "role", None) == "aimag_engineer":
            aimag = getattr(profile, "aimag", None)
            if aimag is not None:
                return qs.filter(location__aimag_ref=aimag)

        return qs