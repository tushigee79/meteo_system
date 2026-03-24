# BURTGEL QUICKSTART FOR AI

Project: БҮРТГЭЛ (BURTGEL)  
Repository: meteo_system  
Framework: Django  
Primary app: inventory

---

# 1. Purpose

Энэ файл нь шинэ AI чат эхлэх үед системийн контекстийг маш хурдан ачаалах зориулалттай.

AI энэ төслийг ойлгохын тулд эхлээд дараах баримтуудыг унших ёстой.

---

# 2. Read order for AI

AI дараах дарааллаар documentation файлуудыг уншина.

1 AI_MEMORY.md  
2 PROJECT_CONTEXT.md  
3 PROJECT_INDEX.md  
4 BUGS_AND_PATCHES.md  
5 BURTGEL_MASTER_ARCHITECTURE_MAP.md  
6 BURTGEL_IMPLEMENTATION_ROADMAP.md  

Энэ дараалал нь:

memory → context → navigation → issues → architecture → execution plan

логик урсгал үүсгэнэ.

---

# 3. System overview

BURTGEL нь ЦУОШГ-ын дараах asset/system-уудыг удирдах платформ юм:

- цаг уурын станц
- ус судлалын станц
- AWS
- аэрологи
- радар
- эталон багаж

Системийн үндсэн боломжууд:

- багаж бүртгэл
- байршлын удирдлага
- lifecycle tracking
- калибровка бүртгэл
- засвар үйлчилгээ
- шилжилт хөдөлгөөн
- QR device passport
- тайлан ба статистик
- role-based access
- audit trail

---

# 4. Main models

Core entities

Location  
Device  
InstrumentCatalog  
UserProfile  

Lifecycle entities

DeviceMovement  
MaintenanceService  
CalibrationRecord  
ControlAdjustment  
FailureIncident  

Support entities

Organization  
QRToken  
ManualLibraryItem  
SparePartOrder  
SparePartOrderItem  

---

# 5. Geographic hierarchy

```text
Aimag
 └── SumDuureg
       └── Location
             └── Device

Location нь дараах metadata агуулна:

координат

elevation

location type

station code

organization

siting classification

wigos_id

6. Device lifecycle concept

Device = current state
Lifecycle tables = historical records

Lifecycle events:

registration

deployment

calibration

failure

maintenance

adjustment

movement

decommission

7. Admin architecture

Admin interface нь custom admin site ашиглана.

InventoryAdminSite

Admin modules

devices

locations

catalog

dashboard

reports

qr passport

workflow

Admin routes

/admin/
/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/
8. Dashboard

Dashboard 3 төрөлтэй.

General dashboard
Table dashboard
Graph dashboard

Dashboard нь дараах мэдээллийг харуулна:

device statistics

organization distribution

aimag distribution

verification status

maintenance statistics

9. Dynamic form logic

Device form дээр:

Aimag → SumDuureg → Location cascade

Kind → InstrumentCatalog cascade

AJAX endpoints

ajax/load-sums/
ajax/location-options/
ajax/catalog-by-kind/
10. Permissions

Roles

Superuser
Central admin
Organization admin
Aimag engineer

Aimag engineer:

зөвхөн өөрийн аймаг

delete permission байхгүй

11. QR passport system

Device бүр:

QR token

public lookup

printable PDF passport

Passport-д:

device information

location

maintenance history

calibration history

12. Known issues

Historical issues (see BUGS_AND_PATCHES.md):

admin route conflict

dashboard JS crash

UTF-8 encoding patch issues

aimag → sum cascade bug

migration dependency issues

admin.py complexity

13. Key files for debugging

Route issues

meteo_config/urls.py
inventory/admin.py
inventory/urls.py

Dashboard issues

templates/admin/dashboard_general.html
templates/admin/dashboard_table.html
templates/admin/dashboard_graph.html

Device form issues

inventory/forms.py
inventory/views.py
inventory/admin.py

Model / migration issues

inventory/models.py
inventory/migrations/

14. Development workflow

See

DEV_WORKFLOW.md

Key commands

python manage.py check
python manage.py showmigrations
python manage.py migrate
python manage.py runserver
15. Current development priority

Current focus:

1 System stability
2 Admin architecture refactor
3 Device lifecycle modules
4 Dashboard analytics
5 QR passport system

16. One sentence system description

BURTGEL нь ЦУОШГ-ын багаж, станц, байршил, lifecycle, засвар, калибровка, QR паспорт, тайлан, workflow болон audit-ийг Django Admin дээр төвлөрүүлэн удирдах asset lifecycle management platform юм.

END