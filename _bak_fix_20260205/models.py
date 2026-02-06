# inventory/models.py
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Газарзүйн функц (алдаа гарахаас сэргийлж try/except-тэй)
try:
    from inventory.geo.district_lookup import lookup_ub_district  # type: ignore
except Exception:  # pragma: no cover
    def lookup_ub_district(lon, lat, base_dir=None):  # type: ignore
        return None


# ============================================================
# 1) ДЦУБ КАТАЛОГ (Лавлах сан)
# ============================================================
class InstrumentCatalog(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "AWS"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "ХАА"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    code = models.CharField(max_length=50, unique=True, verbose_name="Код")
    name_mn = models.CharField(max_length=255, verbose_name="Нэр (MN)")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER, db_index=True)
    unit = models.CharField(max_length=50, blank=True, default="", verbose_name="Нэгж")
    is_active = models.BooleanField(default=True, verbose_name="Идэвхтэй")

    # Шалгалт/калибровкийн цикл (сар)
    verification_cycle_months = models.PositiveIntegerField(
        default=12, verbose_name="Шалгалт/калибровкийн цикл (сар)"
    )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_mn}"

    class Meta:
        verbose_name = "Каталог"
        verbose_name_plural = "Каталог"


# ============================================================
# 2) Аймаг / Сум-Дүүрэг / Байгууллага
# ============================================================
class Aimag(models.Model):
    name = models.CharField(max_length=120, verbose_name="Аймаг/Хот")
    code = models.CharField(max_length=20, blank=True, default="", verbose_name="Код")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Аймаг"
        verbose_name_plural = "Аймаг"


class SumDuureg(models.Model):
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    name = models.CharField(max_length=120, verbose_name="Сум/Дүүрэг")
    is_ub_district = models.BooleanField(default=False, verbose_name="УБ дүүрэг эсэх")

    def __str__(self) -> str:
        return f"{self.aimag} - {self.name}"

    class Meta:
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүрэг"


class Organization(models.Model):
    class OrgType(models.TextChoices):
        OBS_CENTER = "OBS_CENTER", "УЦУОШТ"
        CAL_LAB = "CAL_LAB", "БОХЗТ лаборатори"
        HQ = "HQ", "ЦУОШГ"
        OTHER = "OTHER", "Бусад"

    name = models.CharField(max_length=255, verbose_name="Байгууллага")
    org_type = models.CharField(max_length=20, choices=OrgType.choices, default=OrgType.OTHER, db_index=True)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг")
    is_ub = models.BooleanField(default=False, verbose_name="УБ эсэх")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллага"


# ============================================================
# 3) Байршил (Location)
# ============================================================
class Location(models.Model):
    class LocationType(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "AWS"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "ХАА"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    # ✅ backward-compat alias (зарим хуучин код LOCATION_TYPE_CHOICES гэж хайж болно)
    LOCATION_TYPE_CHOICES = LocationType.choices

    name = models.CharField(max_length=255, verbose_name="Нэр")
    location_type = models.CharField(
        max_length=16,
        choices=LocationType.choices,
        default=LocationType.WEATHER,
        db_index=True,
        verbose_name="Байршлын төрөл",
    )

    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг/Хот")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум/Дүүрэг")

    wmo_index = models.CharField(max_length=10, null=True, blank=True, verbose_name="WMO индекс")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")

    # УБ дүүрэг (text)
    district_name = models.CharField(max_length=100, blank=True, default="", verbose_name="УБ дүүрэг")

    owner_org = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Хариуцагч байгууллага"
    )

    def save(self, *args, **kwargs):
        # УБ дүүрэг автоматаар тодорхойлох (координат байвал)
        try:
            if (
                self.latitude is not None
                and self.longitude is not None
                and self.aimag_ref_id
                and (self.aimag_ref.name or "").strip() == "Улаанбаатар"
            ):
                props = lookup_ub_district(float(self.longitude), float(self.latitude), base_dir=settings.BASE_DIR)
                if props and props.get("name_mn"):
                    self.district_name = props["name_mn"]
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        # name байхгүй branch дээр унахгүй хамгаалалт (хуучин DB/branch)
        label = (
            getattr(self, "name", None)
            or getattr(self, "name_mn", None)
            or getattr(self, "code", None)
            or getattr(self, "wmo_index", None)
            or f"Location#{getattr(self, 'pk', '')}"
        )
        aimag = getattr(self, "aimag_ref", None)
        return f"{label} ({aimag})" if aimag else str(label)

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршил"


# ============================================================
# 4) Хэмжих хэрэгсэл (Device)
# ============================================================
class Device(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "AWS"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "ХАА"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    serial_number = models.CharField(max_length=120, blank=True, default="", verbose_name="Серийн дугаар")
    inventory_code = models.CharField(max_length=120, blank=True, default="", verbose_name="Дотоод код")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER, db_index=True, verbose_name="Төрөл")

    catalog_item = models.ForeignKey(
        InstrumentCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        verbose_name="ДЦУБ жагсаалт",
    )
    other_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Бусад нэр")

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        verbose_name="Байршил",
    )

    STATUS_CHOICES = (
        ("Active", "Ашиглаж байна"),
        ("Inactive", "Идэвхгүй"),
        ("Broken", "Эвдэрсэн"),
        ("Repair", "Засвартай"),
        ("Archived", "Архивласан"),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Active", verbose_name="Төлөв")

    installation_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан")
    lifespan_years = models.PositiveIntegerField(default=10, verbose_name="Ашиглалтын хугацаа (жил)")

    # Calibration / Verification
    last_verification_date = models.DateField(null=True, blank=True, verbose_name="Сүүлд шалгасан/калибровка")
    next_verification_date = models.DateField(null=True, blank=True, verbose_name="Дараагийн шалгалт/калибровка")

    # QR Code
    qr_token = models.UUIDField(null=True, blank=True, db_index=True, editable=False)
    qr_image = models.ImageField(upload_to="qr/devices/", null=True, blank=True)
    qr_revoked_at = models.DateTimeField(null=True, blank=True)
    qr_expires_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        sn = (self.serial_number or "").strip()
        if sn:
            qs = Device.objects.filter(serial_number__iexact=sn)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"serial_number": "Ижил серийн дугаартай багаж аль хэдийн бүртгэлтэй байна."})

    def save(self, *args, **kwargs):
        # 1) next_verification_date автоматаар тооцоолох (ойролцоогоор 30 хоног/сар)
        if self.last_verification_date and self.catalog_item and self.catalog_item.verification_cycle_months:
            self.next_verification_date = self.last_verification_date + timedelta(
                days=int(self.catalog_item.verification_cycle_months) * 30
            )

        # 2) QR token байхгүй бол үүсгэх (admin action дээр шинэчилж болно)
        if not self.qr_token:
            self.qr_token = uuid.uuid4()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        sn = (self.serial_number or "").strip()
        return sn or f"Device#{self.pk}"

    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багаж"


# ============================================================
# 5) Шилжилт хөдөлгөөн & Workflow
# ============================================================
class DeviceMovement(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="movements")
    moved_at = models.DateTimeField(default=timezone.now)

    from_location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="moves_from"
    )
    to_location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="moves_to"
    )

    reason = models.CharField(max_length=255, blank=True, default="")
    moved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.device} -> {self.to_location}"

    class Meta:
        verbose_name = "Шилжилт"
        verbose_name_plural = "Шилжилт"


class WorkflowStatus(models.TextChoices):
    DRAFT = "DRAFT", "Ноорог"
    SUBMITTED = "SUBMITTED", "Хянагдахаар илгээгдсэн"
    APPROVED = "APPROVED", "Батлагдсан"
    REJECTED = "REJECTED", "Татгалзсан"


class MaintenanceService(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="maintenance_services")
    date = models.DateField(default=timezone.localdate)

    reason = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")

    workflow_status = models.CharField(max_length=12, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT)

    # Гүйцэтгэсэн этгээд (гарын авлагаар оруулах)
    performer_type = models.CharField(max_length=20, blank=True, default="")  # "ENGINEER" / "ORG" гэх мэт
    performer_engineer_name = models.CharField(max_length=255, blank=True, default="")
    performer_org_name = models.CharField(max_length=255, blank=True, default="")

    # Системийн хэрэглэгчтэй холбох (сонголтоор)
    performer_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="performed_maintenances"
    )

    def __str__(self) -> str:
        return f"{self.device} - {self.date}"

    class Meta:
        verbose_name = "Засвар үйлчилгээ"
        verbose_name_plural = "Засвар үйлчилгээ"


class ControlAdjustment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="control_adjustments")
    date = models.DateField(default=timezone.localdate)

    result = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")

    workflow_status = models.CharField(max_length=12, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT)

    performer_type = models.CharField(max_length=20, blank=True, default="")
    performer_engineer_name = models.CharField(max_length=255, blank=True, default="")
    performer_org_name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self) -> str:
        return f"{self.device} - {self.date}"

    class Meta:
        verbose_name = "Хяналт тохируулга"
        verbose_name_plural = "Хяналт тохируулга"


class MaintenanceEvidence(models.Model):
    service = models.ForeignKey(MaintenanceService, on_delete=models.CASCADE, related_name="evidences")
    file = models.FileField(upload_to="evidence/maintenance/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Засварын нотлох баримт"
        verbose_name_plural = "Засварын нотлох баримтууд"


class ControlEvidence(models.Model):
    adjustment = models.ForeignKey(ControlAdjustment, on_delete=models.CASCADE, related_name="evidences")
    file = models.FileField(upload_to="evidence/control/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Хяналтын нотлох баримт"
        verbose_name_plural = "Хяналтын нотлох баримтууд"


# ============================================================
# 6) Сэлбэг
# ============================================================
class SparePartOrder(models.Model):
    order_no = models.CharField(max_length=50, unique=True)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.order_no

    class Meta:
        verbose_name = "Сэлбэгийн захиалга"
        verbose_name_plural = "Сэлбэгийн захиалга"


class SparePartItem(models.Model):
    order = models.ForeignKey(SparePartOrder, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    serial_number = models.CharField(max_length=120, blank=True, default="")

    target_device = models.ForeignKey(
        Device, on_delete=models.SET_NULL, null=True, blank=True, related_name="spare_parts", verbose_name="Суурилуулах багаж"
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Сэлбэг (мөр)"
        verbose_name_plural = "Сэлбэг (мөр)"


# ============================================================
# 7) Профайл + Лог
# ============================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.user.username

    class Meta:
        verbose_name = "Хэрэглэгчийн профайл"
        verbose_name_plural = "Хэрэглэгчийн профайл"


class AuthAuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    username = models.CharField(max_length=150, blank=True, default="")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.CharField(max_length=50, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Нэвтрэлтийн лог"
        verbose_name_plural = "Нэвтрэлтийн лог"
