# inventory/admin_mixins.py
from __future__ import annotations

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
    - UserProfile / aimag байхгүй үед: эвдрэхгүй (empty queryset)

    Config:
      aimag_filter_path: str | None
        Ж: "aimag_ref" эсвэл "location__aimag_ref"
        Өгөөгүй бол автоматаар таамаглана.
    """

    aimag_filter_path: str | None = None

    def is_aimag_engineer(self, request) -> bool:
        u = getattr(request, "user", None)
        if not u or not u.is_authenticated:
            return False
        if getattr(u, "is_superuser", False):
            return False
        return u.groups.filter(name=AIMAG_ENGINEER_GROUP).exists()

    def get_user_aimag(self, request):
        """
        ✅ Танай models.py дээр UserProfile.user related_name="profile"
        гэхдээ зарим branch дээр userprofile гэж байж магадгүй тул 2-ыг нь support хийнэ.
        """
        u = request.user
        profile = getattr(u, "profile", None) or getattr(u, "userprofile", None)
        if not profile:
            return None
        return getattr(profile, "aimag", None) or getattr(profile, "aimag_ref", None)

    def resolve_aimag_filter_path(self):
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
                self.aimag_filter_path = f"{lf}__aimag_ref"
                return self.aimag_filter_path

        self.aimag_filter_path = None
        return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if getattr(request.user, "is_superuser", False):
            return qs

        if not self.is_aimag_engineer(request):
            return qs

        aimag = self.get_user_aimag(request)
        path = self.resolve_aimag_filter_path()

        if not aimag or not path:
            return qs.none()

        return qs.filter(**{path: aimag})

    def has_delete_permission(self, request, obj=None):
        if getattr(request.user, "is_superuser", False):
            return True
        if self.is_aimag_engineer(request):
            return False
        return super().has_delete_permission(request, obj=obj)


class GlobalAdminFilterMixin(AimagScopedAdminMixin):
    """
    admin.py дээр ашиглагдаж байсан хуучин интерфейсийг хадгалсан production mixin.

    - AimagEngineer scope: AimagScopedAdminMixin (aimag_filter_path)
    - Admin filters (GET): aimag, sum, kind гэсэн параметр байвал нэмэлтээр filter хийнэ
    - aimag_path/sum_path/kind_path гэдэг атрибутуудыг (хуучин) дэмжинэ
      Ж: aimag_path="location__aimag_ref", sum_path="location__sum_ref", kind_path="kind"
    """

    # legacy paths
    aimag_path: str | None = None
    sum_path: str | None = None
    kind_path: str | None = None

    def _get_param(self, request, key: str) -> str:
        return (request.GET.get(key) or "").strip()

    def _resolve_scope_path_from_aimag_path(self):
        # AimagScopedAdminMixin нь aimag_filter_path-аар scope хийнэ
        if getattr(self, "aimag_filter_path", None):
            return self.aimag_filter_path
        if getattr(self, "aimag_path", None):
            self.aimag_filter_path = self.aimag_path
            return self.aimag_filter_path
        return self.resolve_aimag_filter_path()

    def get_queryset(self, request):
        # 1) engineer scope (aimag)
        self._resolve_scope_path_from_aimag_path()
        qs = super().get_queryset(request)

        # 2) optional GET filters (admin/report style)
        # зөвхөн staff орчинд хэрэглэхэд OK; буруу байвал зүгээр л алгасна.
        aimag_id = self._get_param(request, "aimag")
        sum_id = self._get_param(request, "sum")
        kind = self._get_param(request, "kind")

        try:
            if aimag_id and self.aimag_path:
                qs = qs.filter(**{f"{self.aimag_path}__id": int(aimag_id)})
        except Exception:
            pass
        try:
            if sum_id and self.sum_path:
                qs = qs.filter(**{f"{self.sum_path}__id": int(sum_id)})
        except Exception:
            pass
        try:
            if kind and self.kind_path:
                qs = qs.filter(**{self.kind_path: kind})
        except Exception:
            pass

        return qs
