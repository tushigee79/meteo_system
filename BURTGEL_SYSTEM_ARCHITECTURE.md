# BURTGEL SYSTEM ARCHITECTURE

ЦУОШГ – Багаж, хэмжих хэрэгслийн бүртгэл, хяналтын систем  
Project name: БҮРТГЭЛ (BURTGEL)

Framework: Django  
Admin UI: Django Admin + Jazzmin  
Database: SQLite (dev) → PostgreSQL (production future)

---

# 1. System overview

БҮРТГЭЛ системийн үндсэн зорилго:

- Цаг уур
- Ус судлал
- Автомат станц
- Аэрологи
- Радар
- Эталон багаж

зэрэг хэмжих хэрэгслийг:

• бүртгэх  
• байршлаар хянах  
• lifecycle удирдах  
• засвар / калибровка хянах  
• тайлан гаргах  
• QR device passport үүсгэх

---

# 2. High level architecture

System layers:

User Interface
↓
Admin Interface (Jazzmin)
↓
Application Logic (Django)
↓
Models / ORM
↓
Database


---

# 3. Core modules

System дараах үндсэн модулиудаас бүрдэнэ.

### 3.1 Location management
Станц болон байршлын бүртгэл

### 3.2 Device inventory
Багаж, тоног төхөөрөмжийн бүртгэл

### 3.3 Instrument catalog
Багажийн төрөл, техникийн мэдээлэл

### 3.4 Calibration management
Калибровка, баталгаажуулалт

### 3.5 Maintenance
Засвар үйлчилгээ

### 3.6 Device movement
Багажийн шилжилт хөдөлгөөн

### 3.7 Reporting
Тайлан, статистик

### 3.8 Dashboard
Хяналтын самбар

### 3.9 QR passport
Багажийн QR код ба паспорт

---

# 4. Main data model

System-ийн үндсэн model-ууд:

Location  
Device  
InstrumentCatalog  
DeviceMovement  
MaintenanceService  
ControlAdjustment  

---

# 5. Location hierarchy

System дараах hierarchical бүтэцтэй.


Country
└── Aimag
└── Sum / District
└── Location
└── Device


---

# 6. Location types

Location төрөл:

WEATHER  
HYDRO  
AWS  
RADAR  
AEROLOGY  

---

# 7. Device lifecycle

Багажийн lifecycle дараах үе шаттай.


Registration
↓
Deployment
↓
Operation
↓
Calibration
↓
Failure
↓
Maintenance
↓
Movement
↓
Reuse / Restriction
↓
Decommission


---

# 8. Admin architecture

System нь custom admin site ашигладаг.


InventoryAdminSite


Admin interface нь:

• Dashboard  
• Reports  
• Device management  
• Location management  
• QR passport  
• Maintenance  
• Calibration  

зэрэг хэсгүүдтэй.

---

# 9. Dashboard architecture

Dashboard дараах хэсгүүдтэй.

### General dashboard
system summary

### Table dashboard
device list

### Graph dashboard
statistics charts

Routes:


/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/


---

# 10. Reporting system

System дараах төрлийн тайлан гаргана.

• байгууллагаар  
• аймгаар  
• багажийн төрлөөр  
• калибровка статус  
• засварын статистик  

Export:

CSV  
Excel  
PDF  

---

# 11. Device passport

Device бүрт:

• QR code  
• public lookup  
• printable PDF passport  

үүсгэнэ.

Passport дотор:

• device information  
• location  
• maintenance history  
• calibration history  

---

# 12. API endpoints

System-д AJAX endpoint ашиглагддаг.


ajax/load-sums/
ajax/location-options/
ajax/location-by-sum/
ajax/catalog-by-kind/


Reports API:


api/reports/charts/
api/reports/sums/


---

# 13. Dynamic form logic

Device form дээр dynamic logic ажиллана.

### Location cascade


Aimag → Sum → Location


### Device type cascade


Kind → InstrumentCatalog


---

# 14. Permissions architecture

System role-based access control ашиглана.

Roles:

Superuser  
Central admin  
Organization admin  
Aimag engineer  

---

# 15. Aimag engineer restriction

Аймгийн инженер:

• зөвхөн өөрийн аймгийн data харах  
• delete permission байхгүй  
• queryset filter ашиглана  

---

# 16. QR system

QR system дараах хэсгүүдтэй.

• QR token generation  
• public lookup page  
• QR revoke  
• device passport

---

# 17. File structure

Main project files:


inventory/models.py
inventory/admin.py
inventory/forms.py
inventory/views.py
inventory/urls.py


Templates:


templates/admin/dashboard_general.html
templates/admin/dashboard_table.html
templates/admin/dashboard_graph.html


---

# 18. Known complexity areas

System-д дараах хэсгүүд хамгийн төвөгтэй.

• admin.py architecture  
• dashboard javascript  
• aimag sum cascade  
• migrations  
• QR passport  

---

# 19. Recommended refactor

Admin logic дараах байдлаар салгах.


inventory/admin/
admin_site.py
admin_devices.py
admin_dashboard.py
admin_reports.py
admin_qr.py


---

# 20. Development toolkit

Project documentation files:

AI_MEMORY.md  
PROJECT_CONTEXT.md  
PROJECT_INDEX.md  
BUGS_AND_PATCHES.md  
DEV_WORKFLOW.md  
BURTGEL_SYSTEM_ARCHITECTURE.md  

---

# 21. Future roadmap

### Version 1.0
system stability

### Version 1.1
device lifecycle

### Version 1.2
reporting system

### Version 2.0
national meteorological platform

---

# END