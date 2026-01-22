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
    class Kind(models.TextChoices):
        ETALON = "ETALON", "Эталон"
        WEATHER = "WEATHER", "Цаг уур"
        HYDRO = "HYDRO", "Ус судлал"
        AGRI = "AGRI", "Хөдөө аж ахуй"

        RADAR = "RADAR", "Радарын станц"
        AEROLOGY = "AEROLOGY", "Аэрологийн станц"
        AWS = "AWS", "Цаг уурын автомат станц (AWS)"
        OTHER = "OTHER", "Бусад"

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.WEATHER,
        verbose_name="Төрөл",
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="ДЦУБ дотоод код",
        verbose_name="Код",
    )

    name_mn = models.CharField(max_length=255, verbose_name="Нэр (Монгол)")

    unit = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Хэмжих нэгж",
    )

    is_active = models.BooleanField(default=True, verbose_name="Идэвхтэй")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Эрэмбэ")

    class Meta:
        verbose_name = "ДЦУБ Каталог"
        verbose_name_plural = "ДЦУБ Каталог"
        ordering = ["sort_order", "kind", "name_mn"]
        unique_together = [("kind", "name_mn")]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.name_mn}"


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

    # ✅ УБ-ын 9 дүүргийг DB түвшинд ялгах флаг
    is_ub_district = models.BooleanField(default=False, verbose_name="УБ-ын 9 дүүрэг үү?")

    def __str__(self):
        # ✅ хүссэн форматаар
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
    LOCATION_TYPES = [("METEO", "METEO"), ("HYDRO", "HYDRO"), ("AWS", "AWS"), ("OTHER", "Бусад")]

    name = models.CharField(max_length=255, verbose_name="Нэр")
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default="METEO", verbose_name="Төрөл")
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
        ETALON = InstrumentCatalog.Kind.ETALON, "Эталон"
        WEATHER = InstrumentCatalog.Kind.WEATHER, "Цаг уур"
        HYDRO = InstrumentCatalog.Kind.HYDRO, "Ус судлал"
        AGRI = InstrumentCatalog.Kind.AGRI, "Хөдөө аж ахуй"

        RADAR = InstrumentCatalog.Kind.RADAR, "Радарын станц"
        AEROLOGY = InstrumentCatalog.Kind.AEROLOGY, "Аэрологийн станц"
        AWS = InstrumentCatalog.Kind.AWS, "Цаг уурын автомат станц (AWS)"
        OTHER = InstrumentCatalog.Kind.OTHER, "Бусад"

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
        # Каталог сонгосон бол төрөл нь таарах ёстой
        if self.catalog_item and self.catalog_item.kind != self.kind:
            raise ValidationError({"catalog_item": "Каталогийн төрөл таарахгүй байна."})
        # OTHER сонгосон бол нэр заавал
        if self.kind == self.Kind.OTHER and not (self.other_name or "").strip():
            raise ValidationError({"other_name": "“Бусад” сонгосон бол нэр заавал бөглөнө."})

    def __str__(self):
        name = self.catalog_item.name_mn if self.catalog_item else (self.other_name or "-")
        return f"{self.serial_number} - {name}"

    class Meta:
        # ✅ Optional нэршлийн засвар
        verbose_name = "Хэмжих хэрэгсэл"
        verbose_name_plural = "Хэмжих хэрэгсэл"


# ============================================================
# 6) Сэлбэг захиалга
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
# 7) User Profile
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
# 8) Auth Audit Log
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
