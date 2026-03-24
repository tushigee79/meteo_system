# БҮРТГЭЛ (BURTGEL)

**БҮРТГЭЛ** нь Монгол Улсын Цаг уур, орчны шинжилгээний байгууллагын багаж, станц, системүүдийг бүртгэх, удирдах, lifecycle хянах зориулалттай Django-д суурилсан платформ юм.

Repository  
https://github.com/tushigee79/meteo_system

---

# System overview

BURTGEL систем нь дараах asset-уудыг удирдана.

• цаг уурын станц  
• ус судлалын станц  
• AWS автомат станц  
• аэрологийн станц  
• цаг уурын радар  
• эталон багаж  
• хэмжил зүйн лабораторийн багаж

---

# Main capabilities

Системийн үндсэн боломжууд:

- багаж бүртгэл
- байршлын удирдлага
- device lifecycle tracking
- calibration record
- maintenance history
- device movement tracking
- QR device passport
- тайлан ба статистик
- role-based access
- audit trail

---

# Technology stack

Framework

- Django

Database

- SQLite (development)
- PostgreSQL (production ready)

Frontend

- Django Admin
- Jazzmin
- Chart.js / ECharts
- Leaflet maps

---

# Project structure

meteo_system
│
├─ meteo_config
│
├─ inventory
│ ├─ models.py
│ ├─ admin.py
│ ├─ forms.py
│ ├─ views.py
│ └─ urls.py
│
├─ templates
│
├─ static
│
└─ documentation files


---

# Documentation

Project documentation files:


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
BURTGEL_MASTER_ARCHITECTURE_MAP.md
BURTGEL_QUICKSTART_FOR_AI.md
BURTGEL_CODE_STRUCTURE.md
BURTGEL_DEBUG_PLAYBOOK.md
BURTGEL_GIT_WORKFLOW.md
BURTGEL_RELEASE_CHECKLIST.md


These documents describe the full architecture, development workflow, debugging strategy, and deployment process.

---

# Quick start

Clone repository

```bash
git clone https://github.com/tushigee79/meteo_system.git

Enter project

cd meteo_system

Create virtual environment

python -m venv venv

Activate environment

Windows

venv\Scripts\activate

Install dependencies

pip install -r requirements.txt

Apply migrations

python manage.py migrate

Create superuser

python manage.py createsuperuser

Run development server

python manage.py runserver
Admin interface

Default admin

/admin/

Custom dashboard routes

/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/
Core models

Location hierarchy

Aimag
 └─ SumDuureg
      └─ Location
           └─ Device

Device lifecycle

Device
 ├─ DeviceMovement
 ├─ MaintenanceService
 ├─ CalibrationRecord
 ├─ ControlAdjustment
 └─ FailureIncident
QR device passport

Each device can generate:

QR token

public lookup page

printable PDF passport

Example route

/qr/public/<uuid>
Dashboard

Dashboard modules:

General statistics

Table dashboard

Graph analytics

Includes:

device statistics

aimag distribution

organization distribution

lifecycle status

Development workflow

Git workflow documented in:

BURTGEL_GIT_WORKFLOW.md

Typical workflow

git pull
work
git add .
git commit
git push
Debugging

Debugging guide

BURTGEL_DEBUG_PLAYBOOK.md

Use this file for:

route issues

admin crashes

dashboard errors

migration problems

form cascade issues

Release process

Before production deploy use:

BURTGEL_RELEASE_CHECKLIST.md
Future roadmap

See

BURTGEL_IMPLEMENTATION_ROADMAP.md

Planned features include:

advanced analytics

workflow approvals

system monitoring

map-based station visualization

national instrument registry

Author

Project initiated and developed for meteorological instrumentation management.

License

Internal system (custom deployment).