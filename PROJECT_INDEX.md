# BURTGEL PROJECT INDEX
Метео систем / БҮРТГЭЛ төслийн AI болон developer navigation index

---

## 1. Project identity

**Project name:** БҮРТГЭЛ  
**Type:** Meteorological / Hydrological / Instrument Inventory and Lifecycle Management System  
**Framework:** Django 4.2  
**Admin UI:** Django Admin + Jazzmin customization  
**Primary app:** `inventory`

---

## 2. Main purpose

Энэ систем нь дараах үндсэн зорилготой:

- Цаг уур, ус судлал, AWS, аэрологи, радар, эталон багажийг бүртгэх
- Байршил, байгууллага, харьяаллын дагуу хянах
- Калибровка, засвар, шилжилт хөдөлгөөн, lifecycle удирдах
- Dashboard, тайлан, статистик, экспорт гаргах
- QR кодтой device passport үүсгэх
- WMO / OSCAR / metadata-тэй нийцүүлэх

---

## 3. Core business modules

### 3.1 Location management
Станц, байршил, аймаг, сум/дүүрэг, байгууллагын байршлын бүртгэл

### 3.2 Device inventory
Багаж, тоног төхөөрөмж, системийн бүртгэл

### 3.3 Calibration / verification
Калибровка, баталгаажуулалт, хугацааны хяналт

### 3.4 Maintenance / repair
Засвар үйлчилгээ, эвдрэл, ашигласан сэлбэг

### 3.5 Device movement
Багажийн шилжилт хөдөлгөөний түүх

### 3.6 Reporting
CSV / Excel / PDF тайлан, статистик

### 3.7 Dashboard
Хүснэгт, график, газрын зураг, summary

### 3.8 QR / Device Passport
QR код, public lookup, printable passport PDF

### 3.9 Workflow / supervision
Хяналт, баталгаажуулалт, audit trail

---

## 4. Main code locations

### 4.1 Django config
- `manage.py`
- `meteo_config/settings.py`
- `meteo_config/urls.py`

### 4.2 Main app
- `inventory/models.py`
- `inventory/admin.py`
- `inventory/forms.py`
- `inventory/views.py`
- `inventory/urls.py`

### 4.3 Templates
- `templates/admin/dashboard_general.html`
- `templates/admin/dashboard_table.html`
- `templates/admin/dashboard_graph.html`
- `templates/admin/...` custom admin templates
- `templates/...` reports / QR / custom pages

### 4.4 Static / JS / CSS
- `inventory/static/`
- `static/`

### 4.5 Reports / QR / PDF related
- mostly in `inventory/admin.py`
- sometimes helper snippets in separate utility files if later refactored

---

## 5. Important models

Төслийн гол model-ууд:

- `Location`
- `Device`
- `InstrumentCatalog`
- `DeviceMovement`
- `MaintenanceService`
- `ControlAdjustment`

Мөн байж болох туслах model-ууд:
- `Aimag`
- `SumDuureg`
- `UserProfile`
- QR token / public access related models
- calibration / maintenance lookup models
- organization / lab / engineer related models

---

## 6. Location hierarchy

Ерөнхий логик:

```text
Country
 └─ Aimag
     └─ Sum / District
         └─ Location
             └─ Device