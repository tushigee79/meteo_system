# inventory/models.py (FINAL - production-safe)
from __future__ import annotations

import io
import uuid
from datetime import date, timedelta
from io import BytesIO
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from inventory.geo.district_lookup import lookup_ub_district


# ============================================================
# 1) ДЦУБ КТЛОГ (Лавлах ан)
# ============================================================
class InstrumentCatalog(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "Автомат станц"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "Хөдөө аж ахуй"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    code = models.CharField(max_length=50, unique=True, verbose_name="Код")
    name_mn = models.CharField(max_length=255, verbose_name="р (MN)")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER, db_index=True)
    unit = models.CharField(max_length=50, blank=True, default="", verbose_name="гж")
    is_active = models.BooleanField(default=True, verbose_name="Идэвхтэй")

    # verification cycle (optional)
    verification_cycle_months = models.PositiveIntegerField(default=12, verbose_name="Шалгалт/калибровкийн цикл (ар)")

    def __str__(self):
        return f"{self.code} - {self.name_mn}"

    class Meta:
        verbose_name = "Каталог"
        verbose_name_plural = "Каталог"


# ============================================================
# 2) Аймаг / Сум-Дүүрг
# ============================================================
class Aimag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Аймаг")
    code = models.CharField(max_length=20, blank=True, default="", verbose_name="Код")

    def save(self, *args, **kwargs):
        if self.name:
            s = self.name.strip()
            s = s.replace("–", "-").replace("—", "-").replace("−", "-")
            s = " ".join(s.split())
            self.name = s.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Аймаг"
        verbose_name_plural = "Аймгууд"
        ordering = ["name"]


class SumDuureg(models.Model):
    name = models.CharField(max_length=150, verbose_name="р")

    aimag_ref = models.ForeignKey(
        Aimag,
        on_delete=models.CASCADE,
        related_name="sums",          # ✅ ЗӨВ (ЗӨВХӨ ЭД)
        verbose_name="Аймаг/Улаанбаатар",
        null=True,
        blank=True,
    )

    is_ub_district = models.BooleanField(default=False)

    def __str__(self):
        return self.name


    code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Код",
        help_text="Албан ёсны сум/дүүргийн код (ж: 011, 123, UB-01 гх мт)",
    )

    is_ub_district = models.BooleanField(
        default=False,
        verbose_name="УБ дүүрэг",
    )

    class Meta:
        verbose_name = "Сум / Дүүрэг"
        verbose_name_plural = "Сум / Дүүргүүд"
        ordering = ["aimag_ref__name", "name"]

    def __str__(self):
        return f"{self.code or '-'} – {self.name}"

# ============================================================
# 3) Байгууллага
# ============================================================
class Organization(models.Model):
    class OrgType(models.TextChoices):
        OBS_CENTER = "OBS_CENTER", "УЦУОШТ"
        CAL_LAB = "CAL_LAB", "БОХЗТ лаборатори"
        HQ = "HQ", "ЦУОШГ"
        OTHER = "OTHER", "Буад"

    name = models.CharField(max_length=255, verbose_name="Байгууллага")
    org_type = models.CharField(
        max_length=20,
        choices=OrgType.choices,
        default=OrgType.OTHER,
        db_index=True,
    )

    aimag_ref = models.ForeignKey(
        Aimag,
        on_delete=models.SET_NULL,
        related_name="organizations",   # ✅ ЗӨВ (ЭД Л)
        verbose_name="Аймаг/Улаанбаатар",
        null=True,
        blank=True,
    )

    is_ub = models.BooleanField(default=False)

    def __str__(self):
        return self.name


    is_ub = models.BooleanField(default=False, verbose_name="УБ х")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллагууд"

# ============================================================
# 4) Байршил (Location)  ✅ FIXED
# ============================================================
class Location(models.Model):

    class LocationType(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "Автомат станц"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "Хөдөө аж ахуй"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.WEATHER,
        verbose_name="Байршлын төрөл",
    )

    # … бусад талбарууд чинь хэвээр


    # ✅ backward-compat alias
    LOCATION_TYPE_CHOICES = LocationType.choices
    LOCATION_TYPES = LOCATION_TYPE_CHOICES 

    name = models.CharField(max_length=255, verbose_name="р")  # ✅ заавал
    location_type = models.CharField(
        max_length=16,
        choices=LocationType.choices,
        default=LocationType.WEATHER,
        db_index=True,
        verbose_name="Байршлын төрөл",
    )

    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум/Дүүрг")

    wmo_index = models.CharField(max_length=10, null=True, blank=True, verbose_name="WMO индек")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")

    district_name = models.CharField(max_length=100, blank=True, default="", verbose_name="УБ дүүрэг")

    owner_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Хариуцагч",
    )
    
    parent_location = models.ForeignKey(
    "self",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="child_locations",
    verbose_name="Дэд байршил (эх станц)",
)


    def save(self, *args, **kwargs):
        # УБ дүүрэг автоматаар тодорхойлох (байвал)
        try:
            if (
                self.latitude is not None
                and self.longitude is not None
                and self.aimag_ref
                and (self.aimag_ref.name or "").strip() == "Улаанбаатар"
            ):
                props = lookup_ub_district(float(self.longitude), float(self.latitude), base_dir=settings.BASE_DIR)
                if props and props.get("name_mn"):
                    self.district_name = props["name_mn"]
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        def pick(*vals):
            for v in vals:
                if v is None:
                    continue
                s = str(v).strip()
                if s:
                    return s
            return ""

        label = pick(
            getattr(self, "name", None),
            getattr(self, "wmo_index", None),
            f"Location#{getattr(self, 'pk', '')}",
        )
        aimag = getattr(self, "aimag_ref", None)
        return f"{label} ({aimag})" if aimag else label

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршил"


# ============================================================
# 5) Хэмжих хэрэгсэл (Device)
# ============================================================
class Device(models.Model):
    class Kind(models.TextChoices):
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AWS = "AWS", "Автомат станц"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "Хөдөө аж ахуй"
        ETALON = "ETALON", "Эталон"
        OTHER = "OTHER", "Бусад"

    serial_number = models.CharField(max_length=120, blank=True, default="", verbose_name="Серийн дугаар")
    inventory_code = models.CharField(max_length=120, blank=True, default="", verbose_name="Дотоод код")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER, db_index=True, verbose_name="Төрөл")

    catalog_item = models.ForeignKey(
        InstrumentCatalog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devices", verbose_name="ДЦУБ жагаалт",
    )
    other_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Бусад нэр")

    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devices", verbose_name="Байршил",
    )
    
    system = models.ForeignKey(
        "MeasurementSystem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="components",
        help_text="Radar / Aerology / AWS system this device belongs to",
    )

    STATUS_CHOICES = (
        ("Active", "Ашиглаж байна"),
        ("Inactive", "Идэвхгүй"),
        ("Broken", "Эвдэрсэн"),
        ("Archived", "Архивлсан"),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Active", verbose_name="Төлөв")

    installation_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан")
    lifespan_years = models.PositiveIntegerField(default=10, verbose_name="Ашиглалтын хугацаа (жил)")

    # Calibration / Verification tracking (✅ ганцхан удаа)
    last_verification_date = models.DateField(null=True, blank=True, verbose_name="Сүүлд шалгасан/калибровка")
    next_verification_date = models.DateField(null=True, blank=True, verbose_name="Дараагийн шалгалт/калибровка")

    # QR
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_image = models.ImageField(upload_to="qr/", blank=True, null=True)

    def get_qr_public_url(self) -> str:
        base_url = getattr(settings, "SITE_BASE_URL", "https://meteo.gov.mn").rstrip("/")
        return f"{base_url}/qr/public/{self.qr_token}/"

    def generate_qr_code(self) -> None:
        try:
            import qrcode  # type: ignore
        except Exception as e:
            raise ValidationError(f"qrcode баталгаажуулсан байх ётой. ({e})")

        qr_data = self.get_qr_public_url()
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        serial = self.serial_number or f"dev{self.pk or 'new'}"
        token8 = self.qr_token.hex[:8]
        filename = f"qr_{serial}_{token8}.png"

        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = uuid.uuid4()

        if self.last_verification_date:
            self.next_verification_date = self.compute_next_verification_date()

        token_changed = False
        if self.pk:
            old = self.__class__.objects.filter(pk=self.pk).only("qr_token").first()
            if old and old.qr_token != self.qr_token:
                token_changed = True

        if (not self.qr_image) or token_changed:
            self.generate_qr_code()

        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багаж"

# ============================================================
# 6) Measurement System (Radar / AWS / Aerology)
# ============================================================
class MeasurementSystem(models.Model):
    class SystemType(models.TextChoices):
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AWS = "AWS", "Автомат станц"

    class Status(models.TextChoices):
        OPERATIONAL = "OPERATIONAL", "Ажиллаж байна"
        DEGRADED = "DEGRADED", "Хязгаарлагдмал"
        DOWN = "DOWN", "Ажиллахгүй"

    name = models.CharField(max_length=255, verbose_name="Системийн нэр")

    system_type = models.CharField(
        max_length=20,
        choices=SystemType.choices,
        verbose_name="Системийн төрөл",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="systems",
        verbose_name="Байршил",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPERATIONAL,
        verbose_name="Төлөв",
    )

    installed_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан огноо")

    owner_org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="systems",
        verbose_name="Хариуцагч байгууллага",
    )

    note = models.TextField(blank=True, default="", verbose_name="Тайлбар")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_system_type_display()})"

    class Meta:
        verbose_name = "Систем"
        verbose_name_plural = "Системүүд"


# ============================================================
# 7) DeviceMovement
# ============================================================
class DeviceMovement(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="movements")
    moved_at = models.DateTimeField(default=timezone.now)
    from_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="moves_from")
    to_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="moves_to")
    reason = models.CharField(max_length=255, blank=True, default="")
    moved_by = models.ForeignKey("UserProfile", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.device} {self.from_location} -> {self.to_location}"

    class Meta:
        verbose_name = "Шилжилт"
        verbose_name_plural = "Шилжилт"


# ============================================================
# 8 Workflow + Service Models
# ============================================================
class WorkflowStatus(models.TextChoices):
    DRAFT = "DRAFT", "Ноорог"
    SUBMITTED = "SUBMITTED", "Хянагдахаар илгээгдсэн"
    APPROVED = "APPROVED", "Батлагдсан"
    REJECTED = "REJECTED", "Татгалзсан"


class BaseWorkflowModel(models.Model):
    """MaintenanceService / ControlAdjustment дээр давтагдаж байсан нийтлэг талбарууд.

    NOTE:
    - Abstract model тул DB др хүснэгт үүсэхгүй, харин хүүхд модель дээр талбарууд хуулбарлагдана.
    - `device` FK-гийн reverse accessor мөргөлдөхөө ргийлж base др `related_name="+"` ашигласан.
      Хүүхэд модель дээр device-ийг override хийж тус тсуын related_name-ийг хадгалана.
    """

    PERFORMER_TYPES = [
        ("ENGINEER", "Инженер"),
        ("ORG", "Байгууллага"),
    ]

    # ✅ reverse name clash-аа ргийлж '+' (child др override хийж өгнө)
    device = models.ForeignKey(
        "inventory.Device",
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Багаж / Төхөөрөмж",
    )

    date = models.DateField(default=timezone.localdate, verbose_name="Огноо")

    performer_type = models.CharField(
        max_length=20,  # existing schema-тай нийцүүлх (өмнө нь 20 байан)
        choices=PERFORMER_TYPES,
        default="ENGINEER",
        blank=True,  # хуучин мөрүүдд хооон утга байж болзошгүй
        verbose_name="Хийсэн этгээд (төрөл)",
    )
    performer_engineer_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Хийсэн инженер (нэр)"
    )
    performer_org_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Хийсэн байгууллага (нэр)"
    )

    note = models.TextField(blank=True, default="", verbose_name="Тайлбар / тэмдэглэл")

    # Workflow талбарууд (одоогийн models.py-д байгаа minimum set)
    workflow_status = models.CharField(
        max_length=12,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
        verbose_name="Workflow төлөв",
    )

    # TODO (чиний өмнөх admin/workflow логикоо хамаарч нмн):
    # submitted_by, submitted_at, approved_by, approved_at, rejected_by, rejected_at гх мт

    class Meta:
        abstract = True

    def clean(self):
        """performer_type-оо хамаарч зөвхөн нэг талбар шаардлагатай болгоно."""
        super().clean()

        ptype = (self.performer_type or "").strip().upper() or "ENGINEER"
        self.performer_type = ptype

        if ptype == "ENGINEER":
            if not (self.performer_engineer_name or "").strip():
                raise ValidationError({"performer_engineer_name": "Инженерийн нэр заавал бөглөгдөнө."})
            # Org талбарыг цврлн
            self.performer_org_name = ""
        elif ptype == "ORG":
            if not (self.performer_org_name or "").strip():
                raise ValidationError({"performer_org_name": "Байгууллагын нэр заавал бөглөгдөнө."})
            # Engineer талбарыг цврлн
            self.performer_engineer_name = ""
        else:
            raise ValidationError({"performer_type": "Хийсэн этгээдийн төрөл буруу байна (ENGINEER / ORG)."})

    def __str__(self):
        # хүүхд модель др device override хийн тул нд OK
        return f"{self.device} - {self.date}"


class MaintenanceService(BaseWorkflowModel):
    # ✅ child др reverse accessor-ийг хадгална (өмнөх кодтой нийцтй)
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="maintenance_services", verbose_name="Багаж / Төхөөрөмж")

    REASONS = [
        ("NORMAL", "Хэвийн засвар үйлчилгээ"),
        ("LIMITED", "Хзгаарлагдмал ажиллагаа"),
        ("NOT_WORKING", "Ажиллагаагүй болон"),
    ]
    reason = models.CharField(
        max_length=20,
        choices=REASONS,
        default="NORMAL",
        verbose_name="Засвар хийсэн шалтгаан",
    )

    class Meta:
        verbose_name = "Засвар үйлчилгээ"
        verbose_name_plural = "Завар үйлчилгээ"


class ControlAdjustment(BaseWorkflowModel):
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="control_adjustments", verbose_name="Багаж / Төхөөрөмж")

    RESULTS = [
        ("PASS", "PASS - Хэвийн"),
        ("LIMITED", "Хзгаарлагдмал"),
        ("FAIL", "FAIL - Ажиллагаагүй"),
    ]
    result = models.CharField(
        max_length=20,
        choices=RESULTS,
        default="PASS",
        verbose_name="Үр дүн",
    )

    class Meta:
        verbose_name = "Хяналт тохируулга"
        verbose_name_plural = "Хяналт тохируулга"
class MaintenanceEvidence(models.Model):
    service = models.ForeignKey(MaintenanceService, on_delete=models.CASCADE, related_name="evidences")
    file = models.FileField(upload_to="evidence/maintenance/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence#{self.pk}"

    class Meta:
        verbose_name = "Засварын нотолгоо"
        verbose_name_plural = "Засварын нотолгоо"


class ControlEvidence(models.Model):
    adjustment = models.ForeignKey(
    ControlAdjustment,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    verbose_name="Тохируулга"
)

    file = models.FileField(upload_to="evidence/control/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence#{self.pk}"

    class Meta:
        verbose_name = "Тохируулагын нотолгоо"
        verbose_name_plural = "Тохируулагын нотолгоо"


# ============================================================
# 9) Spare Parts
# ============================================================
class SparePartOrder(models.Model):
    order_no = models.CharField(max_length=50, unique=True)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_no

    class Meta:
        verbose_name = "Сэлбэгийн захиалга"
        verbose_name_plural = "Сэлбэгийн захиалга"


class SparePartItem(models.Model):
    order = models.ForeignKey(SparePartOrder, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    serial_number = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сэлбэг (мөр)"
        verbose_name_plural = "Сэлбэг (мөр)"


# ============================================================
# 10) User Profile + Auth Audit
# ============================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Профайл"
        verbose_name_plural = "Профайл"


class AuthAuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    username = models.CharField(max_length=150, blank=True, default="")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.CharField(max_length=50, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.created_at} {self.action} {self.username}"

    class Meta:
        verbose_name = "Нэвтрэлтийн лог"
        verbose_name_plural = "Нэвтрэлтийн лог"


# Optional models (if your migrations include them)
class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AuditEvent#{self.pk}"

class WorkflowAuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50, blank=True, default="")
    note = models.TextField(blank=True, default="")

    def __str__(self):
        return f"WorkflowAuditLog#{self.pk}"

class WorkflowDailyAgg(models.Model):
    day = models.DateField(default=timezone.localdate)

    def __str__(self):
        return str(self.day)

