from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from smart_selects.db_fields import ChainedForeignKey


# =========================
# 2-3. Засаг захиргааны лавлах
# =========================
class Aimag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Аймаг / Нийслэл")

    class Meta:
        verbose_name = "Аймаг / Нийслэл"
        verbose_name_plural = "2-3. Засаг захиргааны лавлах"

    def __str__(self) -> str:
        return self.name


class Soum(models.Model):
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name="soums", verbose_name="Аймаг / Нийслэл")
    name = models.CharField(max_length=100, verbose_name="Сум / Дүүрэг")

    class Meta:
        unique_together = ("aimag", "name")
        verbose_name = "Сум / Дүүрэг"
        verbose_name_plural = "2-3. Засаг захиргааны лавлах"

    def __str__(self) -> str:
        return f"{self.name} ({self.aimag})"


# =========================
# 11. Байгууллага
# =========================
class Organization(models.Model):
    ORG_TYPE = [
        ("ORG_GENERAL", "Ердийн байгууллага (ж: ЦУОШГ)"),
        ("CAL_LAB", "Байгаль орчны хэмжил зүйн төв – калибровка/шалгалт тохируулгын лаборатори (БОХЗТ)"),
        ("OPERATOR", "Ашиглагч байгууллага"),
    ]

    name = models.CharField(max_length=255, unique=True, verbose_name="Байгууллагын нэр")
    org_type = models.CharField(max_length=20, choices=ORG_TYPE, verbose_name="Төрөл")

    accreditation_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="Итгэмжлэлийн №")
    accreditation_standard = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Стандарт (ж: ISO/IEC 17025)",
    )
    valid_until = models.DateField(blank=True, null=True, verbose_name="Хүчинтэй хугацаа хүртэл")

    contact = models.CharField(max_length=255, blank=True, null=True, verbose_name="Холбоо барих")
    note = models.TextField(blank=True, null=True, verbose_name="Тэмдэглэл")

    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "11. Байгууллага"

    def __str__(self) -> str:
        return self.name


# =========================
# 1. Байршил
# =========================
class Location(models.Model):
    LOCATION_TYPES = [
        ("METEO", "Цаг уурын станц"),
        ("HYDRO", "Ус судлалын харуул"),
        ("AWS", "Автомат цаг уурын станц (AWS)"),
        ("AGRO", "Агрометеорологийн цэг"),
        ("AVIATION", "Нисэхийн цаг уурын нэгж"),
        ("ADMIN", "Захиргаа/Алба"),
    ]

    STATUS_CHOICES = [
        ("OPERATIONAL", "Хэвийн ажиллаж байгаа"),
        ("CLOSED", "Хаагдсан"),
        ("PLANNED", "Төлөвлөгдсөн"),
        ("INACTIVE", "Түр зогссон"),
    ]

    name = models.CharField(max_length=255, verbose_name="Байршлын нэр")

    wmo_index = models.CharField(max_length=20, blank=True, null=True, verbose_name="WMO индекс")
    wigos_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="WIGOS ID")

    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default="METEO", verbose_name="Төрөл")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPERATIONAL", verbose_name="Төлөв")

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Уртраг")
    elevation = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Өндөр (м)")

    aimag_fk = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг / Нийслэл")
    soum_fk = ChainedForeignKey(
        Soum,
        chained_field="aimag_fk",
        chained_model_field="aimag",
        show_all=False,
        auto_choose=True,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Сум / Дүүрэг",
    )

    established_date = models.DateField(null=True, blank=True, verbose_name="Байгуулагдсан огноо")
    is_active = models.BooleanField(default=True, verbose_name="Идэвхтэй эсэх")
    description = models.TextField(blank=True, null=True, verbose_name="Тайлбар")

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "1. Байршлууд"

    def __str__(self) -> str:
        return self.name


# =========================
# 4. Багаж
# =========================
class Device(models.Model):
    DEVICE_STATUS = [
        ("IN_STOCK", "Агуулахад"),
        ("DEPLOYED", "Суурилсан"),
        ("MAINTENANCE", "Засвартай"),
        ("RETIRED", "Ашиглалтаас гарсан"),
    ]

    # ✅ ДЦУБ-ын ерөнхий багажны жагсаалт + Бусад
    DCUB_INSTRUMENTS = [
        ("THERMO", "Термометр (агаарын температур)"),
        ("HYGRO", "Гигрометр / Чийг хэмжигч"),
        ("THERMO_HYGRO", "Температур-чийгийн мэдрүүр (хос)"),
        ("BAROMETER", "Барометр (агаарын даралт)"),
        ("ANEMOMETER", "Анемометр (салхины хурд)"),
        ("WIND_VANE", "Салхины чиглэл хэмжигч (флюгер)"),
        ("RAIN_GAUGE", "Тунадас хэмжигч"),
        ("SNOW_GAUGE", "Цасны хэмжүүр / цасны шугам"),
        ("PYRANOMETER", "Пиранометр (нарны цацраг)"),
        ("VISIBILITY", "Алсын хараа хэмжигч"),
        ("PRESENT_WEATHER", "Одоогийн цаг агаарын мэдрүүр"),
        ("CEILOMETER", "Үүлний доод хязгаар хэмжигч"),
        ("DATA_LOGGER", "Даталоггер"),
        ("POWER", "Тэжээл/UPS"),
        ("OTHER", "Бусад (жагсаалтад байхгүй)"),
    ]

    name = models.CharField(max_length=255, verbose_name="Багажийн нэр")
    dcub_type = models.CharField(
        max_length=50,
        choices=DCUB_INSTRUMENTS,
        default="OTHER",
        verbose_name="ДЦУБ-ын ерөнхий багаж",
    )
    other_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Бусад бол нэр (заавал)")

    model = models.CharField(max_length=255, blank=True, null=True, verbose_name="Загвар")
    manufacturer = models.CharField(max_length=255, blank=True, null=True, verbose_name="Үйлдвэрлэгч")
    serial_number = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Serial №")

    status = models.CharField(max_length=30, choices=DEVICE_STATUS, default="IN_STOCK", verbose_name="Төлөв")

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, blank=True, null=True, related_name="devices", verbose_name="Одоогийн байршил")
    owner_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        verbose_name="Эзэмшигч байгууллага",
    )

    is_reference = models.BooleanField(default=False, verbose_name="Эталон багаж (БОХЗТ) эсэх")
    note = models.TextField(blank=True, null=True, verbose_name="Тэмдэглэл")

    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "4. Багаж"

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number or 'SN-гүй'})"

    def clean(self):
        if self.dcub_type == "OTHER" and not (self.other_name and self.other_name.strip()):
            raise ValidationError({"other_name": "“Бусад” сонгосон бол нэрийг заавал бичнэ."})

        if self.is_reference:
            if not self.owner_org:
                raise ValidationError({"owner_org": "Эталон багаж бол эзэмшигч байгууллага (CAL_LAB/БОХЗТ) заавал байна."})
            if self.owner_org.org_type != "CAL_LAB":
                raise ValidationError({"owner_org": "Эталон багажийн эзэмшигч байгууллага CAL_LAB (БОХЗТ) байх ёстой."})

    def latest_calibration(self):
        return self.calibration_logs.order_by("-calibration_date").first()


# =========================
# 6. Засвар үйлчилгээ (Инженер/Байгууллага + гар бичилт)
# =========================
class MaintenanceLog(models.Model):
    RESULT_CHOICES = [
        ("NORMAL", "Хэвийн"),
        ("LIMITED", "Хязгаарлагдмал"),
        ("NOT_OBSERVED", "Ажиглаагүй"),
        ("FAILED", "Хэвийн бус"),
    ]

    PERFORMER_TYPE = [
        ("ENGINEER", "Инженер"),
        ("ORG", "Байгууллага"),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="maintenance_logs", verbose_name="Багаж")
    date = models.DateField(default=timezone.now, verbose_name="Огноо")

    summary = models.CharField(max_length=255, verbose_name="Ямар засвар хийсэн (товч)")
    details = models.TextField(blank=True, null=True, verbose_name="Дэлгэрэнгүй")

    performed_by_type = models.CharField(max_length=20, choices=PERFORMER_TYPE, default="ENGINEER", verbose_name="Засвар гүйцэтгэсэн этгээд")
    engineer_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Инженерийн нэр (гараар)")
    organization_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Байгууллагын нэр (гараар)")

    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default="NORMAL", verbose_name="Үр дүн")

    class Meta:
        verbose_name = "Засвар"
        verbose_name_plural = "6. Засвар үйлчилгээ"
        ordering = ("-date",)

    def __str__(self) -> str:
        return f"{self.device} / {self.date} / {self.summary}"

    def clean(self):
        if self.performed_by_type == "ENGINEER":
            if not (self.engineer_name and self.engineer_name.strip()):
                raise ValidationError({"engineer_name": "Инженер сонгосон бол инженерийн нэрийг заавал оруулна."})
            if self.organization_name:
                raise ValidationError({"organization_name": "Инженер сонгосон үед байгууллагын нэр бөглөхгүй."})
        else:
            if not (self.organization_name and self.organization_name.strip()):
                raise ValidationError({"organization_name": "Байгууллага сонгосон бол байгууллагын нэрийг заавал оруулна."})
            if self.engineer_name:
                raise ValidationError({"engineer_name": "Байгууллага сонгосон үед инженерийн нэр бөглөхгүй."})


# =========================
# 7. Калибровка (БОХЗТ / Бусад + гар бичилт)
# =========================
class CalibrationLog(models.Model):
    LAB_CHOICE = [
        ("BOHZT", "БОХЗТ"),
        ("OTHER", "Бусад"),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="calibration_logs", verbose_name="Багаж")

    lab_choice = models.CharField(max_length=20, choices=LAB_CHOICE, default="BOHZT", verbose_name="Калибровка хийсэн лаборатори")
    lab_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calibration_logs",
        limit_choices_to={"org_type": "CAL_LAB"},
        verbose_name="БОХЗТ (сонголт)",
    )
    lab_other_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Бусад лабораторийн нэр (гараар)")

    calibration_date = models.DateField(default=timezone.now, verbose_name="Калибровка хийсэн огноо")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Дуусах огноо")
    certificate_no = models.CharField(max_length=255, blank=True, null=True, verbose_name="Гэрчилгээ №")
    note = models.TextField(blank=True, null=True, verbose_name="Тэмдэглэл")

    class Meta:
        verbose_name = "Калибровка"
        verbose_name_plural = "7. Калибровка"
        ordering = ("-calibration_date",)

    def __str__(self) -> str:
        return f"{self.device} / {self.calibration_date}"

    def clean(self):
        if self.lab_choice == "BOHZT":
            if not self.lab_org:
                raise ValidationError({"lab_org": "БОХЗТ сонгосон бол лабораторийг (CAL_LAB) заавал сонгоно."})
            if self.lab_other_name:
                raise ValidationError({"lab_other_name": "БОХЗТ сонгосон үед “Бусад лабораторийн нэр” бөглөхгүй."})
        else:
            if not (self.lab_other_name and self.lab_other_name.strip()):
                raise ValidationError({"lab_other_name": "Бусад сонгосон бол лабораторийн нэрийг заавал гараар оруулна."})
            if self.lab_org:
                raise ValidationError({"lab_org": "Бусад сонгосон үед БОХЗТ сонгохгүй."})


# =========================
# 8. Сэлбэгийн лавлах
# =========================
class SparePart(models.Model):
    name = models.CharField(max_length=255, verbose_name="Сэлбэгийн нэр")
    part_no = models.CharField(max_length=255, blank=True, null=True, verbose_name="Part №")
    unit = models.CharField(max_length=50, default="ш", verbose_name="Нэгж")

    class Meta:
        verbose_name = "Сэлбэг"
        verbose_name_plural = "8. Сэлбэгийн лавлах"

    def __str__(self) -> str:
        return self.name


# =========================
# 9. Багаж сэлбэгийн захиалга
# =========================
class SparePartOrder(models.Model):
    STATUS = [
        ("DRAFT", "Ноорог"),
        ("SUBMITTED", "Илгээсэн"),
        ("APPROVED", "Зөвшөөрсөн"),
        ("ORDERED", "Захиалсан"),
        ("RECEIVED", "Хүлээн авсан"),
        ("CANCELLED", "Цуцалсан"),
    ]

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Үүссэн огноо")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Үүсгэсэн хэрэглэгч")

    aimag_fk = models.ForeignKey(Aimag, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Аймаг/Нийслэл")

    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT", verbose_name="Төлөв")
    note = models.TextField(blank=True, null=True, verbose_name="Тэмдэглэл")

    class Meta:
        verbose_name = "Сэлбэг захиалга"
        verbose_name_plural = "9. Багаж сэлбэгийн захиалга"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Захиалга #{self.id} ({self.get_status_display()})"


class SparePartOrderItem(models.Model):
    order = models.ForeignKey(SparePartOrder, on_delete=models.CASCADE, related_name="items", verbose_name="Захиалга")
    spare_part = models.ForeignKey(SparePart, on_delete=models.PROTECT, verbose_name="Сэлбэг")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Тоо хэмжээ")
    comment = models.CharField(max_length=255, blank=True, null=True, verbose_name="Тайлбар")

    class Meta:
        verbose_name = "Захиалгын мөр"
        verbose_name_plural = "Захиалгын мөрүүд"

    def __str__(self) -> str:
        return f"{self.spare_part} × {self.quantity}"


# =========================
# 10. Нотлох баримт (Generic attachment)
# =========================
class EvidenceFile(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Оруулсан огноо")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Оруулсан хэрэглэгч")
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Тайлбар")
    file = models.FileField(upload_to="evidence/%Y/%m/", verbose_name="Файл")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Нотлох баримт"
        verbose_name_plural = "10. Нотлох баримт"

    def __str__(self) -> str:
        return self.title or f"Evidence #{self.id}"


# =========================
# 12. Тайлан & статистик snapshot
# =========================
class OrganizationReport(models.Model):
    """Admin dashboard-д байгууллагаар нэгтгэсэн статистикийг хадгалж, CSV export хийхэд ашиглана."""

    created_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)

    # snapshot json
    payload = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Тайлан (snapshot)"
        verbose_name_plural = "11. Тайлан & статистик (snapshot)"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        p = "all-time"
        if self.period_start and self.period_end:
            p = f"{self.period_start}..{self.period_end}"
        return f"Report {self.created_at.date()} ({p})"

    @staticmethod
    def build(period_start: date | None = None, period_end: date | None = None) -> dict:
        """Return dict rows: org_name -> metrics."""
        orgs = Organization.objects.all().order_by("name")

        rows = []
        for org in orgs:
            device_qs = Device.objects.filter(owner_org=org)

            cal_qs = CalibrationLog.objects.all()
            mnt_qs = MaintenanceLog.objects.all()

            # if period filter given
            if period_start:
                cal_qs = cal_qs.filter(calibration_date__gte=period_start)
                mnt_qs = mnt_qs.filter(date__gte=period_start)
            if period_end:
                cal_qs = cal_qs.filter(calibration_date__lte=period_end)
                mnt_qs = mnt_qs.filter(date__lte=period_end)

            # Calibration done by org: BOHZT via lab_org, Other via lab_other_name (we count org only)
            cal_by_org = cal_qs.filter(lab_org=org).count()

            # Maintenance done by org name (free text). We count where performed_by_type=ORG and organization_name matches.
            mnt_by_org = mnt_qs.filter(performed_by_type="ORG", organization_name__iexact=org.name).count()

            # QA split by latest calibration expiry
            ok_cnt = warn90_cnt = warn30_cnt = expired_cnt = unknown_cnt = 0
            for d in device_qs.only("id"):
                latest = CalibrationLog.objects.filter(device=d).order_by("-calibration_date").first()
                if not latest or not latest.expiry_date:
                    unknown_cnt += 1
                    continue
                days = (latest.expiry_date - date.today()).days
                if days < 0:
                    expired_cnt += 1
                elif days <= 30:
                    warn30_cnt += 1
                elif days <= 90:
                    warn90_cnt += 1
                else:
                    ok_cnt += 1

            rows.append(
                {
                    "organization": org.name,
                    "org_type": org.org_type,
                    "devices": device_qs.count(),
                    "reference_devices": device_qs.filter(is_reference=True).count(),
                    "calibrations_done": cal_by_org,
                    "maintenance_done": mnt_by_org,
                    "qa_ok": ok_cnt,
                    "qa_90d": warn90_cnt,
                    "qa_30d": warn30_cnt,
                    "qa_expired": expired_cnt,
                    "qa_unknown": unknown_cnt,
                }
            )

        return {
            "period_start": str(period_start) if period_start else None,
            "period_end": str(period_end) if period_end else None,
            "rows": rows,
        }
