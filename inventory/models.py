from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date

# 1. Засаг захиргаа ба Байгууллага
class Aimag(models.Model):
    name = models.CharField(max_length=100, verbose_name="Аймгийн нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Аймаг/Нийслэл"
        verbose_name_plural = "Аймаг/Нийслэл"

class SumDuureg(models.Model):
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүргийн нэр")
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name='sums', verbose_name="Аймаг")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүрэг"

class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Байгууллагын нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллагууд"

# 2. БОХЗТЛ: Эталон багаж
class StandardInstrument(models.Model):
    name = models.CharField(max_length=255, verbose_name="Эталон багажийн нэр")
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    accuracy_class = models.CharField(max_length=50, verbose_name="Нарийвчлалын ангилал", null=True, blank=True)
    last_calibration = models.DateField(verbose_name="Сүүлд шалгагдсан", null=True, blank=True)
    other_standard_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Бусад (Эталоны нэр бичих)")

    def __str__(self):
        if self.other_standard_name: return f"Бусад: {self.other_standard_name} ({self.serial_number})"
        return f"{self.name} ({self.serial_number})"

    class Meta:
        verbose_name = "Эталон багаж"
        verbose_name_plural = "Эталон багаж"

# 3. ЦУОШГ: Станцын байршил
class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    location_type = models.CharField(max_length=20, verbose_name="Төрөл")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум")
    wmo_index = models.CharField(max_length=10, null=True, blank=True, verbose_name="WMO индекс")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")
    owner_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Байгууллага")

    def __str__(self): return f"{self.name} ({self.aimag_ref.name})"

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршил"

# 4. Багаж хэрэгслийн ангилал
class DeviceCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Ангиллын нэр")
    def __str__(self): return self.name

class MasterDevice(models.Model):
    category = models.ForeignKey(DeviceCategory, on_delete=models.CASCADE, related_name='devices', verbose_name="Ангилал", null=True)
    name = models.CharField(max_length=255, verbose_name="Стандарт нэр")
    def __str__(self): 
        cat_prefix = f"{self.category.name}: " if self.category else ""
        return f"{cat_prefix}{self.name}"

# 5. Үндсэн Багаж (Device)
class Device(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Ашиглагдаж буй'), ('Broken', 'Эвдрэлтэй'),
        ('Repair', 'Засварт байгаа'), ('Spare', 'Нөөцөд байгаа'),
        ('Retired', 'Ашиглалтаас гарсан')
    ]
    master_device = models.ForeignKey(MasterDevice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Төрөл (Загвар)")
    other_device_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Бусад (Багажийн нэр бичих)")
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active', verbose_name="Төлөв")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="devices", verbose_name="Байршил", null=True, blank=True)
    installation_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан огноо")
    lifespan_years = models.PositiveIntegerField(default=10, verbose_name="Ашиглах хугацаа (жил)")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Баталгаажуулалт дуусах")

    @property
    def lifespan_expiry(self):
        if self.installation_date:
            try: return date(self.installation_date.year + self.lifespan_years, self.installation_date.month, self.installation_date.day)
            except ValueError: return date(self.installation_date.year + self.lifespan_years, self.installation_date.month, self.installation_date.day - 1)
        return None

    def __str__(self): return f"{self.serial_number} ({self.master_device or self.other_device_name})"

# 6. Сэлбэг захиалгын систем (Засварласан хувилбар)
class SparePartOrder(models.Model):
    STATUS_CHOICES = [('Draft', 'Ноорог'), ('Sent', 'Илгээсэн'), ('Approved', 'Зөвшөөрөгдсөн'), ('Rejected', 'Татгалзсан'), ('Received', 'Хүлээж авсан')]
    order_no = models.CharField(max_length=20, unique=True, verbose_name="Захиалгын №")
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    # Алдаанаас сэргийлж station-г null=True болгов
    station = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name="Станц", null=True)
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Захиалсан инженер")
    description = models.TextField(verbose_name="Техникийн үндэслэл")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Төлөв")
    # Алдаанаас сэргийлж created_at-г түр null=True болгов
    created_at = models.DateTimeField(null=True, blank=True, verbose_name="Үүсгэсэн огноо")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Сэлбэг захиалга"
        verbose_name_plural = "Сэлбэг захиалга"

    def __str__(self):
        return f"{self.order_no} - {self.aimag.name}"

class SparePartItem(models.Model):
    order = models.ForeignKey(SparePartOrder, related_name='items', on_delete=models.CASCADE)
    device_type = models.ForeignKey(MasterDevice, on_delete=models.SET_NULL, null=True, verbose_name="Багажны төрөл")
    part_name = models.CharField(max_length=255, verbose_name="Сэлбэг, хэрэгсэл")
    model_name = models.CharField(max_length=100, blank=True)
    serial_no = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)

# 7. Бусад туслах модулиуд
class CalibrationRecord(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, verbose_name="Багаж")
    standard_used = models.ForeignKey(StandardInstrument, on_delete=models.SET_NULL, null=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()

class DeviceFault(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, verbose_name="Багаж")
    fault_description = models.TextField()
    reported_date = models.DateField(default=date.today)

class UserProfile(models.Model):
    ROLE_CHOICES = [('NAMEM_HQ', 'ЦУОШГ Мэргэжилтэн'), ('LAB_RIC', 'БОХЗТЛ Инженер'), ('AIMAG_ENG', 'Аймгийн Инженер')]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='AIMAG_ENG')