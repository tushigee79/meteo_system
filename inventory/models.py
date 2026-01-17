from django.db import models
from django.contrib.auth.models import User

# 1. Засаг захиргаа ба Байгууллага
class Aimag(models.Model):
    name = models.CharField(max_length=100, verbose_name="Аймгийн нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Аймаг/Нийслэл"
        verbose_name_plural = "Аймаг/Нийслэлүүд"

class SumDuureg(models.Model):
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүргийн нэр")
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name='sums', verbose_name="Аймаг")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Сум/Дүүрэг"
        verbose_name_plural = "Сум/Дүүргүүд"

class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Байгууллагын нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Байгууллага"
        verbose_name_plural = "Байгууллагууд"

# 2. БОХЗТЛ: Эталон багажнууд (RIC Standards)
class StandardInstrument(models.Model):
    name = models.CharField(max_length=255, verbose_name="Эталон багажийн нэр")
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    accuracy_class = models.CharField(max_length=50, verbose_name="Нарийвчлалын ангилал")
    last_calibration = models.DateField(verbose_name="Сүүлд шалгагдсан")
    def __str__(self): return f"{self.name} ({self.serial_number})"
    class Meta:
        verbose_name = "Эталон багаж"
        verbose_name_plural = "Эталон багажууд"

# 3. ЦУОШГ: Станцын нэгдсэн байршил
class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    wmo_index = models.CharField(max_length=10, null=True, blank=True, verbose_name="WMO индекс")
    icao_code = models.CharField(max_length=4, null=True, blank=True, verbose_name="ICAO код")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум/Дүүрэг")
    owner_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Байгууллага")
    location_type = models.CharField(max_length=20, verbose_name="Төрөл") # METEO, HYDRO, AWS
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")

    def __str__(self):
        # Станцын нэрийг Сумтай нь нэгтгэж харуулна
        sum_name = self.sum_ref.name if self.sum_ref else "Тодорхойгүй"
        return f"{sum_name} - {self.name}"
    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршлууд"

# 4. Багаж ба Баталгаажуулалт
class MasterDevice(models.Model):
    name = models.CharField(max_length=255, verbose_name="Стандарт нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Стандарт багаж"
        verbose_name_plural = "Стандарт багажнууд"

class Device(models.Model):
    TYPE_CHOICES = [('METEO', 'Цаг уур'), ('HYDRO', 'Ус судлал'), ('AWS', 'Автомат (AWS)')]
    master_device = models.ForeignKey(MasterDevice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Төрөл (Загвар)")
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    device_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='METEO', verbose_name="Ангилал")
    # ЗАСВАР: null=True, blank=True нэмснээр өгөгдөлгүй үеийн алдаанаас сэргийлнэ
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="devices", verbose_name="Байршил", null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True, verbose_name="Баталгаажуулалт дуусах")
    
    def __str__(self): return f"{self.serial_number} ({self.master_device})"
    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багажнууд"

class CalibrationRecord(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calibrations', verbose_name="Багаж")
    standard_used = models.ForeignKey(StandardInstrument, on_delete=models.SET_NULL, null=True, verbose_name="Ашигласан эталон")
    certificate_no = models.CharField(max_length=100, verbose_name="Гэрчилгээ №")
    issue_date = models.DateField(verbose_name="Олгосон огноо")
    expiry_date = models.DateField(verbose_name="Дуусах огноо")
    correction_value = models.FloatField(default=0.0, verbose_name="Засварын утга")
    file = models.FileField(upload_to='certificates/%Y/', null=True, blank=True, verbose_name="PDF файл")
    
    class Meta:
        verbose_name = "Баталгаажуулалтын бүртгэл"
        verbose_name_plural = "Баталгаажуулалтын бүртгэлүүд"

class DeviceAttachment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/', verbose_name="Файл")
    uploaded_at = models.DateTimeField(auto_now_add=True)

# 5. Захиалга ба Хэрэглэгчийн эрх
class SparePartOrder(models.Model):
    STATUS_CHOICES = [('Draft', 'Ноорог'), ('Sent', 'Илгээсэн'), ('Approved', 'Зөвшөөрсөн'), ('Received', 'Хүлээж авсан')]
    aimag = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Инженер")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Төлөв")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Сэлбэгийн захиалга"
        verbose_name_plural = "Сэлбэгийн захиалгууд"

class UserProfile(models.Model):
    ROLE_CHOICES = [('NAMEM_HQ', 'ЦУОШГ Мэргэжилтэн'), ('LAB_RIC', 'БОХЗТЛ Инженер'), ('AIMAG_ENG', 'Аймгийн Инженер')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Хэрэглэгч")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='AIMAG_ENG', verbose_name="Үүрэг")
    def __str__(self): return f"{self.user.username} ({self.role})"