# BURTGEL BUGS AND PATCHES LOG
БҮРТГЭЛ системийн алдаа, засвар, patch history

---

# How to use this file

Энэ файлд дараах зүйлсийг бүртгэнэ:

- илэрсэн алдаа
- root cause
- хийсэн засвар
- patch / commit
- affected files
- status

---

# BUG TEMPLATE

## Bug ID
BUG-XXXX

## Date
YYYY-MM-DD

## Area
(admin / dashboard / models / forms / migrations / JS / reports)

## Description
Алдааны тайлбар

## Root cause
Яагаад ийм алдаа гарсан

## Fix
Хийсэн засвар

## Files affected
file list

## Patch / commit
commit hash эсвэл patch

## Status
OPEN / FIXED / TESTING

---

# BUG HISTORY

---

## BUG-0001
### Dashboard route 404

Date  
2026-03

Area  
admin routing

Description  

/admin/dashboard/table/

route ажиллахгүй 404 өгсөн.

Django URL resolver дээр route олдоогүй.

Root cause  

dashboard route зөвхөн `InventoryAdminSite.get_urls()` дотор байсан.

Гэхдээ:

meteo_config/urls.py
inventory/urls.py


хооронд route conflict үүссэн.

Fix  

Dashboard route-уудыг зөвхөн custom admin site дээр үлдээж:

InventoryAdminSite.get_urls()


ашигласан.

Files affected

inventory/admin.py
meteo_config/urls.py
inventory/urls.py


Status  

FIXED

---

## BUG-0002
### Dashboard JS crash

Area  

dashboard templates

Description  

Dashboard map болон chart ажиллахгүй.

Console error:

L is not defined
points is not defined


Root cause  

HTML `<script>` tag-уудыг `<script>` block дотор давхар оруулсан.

Example:

<script> <link rel="stylesheet"> <script src="..."> </script>

Fix  

Script-үүдийг HTML level дээр салгасан.

Files affected

templates/admin/dashboard_general.html
templates/admin/dashboard_graph.html


Status  

FIXED

---

## BUG-0003
### UTF-8 font corruption

Area  

patch / encoding

Description  

Patch apply хийхэд Монгол текст эвдэрсэн.

Example

Ð±Ð°Ð¹Ñ€ÑˆÐ¸Ð»


Root cause  

Patch файл BOM encoding-той байсан.

Fix  

Patch-ийг UTF-8 no-BOM болгож дахин үүсгэсэн.

Commands

git apply --reject patch.diff


Files affected  

multiple templates / admin files

Status  

FIXED

---

## BUG-0004
### Aimag → Sum cascade not loading

Area  

DeviceAdmin form

Description  

Aimag сонгоход Sum dropdown update хийхгүй.

Root cause  

AJAX endpoint:

ajax/load-sums/


JS selector таараагүй.

Fix  

JS selector зассан.

Files affected

inventory/forms.py
inventory/views.py
inventory/static/js/device_form.js


Status  

FIXED

---

## BUG-0005
### Duplicate dashboard menu

Area  

admin UI

Description  

Admin sidebar дээр Dashboard хоёр удаа харагдсан.

Root cause  

Route давхар бүртгэгдсэн:

inventory/urls.py
InventoryAdminSite.get_urls()


Fix  

Dashboard route-уудыг `inventory/urls.py`-ээс устгасан.

Status  

FIXED

---

## BUG-0006
### Migration dependency error

Area  

migrations

Description  

Migration cycle dependency үүссэн.

Example

CircularDependencyError


Root cause  

Branch merge хийх үед migration dependency эвдэрсэн.

Fix  

Migration squash хийсэн.

Example


0001_squashed_0046_backfill_device_system_links


Status  

FIXED

---

## BUG-0007
### DeviceAdmin complexity

Area  

admin architecture

Description  

`inventory/admin.py` файл хэт том болсон.

Root cause  

Admin logic, dashboard views, QR logic бүгд нэг файлд байсан.

Fix (planned)

Refactor хийх:


admin.py
admin_dashboard.py
admin_reports.py
admin_qr.py


Status  

OPEN

---

# PATCH HISTORY

---

## PATCH-001
### Admin architecture cleanup

Date  

2026-03

Description  

Admin routing болон dashboard route-уудыг цэвэрлэсэн.

Files


inventory/admin.py
meteo_config/urls.py


---

## PATCH-002
### Dashboard stabilization

Date  

2026-03

Description  

Dashboard JS болон template separation.

Files


dashboard_general.html
dashboard_table.html
dashboard_graph.html


---

## PATCH-003
### Location cascade fix

Date  

2026-03

Description  

Aimag → Sum → Location cascade AJAX зассан.

Files


inventory/forms.py
inventory/views.py
inventory/admin.py


---

# ACTIVE BUGS

Одоогоор шалгах шаардлагатай:

- DeviceAdmin form edge cases
- dashboard performance
- QR public lookup
- migration stability
- admin.py refactor

---

# DEBUG CHECKLIST

Алдаа гарвал дараах дарааллаар шалгана

1  


python manage.py check


2  


python manage.py showmigrations


3  


python manage.py migrate


4  

browser console

5  

route tree


urls.py
admin.py


---

# FINAL NOTE

Энэ файл нь:

- bug history
- patch history
- troubleshooting guide

гурвыг нэг дор хадгалах зориулалттай.