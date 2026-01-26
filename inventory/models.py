# inventory/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

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

    STATUS_CHOICES = [
        ("Active", "Ашиглагдаж буй"),
        ("Broken", "Эвдрэлтэй"),
        ("Repair", "Засварт"),
        ("Spare", "Нөөц"),
        ("Retired", "Хасагдсан"),
    ]

    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.WEATHER,
        verbose_name="Төрөл",
    )

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

    def clean(self):
        if self.catalog_item and self.catalog_item.kind != self.kind:
            raise ValidationError({"catalog_item": "Каталогийн төрөл таарахгүй байна."})

        if self.kind == self.Kind.OTHER and not (self.other_name or "").strip():
            raise ValidationError({"other_name": "“Бусад” сонгосон бол нэр заавал бөглөнө."})

    def __str__(self):
        name = self.catalog_item.name_mn if self.catalog_item else (self.other_name or "-")
        return f"{self.serial_number} - {name}"

    class Meta:
        verbose_name = "Хэмжих хэрэгсэл"
        verbose_name_plural = "Хэмжих хэрэгсэл"


# ============================================================
# ✅ WorkflowStatus helper (shared)
# ============================================================
class WorkflowStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


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
