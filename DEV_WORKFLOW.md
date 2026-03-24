# BURTGEL DEVELOPMENT WORKFLOW

БҮРТГЭЛ системийг хөгжүүлэх стандарт workflow  
(гэрийн компьютер + ажлын компьютер + GitHub)

---

# 1. Development environment

Framework
Django 4.2

Python
3.13

Database
SQLite (dev)

Main repository

https://github.com/tushigee79/meteo_system.git

---

# 2. Basic rule

Ямар ч өөрчлөлт хийхээс өмнө:

1 update хийх
2 branch шалгах
3 local test хийх

---

# 3. Start working (any computer)

Terminal дээр:

git pull

дараа нь:

python manage.py check

дараа нь:

python manage.py runserver

4. Development flow
Step 1

code өөрчлөх

example

inventory/admin.py
inventory/models.py
inventory/forms.py
Step 2

local test

python manage.py check
python manage.py runserver

dashboard
device form
admin route
test хийх

Step 3

git status

git status
Step 4

commit

git add .
git commit -m "dashboard fix"
Step 5

push

git push origin feature/dashboard
5. Home computer → Work computer

Ажлын компьютер дээр:

git pull

дараа нь:

python manage.py runserver
6. Work computer → Home computer

гэртээ:

git pull
7. Before making risky change

backup branch үүсгэнэ

git checkout -b backup-admin-before-refactor

дараа нь код өөрчилнө

8. Migration workflow

models өөрчлөх үед

python manage.py makemigrations
python manage.py migrate

дараа нь commit

git add .
git commit -m "migration update"
9. Debug workflow

алдаа гарвал дараах дарааллаар шалгана

1
python manage.py check
2
python manage.py showmigrations
3
python manage.py migrate
4

browser console

5

urls.py шалгах

10. Dashboard debug

дараах файлууд шалгана

inventory/admin.py
templates/admin/dashboard_general.html
templates/admin/dashboard_table.html
templates/admin/dashboard_graph.html
11. Device form debug
inventory/forms.py
inventory/views.py
inventory/admin.py
inventory/static/
12. Route debug
meteo_config/urls.py
inventory/urls.py
inventory/admin.py
13. Patch workflow

patch apply хийх үед

git apply patch.diff

алдаа гарвал

git apply --reject patch.diff
14. Safe restore

код эвдэрвэл

git restore .

эсвэл

git reset --hard
15. Useful commands

branch харах

git branch

commit history

git log --oneline

diff

git diff
16. Project memory files

AI ашиглах үед:

AI_MEMORY.md
PROJECT_CONTEXT.md
PROJECT_INDEX.md
BUGS_AND_PATCHES.md
17. AI workflow

AI-д дараах prompt ашиглана

Read AI_MEMORY.md
Read PROJECT_CONTEXT.md
Read PROJECT_INDEX.md
Read BUGS_AND_PATCHES.md
Continue BURTGEL development
18. Final rule

production logic-г шууд устгахгүй.

алдсан бол

backup branch
эсвэл git restore ашиглана.

END

---

# Одоо танай project дээр байгаа **AI developer toolkit**


AI_MEMORY.md
PROJECT_CONTEXT.md
PROJECT_INDEX.md
BUGS_AND_PATCHES.md
DEV_WORKFLOW.md


Энэ 5 файлтай бол:

- AI project-ийг **шууд ойлгоно**
- bug history **алга болохгүй**
- home/work **workflow тодорхой**
- шинэ чатанд **context алдагдахгүй**

---

💡 Хэрвээ хүсвэл дараагийн шатанд би танд **маш том upgrade** хийж өгч чадна:

### BURTGEL_SYSTEM_ARCHITECTURE.md

Энэ файлд:

- system diagram
- model relationship
- lifecycle workflow
- admin architecture
- data flow

бүгд орно.

Тэрийг хийчихвэл таны **БҮРТГЭЛ систем бараг enterprise түвшний documentation-той болно.** 🚀