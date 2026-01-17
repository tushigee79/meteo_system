from django.db import models
from django.contrib.auth.models import User

# 1. Аймаг / Нийслэл
class Aimag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Аймаг/Нийслэл")
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "Аймаг/Нийслэл"

# 2. Сум / Дүүрэг
class Soum(models.Model):
    aimag = models.ForeignKey(Aimag, on_delete=models.CASCADE, related_name='soums', verbose_name="Аймаг")
    name = models.CharField(max_length=100, verbose_name="Сум/Дүүрэг")
    def __str__(self): return f"{self.aimag.name} - {self.name}"
    class Meta: verbose_name_plural = "Сум/Дүүрэг"

# 3. Байршил (Станц, харуул)
class Location(models.Model):
    TYPE_CHOICES = [('METEO', 'Цаг уур'), ('HYDRO', 'Ус судлал'), ('AWS', 'Автомат')]
    name = models.CharField(max_length=255, verbose_name="Станцын нэр")
    wmo_index = models.CharField(max_length=20, blank=True, null=True, verbose_name="WMO индекс")
    wigos_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="WIGOS ID")
    location_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Төрөл")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Өргөрөг")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Уртраг")
    elevation = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Өндөр (м)")
    aimag_ref = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    soum_ref = models.ForeignKey(Soum, on_delete=models.PROTECT, verbose_name="Сум")

    def __str__(self): return self.name

# 4. Багаж (Device)
class Device(models.Model):
    name = models.CharField(max_length=255, verbose_name="Багажны нэр")
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Серийн дугаар")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    def __str__(self): return f"{self.name} ({self.serial_number})"

# 5. Хэрэглэгчийн нэмэлт мэдээлэл
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Хариуцсан аймаг")
    is_engineer = models.BooleanField(default=True, verbose_name="Инженер эсэх")
    def __str__(self): return self.user.username

# 6. Дотоод зурвас
class InternalMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_msgs')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='received_msgs')
    message = models.TextField(verbose_name="Зурвас")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    class Meta: ordering = ['-created_at']