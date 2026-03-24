# БҮРТГЭЛ SYSTEM – PROJECT CONTEXT

## Project
БҮРТГЭЛ – ЦУОШГ-ын багаж, станц, системийн бүртгэл болон lifecycle удирдлагын Django систем.

Repository:
https://github.com/tushigee79/meteo_system

---

# 1. CORE ARCHITECTURE

## Main models

Location
- aimag
- sum_duureg
- location_type (METEO / HYDRO / AWS)

Device
- serial_number (unique)
- instrument
- location
- status

InstrumentCatalog
- instrument_name
- kind
- verification_cycle_months

DeviceMovement
- device
- from_location
- to_location
- date
- reason
- approved_by

MaintenanceService
- service_date
- engineer
- organization
- result

ControlAdjustment
- adjustment_date
- result

---

# 2. SYSTEM LEVEL ASSETS

Бүртгэх системүүд:

- Weather radar
- Aerological station
- AWS
- Hydrological station

System → Subsystems → Instruments hierarchy

---

# 3. ADMIN ARCHITECTURE

Custom admin site:

InventoryAdminSite

Admin modules

Dashboard
- dashboard_general
- dashboard_table
- dashboard_graph

ReportsHub

Map
Leaflet based station map

---

# 4. FEATURES

Implemented / In progress

✔ Device QR code
✔ Device Passport PDF
✔ Calibration expiry monitoring
✔ Device movement history
✔ Dashboard statistics
✔ Aimag / Sum cascade filter
✔ WMO metadata support

---

# 5. SECURITY

User roles

Admin
AimagEngineer

Rules

- AimagEngineer sees only own aimag
- delete permission disabled
- audit logging enabled

OTP / temporary password (planned)

---

# 6. WORKFLOW

Device lifecycle

Purchase
Registration
Deployment
Calibration
Maintenance
Movement
Decommission

---

# 7. GIT WORKFLOW

Branches

main → production
dev → development
feature/* → new features

Example

feature/dashboard
feature/device-passport
feature/workflow

Merge flow

feature → dev → main

---

# 8. CHATGPT CONTEXT KEYWORDS

Use these keywords in a new chat to continue work.

burtgel → full system context  
admin → admin.py architecture  
graph → dashboard graphs  
table → dashboard tables  
migration → migration debugging  
qr → device passport / QR  
байршил → aimag / sum filtering  
home and work → git workflow between computers

---

# 9. CURRENT DEVELOPMENT STATE

System version

v1.0 – Stability phase

Working items

- Admin dashboard fixes
- Location cascade filtering
- Device passport QR
- Reports export

---

# 10. IMPORTANT PATHS

Project root

D:\meteo_system\meteo_system

Main app

inventory/

Admin

inventory/admin.py

Models

inventory/models.py

Templates

templates/admin/

---

END OF CONTEXT