from django.db import models
from django.contrib.auth.models import User
from datetime import date

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

# 2. БОХЗТЛ: Эталон багажнууд
class StandardInstrument(models.Model):
    name = models.CharField(max_length=255, verbose_name="Эталон багажийн нэр")
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    accuracy_class = models.CharField(max_length=50, verbose_name="Нарийвчлалын ангилал", null=True, blank=True)
    last_calibration = models.DateField(verbose_name="Сүүлд шалгагдсан", null=True, blank=True)
    
    # ЗАСВАР: Жагсаалтад байхгүй бол гараар бичих модуль
    other_standard_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Бусад (Эталоны нэр бичих)")

    def __str__(self):
        if self.other_standard_name:
            return f"Бусад: {self.other_standard_name} ({self.serial_number})"
        return f"{self.name} ({self.serial_number})"

    @staticmethod
    def seed_reference_standards():
        standards = [
            "Стандарт платин термометр (SPRT)", "Усны гурвалсан цэгийн эталон эс",
            "Лабораторийн платин термометр (PRT)", "Температурын калибратор (Dry block)",
            "Шүүдэр цэгийн эталон гигрометр", "Стандарт психрометр (Assmann)",
            "Чийгийн калибратор камер", "Мөнгөн усны стандарт барометр",
            "Дижитал эталон барометр", "Даралтын калибратор",
            "Эталон анемометр", "Салхины суваг (Wind tunnel reference)",
            "Жинлүүрт стандарт тунадас хэмжигч", "Тунадасны калибровкийн төхөөрөмж",
            "Абсолют кавити радиометр", "Secondary standard пиранометр",
            "Эталон усны түвшний мэдрэгч", "Эталон урсац хэмжигч (Current meter)",
            "pH стандарт уусмал", "Цахилгаан дамжуулалтын стандарт уусмал",
            "Ууссан хүчилтөрөгчийн стандарт уусмал", "Турбидитийн стандарт уусмал",
            "Эталон хөрсний температурын мэдрэгч", "Эталон хөрсний чийгийн мэдрэгч",
            "PAR эталон мэдрэгч", "Радиозонд шалгах эталон камер",
            "Эталон дата логгер"
        ]
        for name in standards:
            StandardInstrument.objects.get_or_create(name=name)

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
    location_type = models.CharField(max_length=20, verbose_name="Төрөл")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Өргөрөг")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Уртраг")

    def __str__(self):
        # ЗАСВАР: image_d50a00.png дээрх "Тодорхойгүй"-г "Аймаг - Сум" болгож засав
        aimag_name = self.aimag_ref.name if self.aimag_ref else "Аймаг тодорхойгүй"
        sum_name = self.sum_ref.name if self.sum_ref else "Сум тодорхойгүй"
        return f"{aimag_name} - {sum_name}"

    class Meta:
        verbose_name = "Байршил"
        verbose_name_plural = "Байршлууд"

# 4. Багаж хэрэгсэл (Стандарт жагсаалт)
class DeviceCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name="Ангиллын нэр")
    def __str__(self): return self.name

class MasterDevice(models.Model):
    category = models.ForeignKey(DeviceCategory, on_delete=models.CASCADE, related_name='devices', verbose_name="Ангилал", null=True)
    name = models.CharField(max_length=255, verbose_name="Стандарт нэр")
    
    def __str__(self): 
        cat_prefix = f"{self.category.name}: " if self.category else ""
        return f"{cat_prefix}{self.name}"

    @staticmethod
    def seed_detailed_devices():
        # Жагсаалтаас "Бусад" сонголтыг хассан
        data = {
            "1) Цаг уурын үндсэн багаж (Meteorology)": [
                "Шингэн термометр (мөнгөн ус / спиртэн)", "Цахим термометр", "Max–Min термометр", "Хөрсний термометр",
                "Психрометр (Assmann, sling)", "Үсэт гигрометр", "Цахим гигрометр", "Температур-чийгийн мэдрэгч (T/RH sensor)",
                "Мөнгөн усны барометр", "Анероид барометр", "Барограф", "Цахим даралт мэдрэгч",
                "Анемометр (аяган, пропеллер, ультрасоник)", "Салхины чиг заагч (wind vane)", "Салхины мэдрэгч (AWS)",
                "Тунадас хэмжигч (manual rain gauge)", "Жинлүүрт тунадас хэмжигч", "Автомат тунадасны мэдрэгч", "Цас хэмжигч саваа",
                "Цасны гүн хэмжигч ультрасоник мэдрэгч", "Пиранометр", "Пиргелиометр", "Нет-радиометр", "Наран тусгалын хугацаа хэмжигч (Campbell-Stokes)",
                "Үүлний өндөр хэмжигч (ceilometer)", "Харагдац хэмжигч (visibility sensor)"
            ],
            "2) Уур амьсгалын багаж (Climatology)": [
                "Температур-чийгийн дата логгер", "Ууршилтын тогоо (Class A pan)", "Ууршилт хэмжигч автомат систем",
                "Хөрсний температурын мэдрэгч (олон гүн)", "Хөрсний чийгийн мэдрэгч", "Нарны цацрагийн урт хугацааны станцын иж бүрдэл", "Уур амьсгалын стандарт AWS"
            ],
            "3) Ус судлалын багаж (Hydrology)": [
                "Түвшин хэмжих рейк", "Даралтат усны түвшний мэдрэгч", "Ультрасоник усны түвшний мэдрэгч", "Radar түвшин хэмжигч",
                "Гидрометрийн сэнс (current meter)", "ADCP (Acoustic Doppler Current Profiler)", "Электромагнит урсац хэмжигч",
                "Усны температур мэдрэгч", "pH метр", "Цахилгаан дамжуулалт (EC) хэмжигч", "Ууссан хүчилтөрөгч (DO) хэмжигч", "Тунгалагшилт (turbidity) хэмжигч",
                "Цасны нягт хэмжигч", "Цасны усны эквивалент (SWE) хэмжигч"
            ],
            "4) Хөдөө аж ахуйн цаг уурын багаж (Agrometeorology)": [
                "Хөрсний температурын мэдрэгч (Агро)", "Хөрсний чийгийн мэдрэгч (TDR/FDR)", "Хөрсний дулаан урсгалын мэдрэгч",
                "Навчны чийгийн мэдрэгч", "Навчны температурын мэдрэгч", "Ургамлын өндөр хэмжигч",
                "Агро AWS станц", "Ууршилт-транспирацийн станц", "PAR мэдрэгч (photosynthetically active radiation)"
            ],
            "5) Радио, агаарын дээд давхаргын багаж": [
                "Радиозонд", "Аэрологийн хөөргөх систем", "GPS салхины тодорхойлогч", "Озон зонд"
            ],
            "6) Автомат систем ба дагалдах төхөөрөмж": [
                "AWS (Automatic Weather Station)", "Data logger", "GSM/Iridium дамжуулалтын модем", 
                "Нарны зай + цэнэг хураагуур", "Мачт, tripod, хамгаалалтын хайрцаг"
            ]
        }
        for cat_name, items in data.items():
            cat_obj, _ = DeviceCategory.objects.get_or_create(name=cat_name)
            for item in items:
                MasterDevice.objects.get_or_create(category=cat_obj, name=item)

    class Meta:
        verbose_name = "Стандарт багаж"
        verbose_name_plural = "Стандарт багажнууд"

# 5. Багаж (Device)
class Device(models.Model):
    TYPE_CHOICES = [('METEO', 'Цаг уур'), ('HYDRO', 'Ус судлал'), ('AWS', 'Автомат (AWS)')]
    STATUS_CHOICES = [
        ('Active', 'Ашиглагдаж буй'), ('Broken', 'Эвдрэлтэй'),
        ('Repair', 'Засварт байгаа'), ('Spare', 'Нөөцөд байгаа'),
        ('Retired', 'Ашиглалтаас гарсан')
    ]

    master_device = models.ForeignKey(MasterDevice, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Төрөл (Загвар)")
    # ЗАСВАР: image_d58183.png дээрх "Бусад" гараар бичих модуль
    other_device_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Бусад (Багажийн нэр бичих)")
    
    serial_number = models.CharField(max_length=100, verbose_name="Серийн дугаар")
    device_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='METEO', verbose_name="Ангилал")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="devices", verbose_name="Байршил", null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active', verbose_name="Төлөв")
    installation_date = models.DateField(null=True, blank=True, verbose_name="Суурилуулсан огноо")
    lifespan_years = models.PositiveIntegerField(default=10, verbose_name="Ашиглах хугацаа (жил)")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Баталгаажуулалт дуусах")
    
    def __str__(self):
        if self.other_device_name:
            return f"{self.serial_number} (Бусад: {self.other_device_name})"
        return f"{self.serial_number} ({self.master_device})"

# 6. Түүх, Гэмтэл, Захиалга
class CalibrationRecord(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calibrations', verbose_name="Багаж")
    # ЗАСВАР: image_d52ba8.png дээрх "Ашигласан эталон" модуль
    standard_used = models.ForeignKey(StandardInstrument, on_delete=models.SET_NULL, null=True, verbose_name="Ашигласан эталон")
    certificate_no = models.CharField(max_length=100, verbose_name="Гэрчилгээ №")
    issue_date = models.DateField(verbose_name="Олгосон огноо")
    expiry_date = models.DateField(verbose_name="Дуусах огноо")
    correction_value = models.FloatField(default=0.0, verbose_name="Засварын утга")
    file = models.FileField(upload_to='certificates/%Y/', null=True, blank=True, verbose_name="PDF файл")

class DeviceFault(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='faults', verbose_name="Багаж")
    reported_date = models.DateField(default=date.today, verbose_name="Мэдээлсэн огноо")
    fault_description = models.TextField(verbose_name="Эвдрэлийн тодорхойлолт")
    action_taken = models.TextField(null=True, blank=True, verbose_name="Авсан арга хэмжээ")
    is_fixed = models.BooleanField(default=False, verbose_name="Засагдсан эсэх")
    fixed_date = models.DateField(null=True, blank=True, verbose_name="Зассан огноо")

class DeviceAttachment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/', verbose_name="Файл")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class SparePartOrder(models.Model):
    STATUS_CHOICES = [('Draft', 'Ноорог'), ('Sent', 'Илгээсэн'), ('Approved', 'Зөвшөөрсөн'), ('Received', 'Хүлээж авсан')]
    aimag = models.ForeignKey(Aimag, on_delete=models.PROTECT, verbose_name="Аймаг")
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Инженер")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', verbose_name="Төлөв")
    created_at = models.DateTimeField(auto_now_add=True)

class UserProfile(models.Model):
    ROLE_CHOICES = [('NAMEM_HQ', 'ЦУОШГ Мэргэжилтэн'), ('LAB_RIC', 'БОХЗТЛ Инженер'), ('AIMAG_ENG', 'Аймгийн Инженер')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Хэрэглэгч")
    aimag = models.ForeignKey(Aimag, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аймаг")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='AIMAG_ENG', verbose_name="Үүрэг")