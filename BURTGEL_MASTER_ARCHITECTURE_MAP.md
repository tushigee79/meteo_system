# BURTGEL MASTER ARCHITECTURE MAP

Project: БҮРТГЭЛ (BURTGEL)  
System: Meteorological Instrument, Station, Lifecycle and Reporting Platform  
Framework: Django  
Primary app: inventory

Энэ файл нь БҮРТГЭЛ системийн бүх архитектурын түвшнийг нэг дор нэгтгэсэн master map болно.

---

# 1. Purpose

Энэ баримтын зорилго:

- системийг 1 файлаас ерөнхийд нь ойлгох
- architecture layers-ийг нэг зураглалд харах
- model, admin, dashboard, QR, reporting, workflow хоорондын холбоог тайлбарлах
- developer, AI, administrator бүгдэд navigation map болох

---

# 2. System identity

БҮРТГЭЛ систем нь дараах төрлийн asset/system-уудыг удирдах үндсэн платформ юм:

- Цаг уурын станц
- Ус судлалын станц
- AWS
- Аэрологийн станц
- Радар
- Эталон багаж
- Засвар, калибровка, баталгаажуулалтын бүртгэл
- Байршил, харьяалал, lifecycle, passport, reporting

---

# 3. Master architecture overview

```text
USERS
│
├── Superuser
├── Central Admin
├── Organization Admin
└── Aimag Engineer
        │
        ▼
ADMIN INTERFACE (Jazzmin + Custom AdminSite)
│
├── Dashboard
├── Device Management
├── Location Management
├── Catalog Management
├── Lifecycle Modules
├── Reports
├── QR / Passport
└── Workflow / Audit
        │
        ▼
APPLICATION LAYER (Django)
│
├── Models
├── Admin Modules
├── Forms
├── Views / AJAX APIs
├── Reports / Exports
└── QR / PDF generators
        │
        ▼
DATABASE LAYER
│
├── Reference Data
├── Core Master Entities
├── Lifecycle History Entities
├── Access / Audit Entities
└── Knowledge / Document Entities

4. Layer-by-layer map
4.1 User layer

Системийн үндсэн хэрэглэгчид:

Superuser

Central admin

Organization admin

Aimag engineer

Хэрэглэгч бүр өөр өөр түвшний:

харах

шүүх

засах

батлах

экспортлох

эрхтэй байна.

4.2 Admin interface layer

Системийн үндсэн UI нь Django Admin дээр тулгуурласан custom admin юм.

InventoryAdminSite

Admin дотор:

Dashboard

Devices

Locations

Instrument Catalog

Calibration

Maintenance

Device Movement

Reports

QR Passport

Workflow

зэрэг хэсгүүд байрлана.

4.3 Application layer

Application layer дараах модулиудаас бүрдэнэ:

inventory/models.py

inventory/forms.py

inventory/views.py

inventory/urls.py

inventory/admin/...

templates

static JS/CSS

export / pdf / qr logic

4.4 Database layer

Database layer нь:

Reference data

Aimag

SumDuureg

Organization

InstrumentCatalog

lookup tables

Core master data

Location

Device

UserProfile

Lifecycle data

DeviceMovement

MaintenanceService

CalibrationRecord

ControlAdjustment

FailureIncident

Access/Audit

QRToken

AuditLog

LoginEvent

WorkflowAction

Knowledge/docs

ManualLibraryItem

DeviceAttachment

5. Main architecture domains

БҮРТГЭЛ системийг 8 том domain-аар харж болно.

5.1 Geographic domain

Байршлын иерархи

5.2 Asset domain

Багаж, төхөөрөмж, систем

5.3 Lifecycle domain

Калибровка, засвар, шилжилт, эвдрэл

5.4 Admin domain

Хэрэглэгчийн удирдлагын интерфэйс

5.5 Reporting domain

Тайлан, график, экспорт

5.6 QR / Passport domain

QR token, public lookup, PDF passport

5.7 Workflow / Audit domain

Approval, activity log, supervision

5.8 Knowledge domain

Гарын авлага, стандарт, хавсралт материал

6. Geographic architecture map
Country
 └── Aimag
      └── SumDuureg / District
           └── Location
                └── Device

Location нь дараах data-г агуулна:

аймаг

сум/дүүрэг

координат

өндөр

location type

station code

wigos_id

siting class

organization

7. Core asset architecture map
InstrumentCatalog
        │
        └── Device
                │
                ├── Location
                ├── Organization
                ├── QRToken
                ├── DeviceMovement
                ├── MaintenanceService
                ├── CalibrationRecord
                ├── ControlAdjustment
                ├── FailureIncident
                └── DeviceAttachment

Энд:

InstrumentCatalog = стандарт тодорхойлолт

Device = бодит объект

Lifecycle models = түүхэн мөр

8. Lifecycle architecture map
Device
 ├── Registration
 ├── Deployment
 ├── Operation
 ├── CalibrationRecord
 ├── FailureIncident
 ├── MaintenanceService
 ├── ControlAdjustment
 ├── DeviceMovement
 └── Decommission / Archive

Lifecycle domain-ийн гол зарчим:

Device = current state
Lifecycle tables = history state

9. Admin architecture map
InventoryAdminSite
│
├── admin_site.py
├── admin_devices.py
├── admin_locations.py
├── admin_catalog.py
├── admin_dashboard.py
├── admin_reports.py
├── admin_qr.py
└── admin_workflow.py

Admin нь модульчилсан байх ёстой.

10. Dashboard architecture map
Dashboard
│
├── General Dashboard
├── Table Dashboard
└── Graph Dashboard

Routes:

/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/

Dashboard data source:

Device queryset

Location queryset

lifecycle aggregates

report JSON endpoints

11. Reporting architecture map
Reports Module
│
├── On-screen summary
├── CSV export
├── Excel export
├── PDF export
└── Dashboard analytics

Report dimensions:

organization

aimag

location type

device kind

verification bucket

maintenance statistics

lifecycle status

12. Dynamic form architecture map

Device admin form нь dynamic logic-той.

Aimag → SumDuureg → Location
Kind → InstrumentCatalog
Role → filtered queryset

Энэ logic нь дараах түвшинд хэрэгжинэ:

forms.py

admin.py / admin_devices.py

views.py AJAX endpoints

JS in static files

13. Permission architecture map
User
 └── UserProfile
        │
        ├── role
        ├── organization
        └── aimag

Role-based behavior:

Superuser

full access

Central admin

national level management

Organization admin

байгууллагын түвшний access

Aimag engineer

зөвхөн өөрийн аймаг

delete permission байхгүй

filtered queryset

14. QR / Passport architecture map
Device
 ├── QRToken
 ├── Public Lookup URL
 └── Device Passport PDF

QR domain flow:

Device бүртгэгдэнэ

QR token үүснэ

Public lookup page нээгдэнэ

Passport PDF хэвлэнэ

Token revoke/regenerate хийж болно

15. Workflow / audit architecture map
User action
   │
   ├── ApprovalWorkflow
   ├── WorkflowAction
   ├── AuditLog
   └── LoginEvent

Use cases:

шилжилт хөдөлгөөний approval

калибровка баталгаажуулалт

засварын баталгаа

login / update / export history

16. Knowledge architecture map
Knowledge Layer
│
├── ManualLibraryItem
├── StandardDocument
├── DeviceAttachment
└── Training Material

Энэ нь engineer-үүдэд:

PDF

DOCX

зураг

стандарт

сургалтын материал

өгнө.

17. File / code architecture map
meteo_config/
├── settings.py
└── urls.py

inventory/
├── models.py
├── forms.py
├── views.py
├── urls.py
├── admin/
│   ├── admin_site.py
│   ├── admin_devices.py
│   ├── admin_locations.py
│   ├── admin_catalog.py
│   ├── admin_dashboard.py
│   ├── admin_reports.py
│   ├── admin_qr.py
│   └── admin_workflow.py
├── static/
└── migrations/

templates/
└── admin/
    ├── dashboard_general.html
    ├── dashboard_table.html
    └── dashboard_graph.html
18. Data flow map
Device registration flow
Admin User
   → Device Form
   → validation
   → Device save
   → QR generation (optional)
   → dashboard/report visibility
Device movement flow
User updates location
   → validation
   → Device.location changes
   → DeviceMovement record created
   → audit log recorded
   → dashboard/report updated
Calibration flow
Calibration record added
   → validation
   → last_verification_date updated
   → next_verification_date recalculated
   → verification bucket updated
   → report/dashboard affected
Report flow
User opens report/dashboard
   → filters selected
   → queryset aggregation
   → HTML / JSON / CSV / Excel output
19. Current known weak points

Одоогийн архитектурын хамгийн эмзэг хэсгүүд:

inventory/admin.py хэт том болсон

dashboard JS/template тогтворгүй

route conflict гарах магадлалтай

aimag → sum → location cascade алдаа өгч байсан

migration dependency эвдэрч байсан

QR/passport logic төвлөрсөн, refactor шаардлагатай

20. Refactor direction map
Current
   ↓
Monolithic admin.py
   ↓
Target
   ↓
Modular admin package
Current
   ↓
Scattered dashboard logic
   ↓
Target
   ↓
Dedicated dashboard module + clean templates + clean JS
Current
   ↓
Mixed lifecycle logic
   ↓
Target
   ↓
Separate lifecycle services / clearer model boundaries
21. National-scale expansion map
Current system
   ↓
Stable inventory platform
   ↓
Lifecycle-aware asset system
   ↓
QR + reporting + audit capable platform
   ↓
WIGOS / OSCAR aligned national platform

Future expansion:

WIGOS ID full use

national station metadata

radar / AWS / aerology as facility-level systems

central monitoring dashboards

compliance reporting

22. Documentation map

Энэ master map нь дараах файлуудыг нэгтгэнэ:

AI_MEMORY.md

PROJECT_CONTEXT.md

PROJECT_INDEX.md

BUGS_AND_PATCHES.md

DEV_WORKFLOW.md

BURTGEL_SYSTEM_ARCHITECTURE.md

BURTGEL_DATABASE_ARCHITECTURE.md

BURTGEL_MODEL_RELATIONSHIPS.md

BURTGEL_IMPLEMENTATION_ROADMAP.md

BURTGEL_ADMIN_ARCHITECTURE.md

Эдгээрийн дундаас:

MASTER_ARCHITECTURE_MAP = big picture

DATABASE_ARCHITECTURE = өгөгдлийн сан

ADMIN_ARCHITECTURE = UI/backend control plane

IMPLEMENTATION_ROADMAP = хөгжүүлэлтийн дараалал

BUGS_AND_PATCHES = operational memory

23. AI start-here block

Шинэ чатанд AI-д дараах дарааллаар уншуулна:

1. AI_MEMORY.md
2. PROJECT_CONTEXT.md
3. PROJECT_INDEX.md
4. BUGS_AND_PATCHES.md
5. BURTGEL_MASTER_ARCHITECTURE_MAP.md
6. BURTGEL_IMPLEMENTATION_ROADMAP.md

Энэ дараалал нь:

memory

context

navigation

known issues

big picture

execution plan

гэсэн логик урсгал үүсгэнэ.

24. One-screen summary

Хэрвээ БҮРТГЭЛ системийг 1 өгүүлбэрээр тодорхойлбол:

БҮРТГЭЛ бол ЦУОШГ-ын багаж, станц, систем, байршил, калибровка, засвар, шилжилт хөдөлгөөн, QR паспорт, тайлан, audit болон workflow-г Django Admin дээр төвлөрүүлэн удирдах үндэсний хэмжээний asset lifecycle management platform юм.

25. Final master map summary
Geography
   └── Aimag / Sum / Location

Assets
   └── InstrumentCatalog / Device

Lifecycle
   └── Movement / Maintenance / Calibration / Failure / Adjustment

Admin
   └── InventoryAdminSite / modular admin package

Dashboard
   └── General / Table / Graph

Reports
   └── CSV / Excel / PDF / Analytics

QR
   └── Token / Public Lookup / Passport

Permissions
   └── UserProfile / role / aimag restrictions

Audit & Workflow
   └── Approval / AuditLog / LoginEvent

Knowledge
   └── Manuals / Standards / Attachments
END