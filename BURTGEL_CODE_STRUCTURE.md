# BURTGEL CODE STRUCTURE

Project: БҮРТГЭЛ (BURTGEL)  
Repository: meteo_system  
Framework: Django  
Primary app: inventory

Энэ файл нь төслийн кодын бүтэц, гол файлууд, модулиудын үүрэг, debug хийх үед аль файлыг эхэлж нээхийг тайлбарлана.

---

# 1. Purpose

Энэ баримтын зорилго:

- project codebase-ийг хурдан ойлгох
- аль логик аль файлд байгааг мэдэх
- AI болон developer navigation map болох
- debug/refactor хийхэд эхлэх цэг өгөх

---

# 2. High-level code layout

```text
meteo_system/
│
├── manage.py
├── meteo_config/
├── inventory/
├── templates/
├── static/
├── media/                  (optional)
├── requirements.txt
└── documentation .md files

3. Project root files
manage.py

Django management command entry point.

Main usage:

runserver

makemigrations

migrate

shell

createsuperuser

requirements.txt

Python dependency list.

Documentation files

Project knowledge/context files:

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

4. Django config structure
meteo_config/
├── __init__.py
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py
settings.py

Системийн үндсэн тохиргоо.

Contains:

INSTALLED_APPS

MIDDLEWARE

DATABASES

STATIC_URL / STATICFILES_DIRS

MEDIA_URL / MEDIA_ROOT

Jazzmin config

language/timezone

custom constants

urls.py

Global routing.

Usually includes:

app urls

custom admin site urls

static/media serving in dev

This file is critical for:

admin route conflict

dashboard route debugging

asgi.py / wsgi.py

Deployment entry points.

5. Main application structure
inventory/
├── __init__.py
├── admin.py                 (current monolithic admin or compatibility layer)
├── apps.py
├── forms.py
├── models.py
├── tests.py
├── urls.py
├── views.py
├── migrations/
├── static/
├── templates/              (optional app-local templates)
└── management/
6. inventory/models.py

This is the core domain model file.

Typically contains:

Aimag

SumDuureg

Organization

Location

InstrumentCatalog

Device

DeviceMovement

MaintenanceService

CalibrationRecord

ControlAdjustment

FailureIncident

UserProfile

QRToken

ManualLibraryItem

SparePartOrder

SparePartOrderItem

Use this file for:

model changes

field additions

constraints

indexes

relationship debugging

migration planning

Open this first when:

migration fails

missing field error

queryset/filter issue tied to model fields

7. inventory/forms.py

Contains custom Django forms and ModelForms.

Common responsibilities:

Device form customization

Aimag → Sum → Location cascade setup

Kind → InstrumentCatalog filtering

conditional validation

custom labels/help texts

admin add/edit form logic

Open this first when:

dropdown not filtering

form validation failing

required field logic broken

initial values incorrect

8. inventory/views.py

Contains app views and JSON/AJAX endpoints.

Typical responsibilities:

ajax/load-sums/

ajax/location-options/

ajax/location-by-sum/

ajax/catalog-by-kind/

qr public lookup view

map view

report JSON endpoints (if not in admin module)

Open this first when:

AJAX request fails

dropdown data not loading

JSON response malformed

QR/public page broken

9. inventory/urls.py

Contains app-level routes.

Typical routes may include:

AJAX endpoints

map routes

QR public lookup

app public pages

Important note:
Dashboard/admin routes should not be duplicated here if they already live in InventoryAdminSite.get_urls().

Open this first when:

404 error

NoReverseMatch

route conflict

duplicate menu entry issue

10. inventory/admin.py

Current state:
This file may be monolithic and contain too much logic.

May include:

InventoryAdminSite

DeviceAdmin

LocationAdmin

InstrumentCatalogAdmin

dashboard views

report export actions

QR actions

custom filters

inline classes

admin routes

Open this first when:

admin page broken

dashboard route broken

list display/filter broken

admin action broken

permission behavior wrong

Recommended future role:
Compatibility layer or import aggregator if refactored into inventory/admin/.

11. Recommended future admin package structure
inventory/admin/
├── __init__.py
├── admin_site.py
├── admin_devices.py
├── admin_locations.py
├── admin_catalog.py
├── admin_dashboard.py
├── admin_reports.py
├── admin_qr.py
├── admin_workflow.py
└── admin_filters.py
admin_site.py

Contains:

InventoryAdminSite

custom admin URLs

top-level integration

admin_devices.py

Contains:

DeviceAdmin

lifecycle inlines

QR actions

verification status indicators

admin_locations.py

Contains:

Aimag admin

SumDuureg admin

Location admin

admin_catalog.py

Contains:

InstrumentCatalog admin

manufacturer/category logic

admin_dashboard.py

Contains:

dashboard views

aggregation helpers

chart/table/general handlers

admin_reports.py

Contains:

report hub

CSV/XLSX export

analytics data preparation

admin_qr.py

Contains:

QR token generation/revoke

device passport PDF

QR display helpers

admin_workflow.py

Contains:

approval workflows

audit-related admin integration

admin_filters.py

Contains:

reusable admin list filters

verification bucket filters

aimag/sum filters

location type filters

12. Templates structure

Global templates are usually here:

templates/
└── admin/
    ├── dashboard_general.html
    ├── dashboard_table.html
    ├── dashboard_graph.html
    ├── reports_hub.html
    ├── device/
    ├── qr/
    └── custom admin partials
dashboard_general.html

General summary dashboard template.

dashboard_table.html

Table-based dashboard.

dashboard_graph.html

Charts and graph dashboard.

These files are critical for:

JS errors

chart rendering issues

Leaflet issues

HTML/script nesting bugs

Open these first when:

L is not defined

points is not defined

dashboard blank page

chart not rendering

13. Static files structure

Possible locations:

inventory/static/
static/

Recommended structure:

static/
├── css/
├── js/
├── images/
└── vendor/

or

inventory/static/inventory/
├── css/
├── js/
└── images/

Common JS responsibilities:

dynamic dropdown cascade

dashboard chart initialization

map helpers

QR preview helpers

Open JS files first when:

onchange event not firing

AJAX loads but UI not updating

chart/map frontend errors

14. Migrations structure
inventory/migrations/
├── 0001_initial.py
├── 0002_....
├── ...
└── __init__.py

Use this folder for:

schema history

dependency tracking

data migration scripts

squash migrations

Open this first when:

CircularDependencyError

unapplied migration errors

field exists in DB but not model

migration order conflicts

15. Management commands structure

Possible location:

inventory/management/commands/

Typical commands may include:

import_admin_units

import_locations_csv

import_instrument_catalog

import_aimag_engineers

data backfill commands

Use these for:

initial data import

cleanup tasks

production data repair

bulk fixes

Open this first when:

CSV import broken

lookup data missing

bulk update needed

16. Code responsibility map
Routing

Files:

meteo_config/urls.py

inventory/urls.py

inventory/admin.py or inventory/admin/admin_site.py

Data model

Files:

inventory/models.py

inventory/migrations/

Forms and validation

Files:

inventory/forms.py

Admin control plane

Files:

inventory/admin.py

future inventory/admin/*

AJAX / JSON

Files:

inventory/views.py

urls.py

JS files

Dashboard UI

Files:

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

admin dashboard view code

Reporting/export

Files:

admin_reports.py or admin.py

views.py

templates/admin/reports_*.html

QR / passport

Files:

admin_qr.py or admin.py

views.py

urls.py

templates/admin/qr/

PDF helper code

17. Main debug entry points
Route bug

Open in this order:

meteo_config/urls.py

inventory/urls.py

inventory/admin.py

Device form bug

Open in this order:

inventory/forms.py

inventory/views.py

inventory/admin.py

related JS file

Dashboard bug

Open in this order:

inventory/admin.py

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

related JS/static assets

Migration bug

Open in this order:

inventory/models.py

inventory/migrations/

admin/forms referencing missing fields

Permission bug

Open in this order:

UserProfile in models.py

DeviceAdmin / LocationAdmin get_queryset

has_*_permission methods

custom filters

QR bug

Open in this order:

admin QR action code

QR model/token logic

urls.py

views.py

PDF generation code

18. Critical code hotspots

These are the most fragile/high-value files:

inventory/admin.py

inventory/models.py

inventory/forms.py

inventory/views.py

meteo_config/urls.py

inventory/urls.py

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

These files should be checked first in almost every serious bug.

19. Suggested refactor map

Current likely state:

inventory/admin.py   → too large
inventory/views.py   → mixed public + ajax + reporting
templates/admin/     → some logic too inline
static/js/           → selectors may be fragile

Target state:

inventory/
├── admin/
├── services/
├── selectors/
├── forms/
├── views/
│   ├── ajax.py
│   ├── public.py
│   └── reports.py
├── pdf/
├── qr/
└── utils/

This refactor is optional but recommended for long-term maintainability.

20. Example future code structure
inventory/
├── models.py
├── forms.py
├── urls.py
├── views.py
├── admin/
│   ├── __init__.py
│   ├── admin_site.py
│   ├── admin_devices.py
│   ├── admin_locations.py
│   ├── admin_catalog.py
│   ├── admin_dashboard.py
│   ├── admin_reports.py
│   ├── admin_qr.py
│   └── admin_workflow.py
├── services/
│   ├── lifecycle_service.py
│   ├── passport_service.py
│   ├── report_service.py
│   └── movement_service.py
├── pdf/
│   └── device_passport.py
├── qr/
│   └── token_service.py
├── management/
│   └── commands/
├── migrations/
└── static/
21. AI navigation hint

When AI helps on this repo, it should use this logic:

first identify bug category

open the smallest likely file set

avoid changing unrelated files

check route/form/model/template alignment together

prefer modular refactor over adding more code into monolithic admin.py

22. One-screen summary

If someone asks “Where is what in BURTGEL codebase?”:

global config → meteo_config/

domain models → inventory/models.py

forms → inventory/forms.py

ajax/public views → inventory/views.py

app routes → inventory/urls.py

admin control plane → inventory/admin.py or inventory/admin/

dashboards → templates/admin/dashboard_*.html

static js/css → static/ or inventory/static/

schema history → inventory/migrations/

bulk import/data fix → inventory/management/commands/

END