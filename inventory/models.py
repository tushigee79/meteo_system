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

# 2. Байршил (Зассан хувилбар)
class Location(models.Model):
    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.CASCADE, verbose_name="Аймаг")
    sum_ref = models.ForeignKey(SumDuureg, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сум/Дүүрэг")
    owner_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Байгууллага")
    location_type = models.CharField(max_length=20, verbose_name="Төрөл") # METEO, HYDRO, AWS
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")

    def __str__(self):
        # Untitled.png зураг дээрх шиг "Сум - Станцын нэр" хэлбэрээр харуулна
        sum_name = self.sum_ref.name if self.sum_ref else "Тодорхойгүй"
        return f"{sum_name} - {self.name}"

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршлууд"

# 3. Багаж (Device)
class MasterDevice(models.Model):
    name = models.CharField(max_length=255, verbose_name="Стандарт нэр")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Стандарт багаж"
        verbose_name_plural = "Стандарт багажнууд"

class Device(models.Model):
    TYPE_CHOICES = [('METEO', 'Цаг уур'), ('HYDRO', 'Ус судлал'), ('AWS', 'Автомат (AWS)')]
    master_device = models.ForeignKey(MasterDevice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Стандарт жагсаалт")
    other_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Бусад нэр")
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    device_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='METEO', verbose_name="Төрөл")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True, related_name="devices", verbose_name="Байршил")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Баталгаажуулалт дуусах")
    is_new = models.BooleanField(default=True, verbose_name="Шинэ багаж")

    def __str__(self):
        return self.master_device.name if self.master_device else (self.other_name or f"Багаж #{self.id}")
    class Meta:
        verbose_name = "Багаж"
        verbose_name_plural = "Багажнууд"

# 4. Захиалга ба Хавсралт
class SparePartOrder(models.Model):
    STATUS_CHOICES = [('Draft', 'Ноорог'), ('Sent', 'Илгээсэн'), ('Approved', 'Зөвшөөрсөн'), ('Received', 'Хүлээж авсан')]
    aimag = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Инженер")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Төлөв")
    created_at = models.DateTimeField(auto_now_add=True)

class SparePartOrderItem(models.Model):
    order = models.ForeignKey(SparePartOrder, related_name='items', on_delete=models.CASCADE)
    part_name = models.CharField(max_length=255, verbose_name="Сэлбэгийн нэр")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Тоо ширхэг")

class DeviceAttachment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/', verbose_name="Файл")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Хэрэглэгч")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг")
    role = models.CharField(max_length=20, default='Engineer', verbose_name="Эрх")
    def __str__(self): return f"{self.user.username} ({self.aimag})"