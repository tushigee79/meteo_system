from django.db import models
from django.contrib.auth.models import User

# 1. Байгууллага (Organization)
class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Байгууллагын нэр")
    code = models.CharField(max_length=50, unique=True, verbose_name="Байгууллагын код")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллагууд"

    def __str__(self):
        return self.name

# 2. Аймаг / Нийслэл
class Aimag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Аймаг/Нийслэл")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Аймаг/Нийслэл"
        verbose_name_plural = "Аймаг/Нийслэл"

    def __str__(self):
        return self.name

# 3. Сум / Дүүрэг
class Soum(models.Model):
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name="soums", verbose_name="Аймаг")
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүрэг")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүрэг"

    def __str__(self):
        return f"{self.aimag.name} - {self.name}"

# 4. Байршил (Location)
class Location(models.Model):
    TYPE_CHOICES = [
        ("METEO", "Цаг уур"),
        ("HYDRO", "Ус судлал"),
        ("AWS", "Автомат"),
    ]
    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    wmo_index = models.CharField(max_length=20, blank=True, null=True, verbose_name="WMO индекс")
    location_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Төрөл")
    latitude = models.DecimalField(max_digits=12, decimal_places=9, verbose_name="Өргөрөг")
    longitude = models.DecimalField(max_digits=12, decimal_places=9, verbose_name="Уртраг")
    elevation = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Өндөр (м)")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    soum_ref = models.ForeignKey(Soum, on_delete=models.PROTECT, verbose_name="Сум")
    owner_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Эзэмшигч байгууллага")

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршил"

    def __str__(self):
        return self.name

# 5. Багаж (Device)
class Device(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Хэвийн'),
        ('REPAIRING', 'Засвартай'),
        ('BROKEN', 'Эвдэрсэн'),
        ('SPARE', 'Нөөцөд'),
    ]
    name = models.CharField(max_length=255, verbose_name="Багажны нэр")
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Төлөв")
    last_calibration_date = models.DateField(null=True, blank=True, verbose_name="Сүүлийн баталгаажуулалт")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices", verbose_name="Байршил")

    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багаж"

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

# 6. Засвар үйлчилгээ (Maintenance)
class Maintenance(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenances', verbose_name="Багаж")
    maintenance_type = models.CharField(max_length=20, verbose_name="Төрөл")
    date = models.DateField(verbose_name="Огноо")
    performed_by = models.CharField(max_length=100, verbose_name="Инженер")

    class Meta:
        verbose_name = "Засвар үйлчилгээ"
        verbose_name_plural = "Засвар үйлчилгээ"

# 7. Баталгаажуулалт (Calibration)
class Calibration(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calibrations', verbose_name="Багаж")
    calibration_date = models.DateField(verbose_name="Баталгаажуулсан огноо")
    expiry_date = models.DateField(verbose_name="Дуусах огноо")
    is_valid = models.BooleanField(default=True, verbose_name="Хүчинтэй")

    class Meta:
        verbose_name = "Баталгаажуулалт"
        verbose_name_plural = "Баталгаажуулалт"

# 8. Хэрэглэгчийн эрх (UserProfile)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг")
    role = models.CharField(max_length=20, default='ENGINEER', verbose_name="Эрх")

    class Meta:
        verbose_name = "Хэрэглэгчийн эрх"
        verbose_name_plural = "Хэрэглэгчийн эрх"