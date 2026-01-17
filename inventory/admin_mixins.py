from django.core.exceptions import FieldDoesNotExist

AIMAG_ENGINEER_GROUP = "AimagEngineer"


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


class AimagScopedAdminMixin:
    """
    - Superuser: шүүгдэхгүй
    - AimagEngineer: зөвхөн өөрийн аймаг
    - Delete: AimagEngineer -> хаана
    - UserProfile байхгүй үед: эвдрэхгүй (empty queryset)
    """
    aimag_filter_path: str | None = None  # ж: "aimag_ref" эсвэл "location__aimag_ref"

    def is_aimag_engineer(self, request) -> bool:
        u = request.user
        return u.is_authenticated and u.groups.filter(name=AIMAG_ENGINEER_GROUP).exists()

    def get_user_aimag(self, request):
        profile = getattr(request.user, "userprofile", None)
        return getattr(profile, "aimag", None) if profile else None

    def resolve_aimag_filter_path(self):
        """
        Хэрэв тохиргоо өгөөгүй бол автоматаар таамаглана:
        1) aimag_ref / aimag_fk / aimag
        2) location_ref / location -> location_ref__aimag_ref
        """
        if self.aimag_filter_path:
            return self.aimag_filter_path

        m = self.model
        # Direct aimag FK
        for f in ("aimag_ref", "aimag_fk", "aimag"):
            if _has_field(m, f):
                self.aimag_filter_path = f
                return self.aimag_filter_path

        # Via location
        for lf in ("location_ref", "location"):
            if _has_field(m, lf):
                # Location дээр aimag_ref байх ёстой (танайд энэ байгаа)
                self.aimag_filter_path = f"{lf}__aimag_ref"
                return self.aimag_filter_path

        self.aimag_filter_path = None
        return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if not self.is_aimag_engineer(request):
            return qs

        aimag = self.get_user_aimag(request)
        path = self.resolve_aimag_filter_path()

        if not aimag or not path:
            return qs.none()

        return qs.filter(**{path: aimag})

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if self.is_aimag_engineer(request):
            return False
        return super().has_delete_permission(request, obj=obj)
