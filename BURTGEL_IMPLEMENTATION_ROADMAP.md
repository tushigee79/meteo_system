## AI START HERE
Read in this order:
1. AI_MEMORY.md
2. PROJECT_CONTEXT.md
3. PROJECT_INDEX.md
4. BUGS_AND_PATCHES.md
5. BURTGEL_IMPLEMENTATION_ROADMAP.md

# BURTGEL IMPLEMENTATION ROADMAP

Project: БҮРТГЭЛ (BURTGEL)  
System: Meteorological Instrument & Station Management Platform  
Framework: Django  
Primary app: inventory

---

# 1. Purpose

Энэ баримт нь БҮРТГЭЛ системийг хөгжүүлэх дараалал, үе шат, хэрэгжилтийн төлөвлөгөөг тодорхойлно.

Roadmap нь:

• системийн тогтвортой байдал  
• lifecycle management  
• reporting  
• QR / passport  
• workflow / audit  
• national platform  

гэсэн шатлалтайгаар хэрэгжинэ.

---

# 2. Current project status

Одоогийн системийн байдал:

✔ Core models бий  
✔ Admin customization хийгдсэн  
✔ Dashboard эхний хувилбар байгаа  
✔ Location hierarchy байгаа  
✔ Device inventory ажиллаж байгаа  

Одоогийн гол зорилго:

System stability.

---

# 3. Implementation phases

System хөгжүүлэлтийг 4 үндсэн үе шатанд хуваана.

Phase 1  
System Stabilization

Phase 2  
Device Lifecycle

Phase 3  
Reporting & Analytics

Phase 4  
National Platform Expansion

---

# 4. Phase 1 – System stabilization

Goal  
Системийг production-д бэлэн болгох.

## 4.1 Admin architecture cleanup

Current problem

inventory/admin.py хэт том болсон.

Refactor

inventory/admin/
admin_site.py
admin_devices.py
admin_locations.py
admin_dashboard.py
admin_reports.py
admin_qr.py


Benefits

• maintainability  
• debugging easy  
• modular structure  

---

## 4.2 Admin routing stabilization

Fix routes


/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/


Check

meteo_config/urls.py  
inventory/admin.py  
inventory/urls.py  

---

## 4.3 DeviceAdmin form stabilization

Dynamic logic


Aimag → Sum → Location
Kind → InstrumentCatalog


Ensure

• AJAX endpoints stable  
• form validation stable  
• queryset filtering correct  

---

## 4.4 Migration cleanup

Tasks

• remove migration conflicts  
• squash old migrations  
• ensure dependency chain correct  

Commands


python manage.py showmigrations
python manage.py migrate


---

## 4.5 Dashboard stabilization

Fix

• JS crash  
• template script nesting  
• chart rendering  
• Leaflet map

Files


dashboard_general.html
dashboard_table.html
dashboard_graph.html


---

# 5. Phase 2 – Device lifecycle management

Goal  
Багажийн амьдралын мөчлөгийг бүрэн хянах.

---

## 5.1 DeviceMovement

Track

• source location  
• destination location  
• movement date  
• approval  

Outcome

Device relocation history.

---

## 5.2 MaintenanceService

Track

• service date  
• engineer / organization  
• diagnosis  
• action  
• result  

---

## 5.3 CalibrationRecord

Track

• calibration date  
• valid until  
• lab  
• certificate  

Automation

Update


Device.last_verification_date
Device.next_verification_date


---

## 5.4 ControlAdjustment

Track

• inspection  
• tuning  
• adjustment

---

## 5.5 FailureIncident

Track

• incident  
• severity  
• cause  
• resolution  

---

# 6. Phase 3 – Reporting & analytics

Goal  
Системээс удирдлагын шийдвэр гаргах тайлан гаргах.

---

## 6.1 Dashboard analytics

Charts

• device count by organization  
• device count by aimag  
• verification status  
• maintenance statistics  

---

## 6.2 Reporting module

Reports

• organization report  
• aimag report  
• device type report  
• calibration status  

Export

CSV  
Excel  
PDF

---

## 6.3 Advanced filters

Filters

• aimag  
• location type  
• device kind  
• verification bucket  

---

# 7. Phase 4 – QR passport system

Goal  
Багаж бүрийг QR code-оор хянах.

---

## 7.1 QRToken system

Generate

• QR token  
• public lookup  

---

## 7.2 Public device page

Route


qr/device/<uuid>


Display

• device information  
• location  
• last calibration  
• maintenance history  

---

## 7.3 Device Passport PDF

Printable A4 passport.

Include

• QR code  
• device details  
• calibration history  
• maintenance records  

---

# 8. Phase 5 – Workflow & audit

Goal  
Системийн хяналтын механизм бий болгох.

---

## 8.1 Approval workflow

Examples

• device relocation approval  
• maintenance validation  
• calibration confirmation  

---

## 8.2 Audit log

Track

• user action  
• before / after state  
• timestamp  
• IP  

---

# 9. Phase 6 – National platform expansion

Goal  
БҮРТГЭЛ системийг улсын хэмжээний платформ болгох.

---

## 9.1 WIGOS / OSCAR integration

Add


Location.wigos_id


---

## 9.2 Radar / AWS system models

Add


SystemAsset
SystemComponent


---

## 9.3 National reporting

Possible outputs

• national station inventory  
• calibration compliance  
• device distribution map  

---

# 10. Development priorities

Priority order

1 System stability  
2 Lifecycle models  
3 Dashboard analytics  
4 QR passport  
5 Workflow & audit  
6 National integration  

---

# 11. Recommended timeline

Example timeline

Phase 1  
1–2 months

Phase 2  
2–3 months

Phase 3  
1–2 months

Phase 4  
1 month

Phase 5  
1 month

Phase 6  
future expansion

---

# 12. Risks

Possible risks

• migration conflicts  
• admin complexity  
• dashboard JS instability  
• inconsistent location data  

Mitigation

• modular admin architecture  
• clean migrations  
• strict data validation  

---

# 13. Success criteria

System is successful when:

✔ бүх багаж бүртгэгдсэн  
✔ lifecycle бүртгэл бүрэн  
✔ аймаг бүр ашиглаж байгаа  
✔ тайлан автоматаар гарч байгаа  
✔ QR passport ажиллаж байгаа  

---

# END