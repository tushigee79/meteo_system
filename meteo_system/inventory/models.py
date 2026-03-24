# inventory/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import timedelta

from django.contrib.auth.models import User   # ✅ ЗААВАЛ

import uuid
from io import BytesIO
from django.core.files.base import ContentFile

from inventory.geo.district_lookup import lookup_ub_district


# ============================================================
# 1) ДЦУБ КАТАЛОГ (Лавлах сан)
# ============================================================
class InstrumentCatalog(models.Model):
    KIND_CHOICES = [
        ("WEATHER", "Цаг уур"),
        ("HYDRO", "Ус судлал"),
        ("AWS", "AWS"),
        ("RADAR", "Радар"),
        ("AEROLOGY", "Аэрологи"),
        ("AGRO", "ХАА"),
        ("ETALON", "Эталон"),
        ("OTHER", "Бусад"),
    ]

    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default="OTHER",
        verbose_name="Төрөл",
    )

    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Код",
    )

    name_mn = models.CharField(max_length=255, verbose_name="Нэр")

    unit = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Нэгж",
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    verification_cycle_months = models.PositiveIntegerField(
        default=0,
        verbose_name="Шалгалт/калибровкийн цикл (сар)",
        help_text="0 бол автоматаар тооцохгүй (manual). Ж: 12 = жил бүр."
    )

    class Meta:
        verbose_name = "ДЦУБ Каталог"
        verbose_name_plural = "ДЦУБ Каталог"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} – {self.name_mn}"


# ============================================================
# 2) Захиргааны нэгж ба Байгууллага
# ============================================================
class Aimag(models.Model):
    name = models.CharField(max_length=100, verbose_name="Аймаг/Нийслэлийн нэр")
    code = models.CharField(max_length=20, blank=True, default="", verbose_name="Код")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Аймаг/Нийслэл"
        verbose_name_plural = "Аймаг/Нийслэл"


class SumDuureg(models.Model):
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүргийн нэр")
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name="sums")
    code = models.CharField(max_length=20, blank=True, default="", verbose_name="Код")

    is_ub_district = models.BooleanField(default=False, verbose_name="УБ-ын 9 дүүрэг үү?")

    def __str__(self):
        return f"{self.aimag} - {self.name}"

    class Meta:
        unique_together = ("aimag", "name")
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүрэг"


class Organization(models.Model):
    ORG_TYPES = [
        ("CENTER", "НЦУТ"),
        ("CAL_LAB", "БОХЗТЛ"),
        ("OBS_CENTER", "УЦУОШТ"),
    ]

    name = models.CharField(max_length=255, unique=True, verbose_name="Байгууллагын нэр")
    org_type = models.CharField(max_length=20, choices=ORG_TYPES, default="OBS_CENTER", verbose_name="Төрөл")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг/Нийслэл")
    is_ub = models.BooleanField(default=False, verbose_name="Улаанбаатар хот уу?")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллагууд"


# ============================================================
# 3) Байршил
# ============================================================
class Location(models.Model):
    LOCATION_TYPES = [
        ("WEATHER", "Цаг уур"),
        ("HYDRO", "Ус судлал"),
        ("AWS", "AWS"),
        ("ETALON", "Эталон"),
        ("RADAR", "Радар"),
        ("AEROLOGY", "Аэрологи"),
        ("AGRO", "Хөдөө аж ахуй"),
        ("OTHER", "Бусад"),
    ]


    # Backward-compat aliases used by dashboards/filters
    LOCATION_TYPE_CHOICES = LOCATION_TYPES
    TYPE_CHOICES = LOCATION_TYPES
    name = models.CharField(max_length=255, verbose_name="Нэр")

    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPES,
        default="WEATHER",
        verbose_name="Байршлын төрөл",
    )

    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум/Дүүрэг")

    wmo_index = models.CharField(max_length=10, null=True, blank=True, verbose_name="WMO индекс")
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

    def save(self, *args, **kwargs):
        try:
            if (
                self.latitude is not None
                and self.longitude is not None
                and self.aimag_ref
                and self.aimag_ref.name.strip() == "Улаанбаатар"
            ):
                props = lookup_ub_district(float(self.longitude), float(self.latitude), base_dir=settings.BASE_DIR)
                if props and props.get("name_mn"):
                    self.district_name = props["name_mn"]
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.aimag_ref})"

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
        ETALON = "ETALON", "Эталон"
        RADAR = "RADAR", "Радар"
        AEROLOGY = "AEROLOGY", "Аэрологи"
        AGRO = "AGRO", "Хөдөө аж ахуй"
        OTHER = "OTHER", "Бусад"

    # Backward-compat: some dashboards expect KIND_CHOICES
    KIND_CHOICES = Kind.choices

    STATUS_CHOICES = [
        ("Active", "Ашиглагдаж буй"),
        ("Broken", "Эвдрэлтэй"),
        ("Repair", "Засварт"),
        ("Spare", "Нөөц"),
        ("Retired", "Хасагдсан"),
    ]

    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")
    inventory_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Бараа материалын код")
    manufacturer = models.CharField(max_length=100, blank=True, null=True, verbose_name="Үйлдвэрлэгч")
    commissioned_date = models.DateField(blank=True, null=True, verbose_name="Ашиглалтад орсон огноо")

    # QR token (used for QR lookup/public page)
    qr_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="QR токен",
    )

    # QR security / lifecycle
    qr_expires_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="QR хүчинтэй хугацаа")
    qr_revoked_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="QR хүчингүй болгосон огноо")



    # QR image (generated automatically on save if missing)
    qr_image = models.ImageField(upload_to="qr/devices/", null=True, blank=True, verbose_name="QR зураг")

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.WEATHER,
        verbose_name="Төрөл",
    )

    
    def save(self, *args, **kwargs):
        # 1. Хэрэв QR зураг байхгүй бол шинээр үүсгэнэ
        if not self.qr_image:
            # QR кодын тохиргоо
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # QR дотор хадгалах өгөгдөл (Public URL)
            # Жишээ нь: https://meteo.gov.mn/qr/public/TOKEN/
            # Одоогоор зөвхөн token-оо хийж турших эсвэл домайнаа хатуу бичиж болно
            qr_data = f"/qr/public/{self.qr_token}/" 
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Зураг болгох
            img = qr.make_image(fill_color="black", back_color="white")

            # Санах ой руу хадгалах (Buffer)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Файлын нэр өгөх (qr_сериал.png)
            filename = f"qr_{self.serial_number}.png"
            
            # ImageField-д хадгалах (save=False нь дахин loop-д орохоос сэргийлнэ)
            self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=False)

        # 2. Үндсэн хадгалах үйлдлийг дуудах
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    catalog_item = models.ForeignKey(
        InstrumentCatalog,
        on_delete=models.PROTECT,
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

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Active", verbose_name="Төлөв")
    installation_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан")
    lifespan_years = models.PositiveIntegerField(default=10, verbose_name="Ашиглалтын хугацаа (жил)")


    # ============================================================
    # Calibration / Verification tracking
    # ============================================================
    last_verification_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Сүүлд шалгасан/калибровка",
    )
    next_verification_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Дараагийн шалгалтын огноо",
    )

    def clean(self):
        super().clean()

        # catalog kind must match device kind
        if self.catalog_item and self.catalog_item.kind != self.kind:
            raise ValidationError({"catalog_item": "Каталогийн төрөл таарахгүй"})

        # OTHER requires other_name
        if self.kind == self.Kind.OTHER and not (self.other_name or "").strip():
            raise ValidationError({"other_name": "“Бусад” сонгосон бол нэр заавал бөглөнө."})

    def compute_next_verification_date(self):
        """Auto-calc next_verification_date using catalog_item.verification_cycle_months."""
        if not self.last_verification_date:
            return None

        months = 0
        try:
            months = int(getattr(self.catalog_item, "verification_cycle_months", 0) or 0)
        except Exception:
            months = 0

        if months <= 0:
            return None

        try:
            from dateutil.relativedelta import relativedelta  # type: ignore
            return self.last_verification_date + relativedelta(months=+months)
        except Exception:
            # fallback: 30-day months approximation
            return self.last_verification_date + timedelta(days=30 * months)

    def verification_bucket(self, today=None):
        """Return one of: expired / due_30 / due_90 / ok / unknown."""
        if today is None:
            today = timezone.localdate()

        d = self.next_verification_date
        if not d:
            return "unknown"
        if d < today:
            return "expired"

        delta = (d - today).days
        if delta <= 30:
            return "due_30"
        if delta <= 90:
            return "due_90"
        return "ok"

    def __str__(self):
        name = self.catalog_item.name_mn if self.catalog_item else (self.other_name or "-")
        return f"{self.serial_number} - {name}"

    def save(self, *args, **kwargs):
        """
        Save + (1) auto QR generation,
               (2) movement history when location changes,
               (3) auto next verification date.
        """
        old_location_id = None

        # 0) Auto-calc next verification date
        try:
            computed = self.compute_next_verification_date()
            if computed:
                self.next_verification_date = computed
        except Exception:
            pass

        # 1) QR expiry: 12 months (≈365 days) from creation
        if not self.qr_expires_at:
            self.qr_expires_at = timezone.now() + timedelta(days=365)

        # 2) Track old location (for movement history)
        if self.pk:
            try:
                old_location_id = (
                    Device.objects.filter(pk=self.pk)
                    .values_list("location_id", flat=True)
                    .first()
                )
            except Exception:
                old_location_id = None

        super().save(*args, **kwargs)

        # 3) Write movement history if location changed
        try:
            new_location_id = self.location_id
            if self.pk and old_location_id != new_location_id:
                DeviceMovement.objects.create(
                    device=self,
                    from_location_id=old_location_id,
                    to_location_id=new_location_id,
                    moved_at=timezone.now(),
                    reason="",
                    moved_by=None,
                )
        except Exception:
            pass

        # 4) Generate QR if missing
        if not self.qr_image:
            try:
                import os
                import qrcode
                from io import BytesIO
                from django.core.files.base import ContentFile

                target_dir = os.path.join(str(settings.MEDIA_ROOT), "qr", "devices")
                os.makedirs(target_dir, exist_ok=True)

                serial = (self.serial_number or "").strip()
                base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
                path = f"/qr/public/{self.qr_token}/"
                qr_data = (base + path) if base else path

                img = qrcode.make(qr_data)
                buf = BytesIO()
                img.save(buf, format="PNG")

                serial_part = (serial or "no_serial").strip() or "no_serial"
                fname = f"device_{self.pk}_{serial_part}.png".replace(" ", "_")
                self.qr_image.save(fname, ContentFile(buf.getvalue()), save=False)
                super().save(update_fields=["qr_image"])
            except Exception as e:
                print("❌ QR generation failed:", repr(e))

    class Meta:
        verbose_name = "Хэмжих хэрэгсэл"
        verbose_name_plural = "Хэмжих хэрэгсэл"


# ============================================================
# ✅ Device Movement History (WMO metadata)
# ============================================================
class DeviceMovement(models.Model):
    """Багаж шилжилт хөдөлгөөний түүх.

    device.location өөрчлөгдөх бүрт from/to байршил, огноо, шалтгаан, шилжүүлсэн этгээдийг хадгална.
    """

    device = models.ForeignKey(
        "inventory.Device",
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="Багаж",
    )
    from_location = models.ForeignKey(
        "inventory.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moved_from",
        verbose_name="Хаанаас",
    )
    to_location = models.ForeignKey(
        "inventory.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moved_to",
        verbose_name="Хаашаа",
    )
    moved_at = models.DateTimeField(default=timezone.now, verbose_name="Шилжүүлсэн огноо/цаг")
    reason = models.CharField(max_length=255, blank=True, default="", verbose_name="Шалтгаан")
    moved_by = models.ForeignKey(
        "inventory.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_movements",
        verbose_name="Шилжүүлсэн (UserProfile)",
    )

    class Meta:
        verbose_name = "Багаж шилжилт (түүх)"
        verbose_name_plural = "Багаж шилжилтийн түүх"
        ordering = ["-moved_at", "-id"]
        indexes = [
            models.Index(fields=["moved_at"]),
            models.Index(fields=["device", "moved_at"]),
        ]

    def __str__(self):
        return f"{self.device_id} {self.from_location_id}->{self.to_location_id} @ {self.moved_at:%Y-%m-%d %H:%M}"

# ============================================================
# ✅ WorkflowStatus helper (shared)
# ============================================================
class WorkflowStatus(models.TextChoices):
    DRAFT = "DRAFT", "Ноорог"
    SUBMITTED = "SUBMITTED", "Хянагдахаар илгээсэн"
    APPROVED = "APPROVED", "Батлагдсан"
    REJECTED = "REJECTED", "Татгалзсан"


# ============================================================
# 5) Засвар, үйлчилгээ
# ============================================================
class MaintenanceService(models.Model):
    PERFORMER_TYPES = [
        ("ENGINEER", "Инженер"),
        ("ORG", "Байгууллага"),
    ]

    REASONS = [
        ("NORMAL", "Хэвийн засвар үйлчилгээ"),
        ("LIMITED", "Хязгаарлагдмал ажиллагаа"),
        ("NOT_WORKING", "Ажиллагаагүй болсон"),
    ]

    device = models.ForeignKey(
        "inventory.Device",
        on_delete=models.PROTECT,
        related_name="maintenance_services",
        verbose_name="Багаж / Төхөөрөмж",
    )
    date = models.DateField(verbose_name="Огноо")

    reason = models.CharField(
        max_length=20,
        choices=REASONS,
        default="NORMAL",
        verbose_name="Засвар хийсэн шалтгаан",
    )

    performer_type = models.CharField(
        max_length=10,
        choices=PERFORMER_TYPES,
        default="ENGINEER",
        verbose_name="Хийсэн этгээд (төрөл)",
    )
    performer_engineer_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Хийсэн инженер (нэр)",
    )
    performer_org_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Хийсэн байгууллага (нэр)",
    )

    # (Хуучин 1 файл) — олон файл нь MaintenanceEvidence model дээр хадгалагдана.
    evidence = models.FileField(
        upload_to="evidence/maintenance/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Нотлох баримт (файл)",
    )

    note = models.TextField(blank=True, default="", verbose_name="Тайлбар / тэмдэглэл")

    # --- Workflow ---
    workflow_status = models.CharField(
        max_length=12,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
        verbose_name="Workflow төлөв",
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Илгээсэн огноо")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ms_submitted",
        verbose_name="Илгээсэн хэрэглэгч",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Баталсан огноо")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ms_approved",
        verbose_name="Баталсан хэрэглэгч",
    )
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Татгалзсан огноо")
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ms_rejected",
        verbose_name="Татгалзсан хэрэглэгч",
    )
    reject_reason = models.TextField(blank=True, default="", verbose_name="Reject шалтгаан")

    # --- Hybrid verification flags ---
    self_verified = models.BooleanField(default=False, verbose_name="Аймаг өөрөө баталсан")
    central_verified = models.BooleanField(default=False, verbose_name="Төвөөр баталгаажсан")
    central_review_required = models.BooleanField(default=False, verbose_name="Төвийн баталгаа шаардлагатай")



    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Засвар, үйлчилгээ"
        verbose_name_plural = "Засвар, үйлчилгээ"
        ordering = ["-date", "-id"]
        permissions = [
            ("can_approve_workflow", "Can approve/reject workflow"),
        ]

    def __str__(self):
        return f"{self.device} - {self.get_reason_display()} ({self.date})"

    def clean(self):
        super().clean()
        eng = (self.performer_engineer_name or "").strip()
        org = (self.performer_org_name or "").strip()

        if self.performer_type == "ENGINEER":
            if not eng:
                raise ValidationError({"performer_engineer_name": "Инженерийн нэр заавал."})
            if org:
                raise ValidationError({"performer_org_name": "Инженер сонгосон үед байгууллага бөглөхгүй."})

        if self.performer_type == "ORG":
            if not org:
                raise ValidationError({"performer_org_name": "Байгууллагын нэр заавал."})
            if eng:
                raise ValidationError({"performer_engineer_name": "Байгууллага сонгосон үед инженер бөглөхгүй."})


# ============================================================
# 6) Хяналт, тохируулга
# ============================================================
class ControlAdjustment(models.Model):
    PERFORMER_TYPES = [
        ("ENGINEER", "Инженер"),
        ("ORG", "Байгууллага"),
    ]

    RESULTS = [
        ("PASS", "PASS - Хэвийн"),
        ("LIMITED", "Хязгаарлагдмал"),
        ("FAIL", "FAIL - Ажиллагаагүй"),
    ]

    device = models.ForeignKey(
        "inventory.Device",
        on_delete=models.PROTECT,
        related_name="control_adjustments",
        verbose_name="Багаж / Төхөөрөмж",
    )
    date = models.DateField(verbose_name="Огноо")

    result = models.CharField(max_length=20, choices=RESULTS, default="PASS", verbose_name="Үр дүн")

    performer_type = models.CharField(
        max_length=10,
        choices=PERFORMER_TYPES,
        default="ENGINEER",
        verbose_name="Хийсэн этгээд (төрөл)",
    )
    performer_engineer_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Хийсэн инженер (нэр)",
    )
    performer_org_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Хийсэн байгууллага (нэр)",
    )

    # (Хуучин 1 файл) — олон файл нь ControlEvidence model дээр хадгалагдана.
    evidence = models.FileField(
        upload_to="evidence/control/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Нотлох баримт (файл)",
    )

    note = models.TextField(blank=True, default="", verbose_name="Тайлбар / тэмдэглэл")

    # --- Workflow ---
    workflow_status = models.CharField(
        max_length=12,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
        verbose_name="Workflow төлөв",
    )
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Илгээсэн огноо")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ca_submitted",
        verbose_name="Илгээсэн хэрэглэгч",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Баталсан огноо")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ca_approved",
        verbose_name="Баталсан хэрэглэгч",
    )
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Татгалзсан огноо")
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ca_rejected",
        verbose_name="Татгалзсан хэрэглэгч",
    )
    reject_reason = models.TextField(blank=True, default="", verbose_name="Reject шалтгаан")

    # --- Hybrid verification flags ---
    self_verified = models.BooleanField(default=False, verbose_name="Аймаг өөрөө баталсан")
    central_verified = models.BooleanField(default=False, verbose_name="Төвөөр баталгаажсан")
    central_review_required = models.BooleanField(default=False, verbose_name="Төвийн баталгаа шаардлагатай")



    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Хяналт, тохируулга"
        verbose_name_plural = "Хяналт, тохируулга"
        ordering = ["-date", "-id"]
        permissions = [
            ("can_approve_workflow", "Can approve/reject workflow"),
        ]

    def __str__(self):
        return f"{self.device} - {self.get_result_display()} ({self.date})"

    def clean(self):
        super().clean()
        eng = (self.performer_engineer_name or "").strip()
        org = (self.performer_org_name or "").strip()

        if self.performer_type == "ENGINEER":
            if not eng:
                raise ValidationError({"performer_engineer_name": "Инженерийн нэр заавал."})
            if org:
                raise ValidationError({"performer_org_name": "Инженер сонгосон үед байгууллага бөглөхгүй."})

        if self.performer_type == "ORG":
            if not org:
                raise ValidationError({"performer_org_name": "Байгууллагын нэр заавал."})
            if eng:
                raise ValidationError({"performer_engineer_name": "Байгууллага сонгосон үед инженер бөглөхгүй."})


# ============================================================
# 6.1) Засварын олон нотлох баримт  ✅ ШИНЭ
# ============================================================
class MaintenanceEvidence(models.Model):
    service = models.ForeignKey(
        "inventory.MaintenanceService",
        on_delete=models.CASCADE,
        related_name="evidences",
        verbose_name="Засвар, үйлчилгээ",
    )
    file = models.FileField(
        upload_to="evidence/maintenance/%Y/%m/",
        verbose_name="Нотлох баримт (файл)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Засварын нотлох баримт"
        verbose_name_plural = "Засварын нотлох баримтууд"
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"{self.service_id} evidence #{self.id}"


# ============================================================
# 6.2) Хяналтын олон нотлох баримт  ✅ ШИНЭ
# ============================================================
class ControlEvidence(models.Model):
    control = models.ForeignKey(
        "inventory.ControlAdjustment",
        on_delete=models.CASCADE,
        related_name="evidences",
        verbose_name="Хяналт, тохируулга",
    )
    file = models.FileField(
        upload_to="evidence/control/%Y/%m/",
        verbose_name="Нотлох баримт (файл)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Хяналтын нотлох баримт"
        verbose_name_plural = "Хяналтын нотлох баримтууд"
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"{self.control_id} evidence #{self.id}"


# ============================================================
# 7) Сэлбэг захиалга
# ============================================================
class SparePartOrder(models.Model):
    order_no = models.CharField(max_length=20, unique=True, verbose_name="Захиалгын №")
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="Draft")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.order_no


class SparePartItem(models.Model):
    order = models.ForeignKey(SparePartOrder, related_name="items", on_delete=models.CASCADE)
    part_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)


# ============================================================
# 8) User Profile
# ============================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, default="AIMAG_ENG")
    org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)

    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


# ============================================================
# 9) Auth Audit Log
# ============================================================
class AuthAuditLog(models.Model):
    ACTION_CHOICES = [
        ("LOGIN_SUCCESS", "LOGIN_SUCCESS"),
        ("LOGIN_FAILED", "LOGIN_FAILED"),
        ("FORCED_PW_CHANGE", "FORCED_PW_CHANGE"),
        ("PASSWORD_CHANGED", "PASSWORD_CHANGED"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True, default="")
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action} {self.username}"


# ============================================================
# 10) Workflow + Data Audit (CRUD)
# ============================================================
class AuditEvent(models.Model):
    """CRUD + workflow action audit log.
    (Нэвтрэлтийн аудит нь AuthAuditLog дээр хадгалагдана.)
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "CREATE"
        UPDATE = "UPDATE", "UPDATE"
        DELETE = "DELETE", "DELETE"
        SUBMIT = "SUBMIT", "SUBMIT"
        APPROVE = "APPROVE", "APPROVE"
        REJECT = "REJECT", "REJECT"
        LIFECYCLE = "LIFECYCLE", "LIFECYCLE"
        NOTIFY = "NOTIFY", "NOTIFY"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        verbose_name="Хэрэглэгч",
    )
    action = models.CharField(max_length=20, choices=Action.choices, verbose_name="Үйлдэл")

    model_label = models.CharField(max_length=100, verbose_name="Model")  # e.g. inventory.ControlAdjustment
    object_id = models.CharField(max_length=50, blank=True, default="", verbose_name="Object ID")
    object_repr = models.CharField(max_length=255, blank=True, default="", verbose_name="Object")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    created_at = models.DateTimeField(default=timezone.now)
    changes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Audit event"
        verbose_name_plural = "Audit events"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action} {self.model_label}#{self.object_id}"


# ============================================================
# 11) Workflow Review Audit Log (Approve/Reject)
# ============================================================
class WorkflowAuditLog(models.Model):
    ACTION_CHOICES = [
        ("APPROVE", "APPROVE"),
        ("REJECT", "REJECT"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_audit_logs",
        verbose_name="Хэрэглэгч",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Үйлдэл")
    model_name = models.CharField(max_length=120, verbose_name="Model нэр")  # e.g. "MaintenanceService"
    record_id = models.PositiveIntegerField(verbose_name="Record ID")
    comment = models.TextField(blank=True, default="", verbose_name="Тайлбар")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Огноо")

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Workflow audit log"
        verbose_name_plural = "Workflow audit logs"
        indexes = [
            models.Index(fields=["model_name", "record_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action} {self.model_name}#{self.record_id}"

# ============================================================
# 12) Workflow materialized daily aggregation (optional, for heavy data)
# ============================================================
class WorkflowDailyAgg(models.Model):
    """Daily materialized aggregation for workflow analytics.

    ⚠️ Optional: use with management command materialize_workflow_agg.
    Create migration after adding this model.
    """

    day = models.DateField(db_index=True, verbose_name="Огноо (өдөр)")
    # Scope dimensions (nullable so it can store global totals)
    aimag = models.ForeignKey(Aimag, null=True, blank=True, on_delete=models.SET_NULL, related_name="workflow_daily_aggs")
    kind = models.CharField(max_length=20, blank=True, default="", verbose_name="Device kind")
    location_type = models.CharField(max_length=20, blank=True, default="", verbose_name="Location type")

    # Counts (MS/CA by status)
    ms_submitted = models.PositiveIntegerField(default=0)
    ms_approved = models.PositiveIntegerField(default=0)
    ms_rejected = models.PositiveIntegerField(default=0)

    ca_submitted = models.PositiveIntegerField(default=0)
    ca_approved = models.PositiveIntegerField(default=0)
    ca_rejected = models.PositiveIntegerField(default=0)

    # SLA (approved only) - average hours from submitted_at to approved_at
    sla_avg_hours = models.FloatField(default=0.0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Workflow daily aggregation"
        verbose_name_plural = "Workflow daily aggregations"
        indexes = [
            models.Index(fields=["day"]),
            models.Index(fields=["day", "aimag"]),
            models.Index(fields=["day", "kind"]),
            models.Index(fields=["day", "location_type"]),
        ]
        unique_together = ("day", "aimag", "kind", "location_type")

    def __str__(self):
        a = self.aimag.name if self.aimag else "ALL"
        k = self.kind or "ALL"
        lt = self.location_type or "ALL"
        return f"{self.day} {a} {k} {lt}"