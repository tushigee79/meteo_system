# BURTGEL DEBUG PLAYBOOK

Project: БҮРТГЭЛ (BURTGEL)  
Repository: meteo_system  
Framework: Django  
Primary app: inventory

Энэ файл нь БҮРТГЭЛ системийн хамгийн түгээмэл алдаануудыг оношлох, тусгаарлах, засах дарааллыг тодорхойлно.

---

# 1. Purpose

Энэ playbook-ийн зорилго:

- алдаа гарсан үед сандралгүй зөв дарааллаар шалгах
- route, form, model, template, migration, QR, permission асуудлыг хурдан тусгаарлах
- AI болон developer аль аль нь ижил логикоор debug хийх
- нэг асуудлыг засахдаа өөр асуудал үүсгэхээс сэргийлэх

---

# 2. Golden rules

1. Нэг удаад нэг л асуудлыг isolate хий
2. Эхлээд error log / traceback-ийг бүрэн унш
3. Route, model, form, template-ийг холбож шалга
4. Шууд олон файлд том өөрчлөлт бүү хий
5. Patch apply хийхээс өмнө branch эсвэл backup үүсгэ
6. Migration асуудалтай үед admin/template засахаасаа өмнө schema-г шалга
7. Dashboard алдаанд browser console-г заавал шалга
8. UTF-8 encoding-г эвдэхгүй байх

---

# 3. Universal first check

Ямар ч алдаа гарсан эхний алхамууд:

## Step 1
Команд ажиллуул

```bash
python manage.py check

Step 2

Migration төлөв шалга

python manage.py showmigrations
Step 3

Schema plan шалга

python manage.py migrate --plan
Step 4

Server log унш

python manage.py runserver
Step 5

Browser console шалга

JS error байна уу

network request failed байна уу

404 / 500 response байна уу

4. Debug category map

Алдааг эхлээд ангил.

Category A

Route / URL / NoReverseMatch / 404

Category B

Admin page crash / 500

Category C

Dashboard blank / JS error / map/chart failure

Category D

Device form cascade / dropdown / validation error

Category E

Migration / model / field mismatch

Category F

Permission / queryset / role filtering error

Category G

QR / passport / PDF error

Category H

Encoding / patch / Mongolian text corruption

5. Route debugging playbook

Symptoms:

404

NoReverseMatch

wrong admin path

duplicate route

dashboard URL not found

Check order

meteo_config/urls.py

inventory/urls.py

inventory/admin.py or inventory/admin/admin_site.py

Questions to ask

Route global urlconf дээр бүртгэгдсэн үү?

custom admin site дээр route орсон уу?

inventory/urls.py дээр давхар route байна уу?

name= давхцаж байна уу?

/admin/ ба /django-admin/ prefix зөрсөн үү?

Common fixes

Dashboard route-уудыг зөвхөн custom admin site дээр үлдээх

app urls ба admin urls-ийг давхардуулахгүй байх

template дахь url tag дээрх route name-ийг тааруулах

Quick commands
python manage.py check
Likely files

meteo_config/urls.py

inventory/urls.py

inventory/admin.py

6. Admin page crash playbook

Symptoms:

/admin/ эсвэл custom admin home 500 өгнө

changelist/add/change page render болохгүй

import error

attribute error

Check order

traceback line

inventory/admin.py

model/admin referenced fields

template override байгаа эсэх

Common causes

admin list_display дээр байхгүй field

renamed field-ийг admin ашиглаж байгаа

broken queryset annotation

missing import

custom admin site route conflict

broken custom form

Quick isolate method

list_display-г түр багасга

custom form-ийг түр салга

custom action-уудыг түр comment хий

recently changed field-үүдийг models.py дээр шалга

Likely files

inventory/admin.py

inventory/models.py

inventory/forms.py

7. Dashboard debugging playbook

Symptoms:

dashboard blank page

chart харагдахгүй

map ажиллахгүй

JS error: L is not defined

JS error: points is not defined

Check order

browser console

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

dashboard view code in admin

network tab → JSON endpoints

Common causes

nested <script> tag

<link> tag-ийг <script> дотор хийсэн

Leaflet/ECharts/Chart.js script load болоогүй

context variable template рүү дамжаагүй

JSON endpoint malformed

HTML ба JSON-г нэг view дээр буруу mix хийсэн

Fix strategy

template head/body script-үүдийг цэгцэл

inline JS-ийг external JS рүү салга

context key-үүдийг сервер талд баталгаажуул

JSON endpoint-ийг browser дээр шууд нээж response шалга

Likely files

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

inventory/admin.py

8. Device form debugging playbook

Symptoms:

Aimag сонгоход Sum ачаалахгүй

Sum сонгоход Location шүүгдэхгүй

Kind сонгоход InstrumentCatalog өөрчлөгдөхгүй

add form ба change form өөрөөр ажиллана

validation fail

Check order

inventory/forms.py

inventory/views.py

inventory/admin.py

related JS file

browser network tab

Questions to ask

AJAX endpoint зөв URL-тай юу?

select element id/name зөв үү?

onchange event fire болж байна уу?

queryset server side дээр зөв filter хийж байна уу?

change form initial state зөв populate болсон уу?

Common causes

selector mismatch

wrong endpoint path

admin rendered field id өөр болсон

queryset none буцааж байгаа

request.GET parameter name буруу

form __init__ дээр initial filter хийгдээгүй

Likely files

inventory/forms.py

inventory/views.py

inventory/admin.py

inventory/static/...js

9. Migration debugging playbook

Symptoms:

unapplied migrations

CircularDependencyError

field exists in DB but not model

model has field but DB table missing

server works partly but admin crash

Check order

inventory/models.py

inventory/migrations/

showmigrations

migrate --plan

recent branch merge history

Commands
python manage.py showmigrations
python manage.py migrate --plan
python manage.py makemigrations
python manage.py migrate
Common causes

branch merge хийж migration dependency эвдэрсэн

squash migration partial state

model code өөрчлөгдсөн ч migration үүсгээгүй

stale sqlite db

migration applied order зөрсөн

Fix strategy

schema vs model first compare

fake migration хийхээс өмнө маш сайн шалга

data migration ба schema migration-ийг ялга

squashed migration ашиглаж байвал dependency-г унш

Likely files

inventory/models.py

inventory/migrations/*

10. Permission debugging playbook

Symptoms:

Aimag engineer бүх data харж байна

delete button алга болохгүй

queryset filter буруу

admin menu role-based харагдахгүй

Check order

UserProfile model

get_queryset()

has_view_permission()

has_change_permission()

has_delete_permission()

custom admin site menu logic

Common causes

user.profile / user.userprofile access mismatch

aimag null

filter location__aimag vs aimag field mismatch

superuser exception logic missing

delete permission override буруу

Likely files

inventory/models.py

inventory/admin.py

11. QR / passport debugging playbook

Symptoms:

QR token үүсэхгүй

public lookup 404

QR page data буруу

PDF passport generate болохгүй

Check order

QR action code

QR model/token logic

urls.py

views.py

PDF generation code

static/media access

Common causes

token save болоогүй

uuid route mismatch

wrong reverse URL

PDF font path issue

missing file response headers

Mongolian font register болоогүй

Likely files

inventory/admin.py

inventory/views.py

inventory/urls.py

PDF helper/util code

12. Encoding / patch debugging playbook

Symptoms:

Mongolian text эвдэрсэн

patch corrupt

BOM issue

git apply failed

Common causes

UTF-8 BOM

Windows encoding mismatch

copied patch content damaged

editor saved in wrong encoding

Safe practice

UTF-8 no-BOM ашиглах

patch-ийг plain text байдлаар хадгалах

large patch-ийг хэсэгчилж apply хийх

Commands
git apply patch.diff
git apply --reject patch.diff
git diff
Recovery
git restore .

эсвэл болгоомжтой:

git reset --hard
13. Model-field mismatch playbook

Symptoms:

admin references removed field

template references missing context/field

filter crashes on old field name

Check order

traceback field name

models.py дээр тухайн field байна уу

admin/forms/templates бүх reference update болсон уу

migrations applied болсон уу

Typical example

field name sum-аас sum_duureg болсон

admin/form/template дээр хуучин нэр үлдсэн

14. Queryset debugging playbook

Symptoms:

dropdown хоосон

admin changelist хоосон

report 0 count харуулна

filter буруу ажиллана

Check strategy

Django shell дээр queryset test хий

raw count ав

related field path зөв эсэхийг шалга

Example shell steps
python manage.py shell
from inventory.models import Device
Device.objects.count()
Device.objects.filter(location__aimag_id=1).count()
Common causes

wrong FK path

null related fields

filter name mismatch

role restriction хэтэрхий чанга

15. AJAX debugging playbook

Symptoms:

dropdown update болохгүй

frontend дээр loading боловч data ирэхгүй

400/403/404/500 response

Browser checks

network tab

request URL

request params

response JSON

response status code

Server checks

endpoint function hit болж байна уу

request.GET key зөв үү

queryset serialize болж байна уу

Common causes

csrf issue

wrong URL name

empty queryset

invalid JSON response

frontend expected {id, name} but backend өөр format буцаасан

16. Dashboard data debugging playbook

Symptoms:

chart 0 data

table хоосон

map marker алга

API returns empty list

Check order

queryset aggregation code

filters from request.GET

JSON serialization

template JS parsing

Shell test

aggregation-аа shell дээр ажиллуулж үз

empty data business issue юу code issue юу ялга

17. Safe debugging workflow

When a bug appears:

Phase 1 – Reproduce

яг ямар алхмаар гарч байгааг тэмдэглэ

Phase 2 – Classify

route уу?

form уу?

migration уу?

dashboard уу?

Phase 3 – Isolate

хамгийн бага file set сонго

Phase 4 – Fix

жижиг өөрчлөлт хий

нэг дор их refactor бүү хий

Phase 5 – Verify

previous page

related page

console

server log

permissions

export/action

Phase 6 – Record

BUGS_AND_PATCHES.md дээр тэмдэглэ

18. Minimal command toolkit
python manage.py check
python manage.py showmigrations
python manage.py migrate --plan
python manage.py migrate
python manage.py runserver
python manage.py shell
git status
git diff
git branch
19. High-risk files checklist

Бараг бүх том асуудал эхлээд эдгээрийг шалгана:

meteo_config/urls.py

inventory/models.py

inventory/forms.py

inventory/views.py

inventory/admin.py

inventory/urls.py

templates/admin/dashboard_general.html

templates/admin/dashboard_table.html

templates/admin/dashboard_graph.html

20. Regression check after every fix

Засвар бүрийн дараа доод тал нь эднийг шалга.

Route fix хийсэн бол

admin home

dashboard routes

affected reverse links

Form fix хийсэн бол

add form

change form

AJAX response

validation

Migration fix хийсэн бол

check

showmigrations

admin page load

create/edit object

Dashboard fix хийсэн бол

console clean

map load

chart load

filters work

Permission fix хийсэн бол

superuser

aimag engineer

delete button

filtered queryset

QR fix хийсэн бол

generate token

open public URL

PDF download

21. AI usage note

If AI is helping debug this repo, ask it to:

identify bug category

inspect only the most relevant files first

avoid broad refactors unless requested

explain root cause

provide minimal safe patch

update bug memory if needed

Suggested prompt:

Read BURTGEL_QUICKSTART_FOR_AI.md and BURTGEL_DEBUG_PLAYBOOK.md, then help me debug this error:
[paste traceback]
22. One-page emergency checklist

When stuck, do this:

python manage.py check

python manage.py showmigrations

read full traceback

inspect route/model/form/template depending on category

check browser console

test queryset in shell

make smallest possible fix

re-test

record in BUGS_AND_PATCHES.md

END