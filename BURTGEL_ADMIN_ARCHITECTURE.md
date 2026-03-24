# BURTGEL ADMIN ARCHITECTURE

Project: БҮРТГЭЛ (BURTGEL)  
Framework: Django  
Admin UI: Django Admin + Jazzmin  

Энэ баримт нь системийн **Admin архитектур, модульчлал, routing, permission логик, dashboard integration**-ийг тайлбарлана.

---

# 1. Purpose

Admin interface нь системийн:

• багаж бүртгэл  
• байршлын удирдлага  
• lifecycle tracking  
• тайлан  
• QR паспорт  
• системийн хяналт  

зэрэг бүх үйлдлийн **гол хэрэглэгчийн интерфэйс** юм.

---

# 2. Admin design philosophy

BURTGEL admin нь дараах зарчмыг баримтална.

1️⃣ Custom AdminSite ашиглах  
2️⃣ Admin module-уудыг салгаж modular болгох  
3️⃣ Dashboard-ийг admin-д нэгтгэх  
4️⃣ Role-based access control  
5️⃣ Large-scale data navigation support

---

# 3. Admin site structure

Систем нь стандарт Django admin-оос гадна custom admin site ашиглана.

```text
InventoryAdminSite

Example

class InventoryAdminSite(AdminSite):
    site_header = "BURTGEL System"
    site_title = "BURTGEL Admin"

Admin root:

/admin/
4. Admin routing architecture

Admin routes:

/admin/
/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/
/admin/reports/

Routing chain:

meteo_config/urls.py
        ↓
InventoryAdminSite.urls
        ↓
custom admin views
5. Admin module structure

Admin code modular байх ёстой.

Recommended structure:

inventory/admin/
    __init__.py
    admin_site.py
    admin_devices.py
    admin_locations.py
    admin_catalog.py
    admin_dashboard.py
    admin_reports.py
    admin_qr.py
    admin_workflow.py

Benefits

• код уншихад амар
• bug isolate хийхэд амар
• testing хялбар

6. Admin site configuration

File

admin_site.py

Responsibilities

• AdminSite class
• global actions
• dashboard routes
• reports routes

Example

class InventoryAdminSite(AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/general/", ...),
            path("dashboard/table/", ...),
            path("dashboard/graph/", ...),
        ]
        return custom_urls + urls
7. Device admin module

File

admin_devices.py

Handles

• Device
• DeviceMovement
• MaintenanceService
• CalibrationRecord
• ControlAdjustment

Features

• inline lifecycle records
• QR actions
• verification status indicators

Example

class DeviceAdmin(admin.ModelAdmin):
    list_display = (...)
    search_fields = (...)
8. Location admin module

File

admin_locations.py

Handles

• Location
• Aimag
• SumDuureg

Features

• map integration
• hierarchy navigation
• station metadata

9. Catalog admin module

File

admin_catalog.py

Handles

• InstrumentCatalog
• Manufacturer
• Device type

Purpose

Central instrument specification management.

10. Dashboard admin module

File

admin_dashboard.py

Handles

• system overview
• statistics
• charts
• map

Dashboard types

General
Table
Graph

11. Reports admin module

File

admin_reports.py

Handles

• CSV export
• Excel export
• statistical reports

Example reports

• devices by organization
• devices by aimag
• calibration status

12. QR admin module

File

admin_qr.py

Handles

• QR token generation
• revoke token
• device passport generation

Admin actions

generate_qr
revoke_qr
download_device_passport
13. Workflow admin module

File

admin_workflow.py

Handles

• approvals
• verification workflows
• audit actions

Future extension.

14. Inline architecture

Device admin дээр lifecycle model-ууд inline байдлаар харагдана.

Device
 ├─ DeviceMovementInline
 ├─ MaintenanceInline
 ├─ CalibrationInline
 └─ AdjustmentInline

Benefits

• lifecycle history нэг дэлгэц дээр
• audit easier

15. Admin permissions

Admin permission system:

Superuser
Central admin
Organization admin
Aimag engineer

16. Aimag engineer restriction

Аймгийн инженер:

• зөвхөн өөрийн аймгийн data харна
• delete permission байхгүй

Implementation

get_queryset()
has_delete_permission()

Example

def get_queryset(self, request):
    qs = super().get_queryset(request)
    if request.user.profile.role == "aimag_engineer":
        return qs.filter(location__aimag=request.user.profile.aimag)
    return qs
17. Admin UI (Jazzmin)

Admin UI theme

Jazzmin

Features

• sidebar navigation
• icons
• dark mode
• custom dashboard links

18. Admin performance optimization

Large dataset үед:

• list_filter ашиглах
• search_fields optimize хийх
• select_related ашиглах
• pagination тохируулах

Example

list_select_related = ("location", "catalog")
19. Admin debugging

Admin алдаа гарвал шалгах.

1

inventory/admin.py

2

inventory/admin/

3

meteo_config/urls.py

4

templates/admin

20. Known admin complexity

BURTGEL admin-д хамгийн төвөгтэй хэсгүүд:

• DeviceAdmin
• Dashboard JS
• location cascade logic
• QR passport generation

21. Recommended refactor priority

Priority

1 Admin module split
2 DeviceAdmin cleanup
3 Dashboard stabilization
4 Report modularization
5 QR integration

22. Long-term admin vision

BURTGEL admin нь дараах боломжуудтай болно.

• real-time dashboard
• lifecycle monitoring
• map-based navigation
• workflow approvals
• automated reporting

END