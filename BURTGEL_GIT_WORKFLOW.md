# BURTGEL GIT WORKFLOW

Project: БҮРТГЭЛ (BURTGEL)  
Repository: meteo_system  
Version control: Git + GitHub  

Энэ баримт нь БҮРТГЭЛ системийг Git ашиглан аюулгүй хөгжүүлэх стандарт workflow-г тодорхойлно.

---

# 1. Purpose

Git workflow-ийн зорилго:

- код алдахгүй байх
- гэр болон ажлын компьютер хооронд синк хийх
- patch / bug fix-үүдийг хянах
- migration conflict-оос сэргийлэх
- production кодыг тогтвортой хадгалах

---

# 2. Repository structure

GitHub repository:

https://github.com/tushigee79/meteo_system


Local project path example:


D:\meteo_system\


---

# 3. Main branches

Repository дараах branch-уудтай байна.

### main
Production-ready код.

### dev
Ерөнхий хөгжүүлэлт.

### feature/*
Шинэ feature.

Example:


feature/dashboard
feature/qr-passport
feature/lifecycle


### patch/*
Bug fix branch.

Example:


patch/admin-fix
patch/dashboard-fix


---

# 4. Daily development workflow

Өдөр бүр ажил эхлэхдээ:

```bash
git pull

Ажил дуусахдаа:

git add .
git commit -m "describe change"
git push
5. Safe commit rules

Commit хийхдээ:

жижиг өөрчлөлт бүр commit хийх

нэг commit = нэг логик өөрчлөлт

ойлгомжтой message бичих

Example commit messages:

fix dashboard route conflict
add QR passport action
refactor DeviceAdmin filters
fix aimag-sum cascade
6. Working on new feature

Шинэ feature эхлэхдээ:

git checkout -b feature/new-feature

Example:

git checkout -b feature/dashboard-map

Ажил дууссаны дараа:

git push origin feature/dashboard-map
7. Bug fixing workflow

Bug гарсан үед:

git checkout -b patch/bug-name

Example:

git checkout -b patch/dashboard-js

Fix хийсний дараа:

git commit
git push
8. Home ↔ Work computer workflow
Work computer дээр
git add .
git commit -m "work progress"
git push
Home computer дээр
git pull
Home дээр хийсэн өөрчлөлт
git add .
git commit -m "continue development"
git push
Work computer дээр буцааж
git pull
9. Emergency backup

Том өөрчлөлт хийхээс өмнө:

git branch backup-before-refactor

эсвэл

git tag backup_2026_03_12
10. Before applying patch

Patch apply хийхээс өмнө:

git status
git diff

Хэрвээ эрсдэлтэй бол:

git stash
11. If patch breaks code

Rollback:

git restore .

эсвэл

git reset --hard

⚠ Warning: local changes устна.

12. Migration safety rules

Migration commit хийхээс өмнө:

python manage.py makemigrations
python manage.py migrate
python manage.py check

Migration файлыг commit хийнэ.

git add .
git commit -m "add migration"
13. Files that should NOT be committed

Git ignore:

venv/
__pycache__/
db.sqlite3
.env
*.pyc
14. Checking repository state

Useful commands:

git status
git branch
git log
git diff
15. Recovering lost changes

If code lost:

git log

Old commit руу буцах:

git checkout commit_id
16. Typical safe workflow

Daily routine:

git pull
work
git add .
git commit -m "update"
git push
17. AI collaboration workflow

When AI helps development:

commit current state

apply suggested changes

test locally

commit again

Example:

git commit -m "before AI patch"
18. Recommended commit frequency

Хэт их код бичээд commit хийхгүй байж болохгүй.

Recommended:

30–60 минут тутам commit

feature бүр дээр commit

19. Production stability rule

Production branch (main) дээр:

experimental код push хийхгүй

dev branch-ээс merge хийж оруулна

20. One sentence rule

Always commit before making risky changes.

END