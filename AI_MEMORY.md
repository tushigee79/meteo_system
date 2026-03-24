# AI MEMORY – BURTGEL SYSTEM

This file restores the full working context for the BURTGEL system when starting a new AI chat.

---

# SYSTEM NAME
БҮРТГЭЛ – ЦУОШГ instrumentation registry system.

Purpose:
National system to manage meteorological instruments, stations, radar, aerology, AWS, hydrology devices and their lifecycle.

Repository
https://github.com/tushigee79/meteo_system

---

# TECHNOLOGY STACK

Backend
Django 4.2

Frontend
Django Admin + Jazzmin

Charts
Chart.js / ECharts

Map
Leaflet

Database
SQLite (development)

---

# CORE MODELS

Location  
Device  
InstrumentCatalog  
DeviceMovement  
MaintenanceService  
ControlAdjustment  

---

# LOCATION STRUCTURE

Location hierarchy

Aimag  
SumDuureg  
Location

Location types

METEO  
HYDRO  
AWS  

---

# DEVICE STRUCTURE

Device fields

serial_number (unique)  
instrument  
location  
status  
verification dates  

Device lifecycle

Purchase  
Registration  
Deployment  
Calibration  
Maintenance  
Movement  
Decommission  

---

# SYSTEM LEVEL ASSETS

Special device types

Weather radar  
Aerological station  
AWS station  
Hydrological station  

Structure

System → Subsystems → Instruments

---

# ADMIN ARCHITECTURE

Custom admin site

InventoryAdminSite

Main modules

Dashboard  
ReportsHub  
Device admin  
Location admin  

Dashboard pages

dashboard_general  
dashboard_table  
dashboard_graph  

---

# IMPLEMENTED FEATURES

QR code for devices  
Device Passport PDF  
Calibration expiry monitoring  
Device movement history  
Aimag / Sum cascade filtering  
Dashboard statistics  
CSV / Excel export  

---

# SECURITY MODEL

Roles

Admin  
AimagEngineer  

Rules

AimagEngineer sees only own aimag data  
Delete permission disabled  
Audit logging required  

OTP / temporary password (planned)

---

# GIT WORKFLOW

Branches

main → production  
dev → development  
feature/* → development features  

Example branches

feature/dashboard  
feature/device-passport  
feature/workflow  

Merge order

feature → dev → main

---

# IMPORTANT FILE PATHS

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

# CHAT CONTINUATION KEYWORDS

Use these keywords to continue previous work.

burtgel  
admin  
graph  
table  
migration  
qr  
байршил  
home and work  

---

# CURRENT DEVELOPMENT STATE

Version

v1.0 – stability phase

Current tasks

Admin dashboard fixes  
Location cascade filtering  
Device passport QR  
Reports export  

---

END OF AI MEMORY