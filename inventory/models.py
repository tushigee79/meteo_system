from django.db import models
from django.contrib.auth.models import User

# 1. Аймаг / Нийслэл
class Aimag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Аймаг/Нийслэл")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Аймаг/Нийслэл"
        verbose_name_plural = "Аймаг/Нийслэл"


# 2. Сум / Дүүрэг
class Soum(models.Model):
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name="soums", verbose_name="Аймаг")
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүрэг")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.aimag.name} - {self.name}"

    class Meta:
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүрэг"


# 3. Байршил (Станц, харуул)
class Location(models.Model):
    TYPE_CHOICES = [
        ("METEO", "Цаг уур"),
        ("HYDRO", "Ус судлал"),
        ("AWS", "Автомат"),
    ]

    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    wmo_index = models.CharField(max_length=20, blank=True, null=True, verbose_name="WMO индекс")
    wigos_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="WIGOS ID")
    location_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Төрөл")
    latitude = models.DecimalField(max_digits=12, decimal_places=9, verbose_name="Өргөрөг")
    longitude = models.DecimalField(max_digits=12, decimal_places=9, verbose_name="Уртраг")
    elevation = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Өндөр (м)")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    soum_ref = models.ForeignKey(Soum, on_delete=models.PROTECT, verbose_name="Сум")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршил"


# 4. Багаж (Device)
class Device(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Хэвийн ажиллаж буй'),
        ('REPAIRING', 'Засвартай'),
        ('BROKEN', 'Эвдэрсэн'),
        ('SPARE', 'Нөөцөд байгаа'),
    ]

    name = models.CharField(max_length=255, verbose_name="Багажны нэр")
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Төлөв")
    last_calibration_date = models.DateField(null=True, blank=True, verbose_name="Сүүлийн баталгаажуулалт")
    
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        verbose_name="Байршил",
    )

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багаж"



# 5. Засвар үйлчилгээ (Maintenance) - ШИНЭЭР НЭМЭВ
class Maintenance(models.Model):
    MAINTENANCE_TYPES = [
        ('REPAIR', 'Засвар'),
        ('INSPECTION', 'Үзлэг'),
        ('CLEANING', 'Цэвэрлэгээ'),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenances', verbose_name="Багаж")
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES, verbose_name="Төрөл")
    date = models.DateField(verbose_name="Огноо")
    performed_by = models.CharField(max_length=100, verbose_name="Гүйцэтгэсэн инженер")
    description = models.TextField(blank=True, verbose_name="Тайлбар")

    class Meta:
        verbose_name = "Засвар үйлчилгээ"
        verbose_name_plural = "Засвар үйлчилгээ"


# 6. Баталгаажуулалт (Calibration) - ШИНЭЭР НЭМЭВ
class Calibration(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calibrations', verbose_name="Багаж")
    calibration_date = models.DateField(verbose_name="Баталгаажуулсан огноо")
    expiry_date = models.DateField(verbose_name="Дуусах огноо")
    certificate_number = models.CharField(max_length=50, verbose_name="Гэрчилгээний дугаар")
    is_valid = models.BooleanField(default=True, verbose_name="Хүчинтэй эсэх")

    class Meta:
        verbose_name = "Баталгаажуулалт"
        verbose_name_plural = "Баталгаажуулалт"


# 7. Хэрэглэгчийн нэмэлт мэдээлэл (UserProfile)
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Админ'),
        ('ENGINEER', 'Аймгийн инженер'),
        ('VIEWER', 'Үзэгч'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Хариуцсан аймаг")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ENGINEER', verbose_name="Эрх")

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = "Хэрэглэгчийн эрх"
        verbose_name_plural = "Хэрэглэгчийн эрх"


# 8. Дотоод зурвас
class InternalMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_msgs", verbose_name="Илгээгч")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="received_msgs")
    message = models.TextField(verbose_name="Зурвас")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Дотоод зурвас"
        verbose_name_plural = "Дотоод зурвас"