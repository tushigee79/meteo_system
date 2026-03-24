# BURTGEL RELEASE CHECKLIST

Project: БҮРТГЭЛ (BURTGEL)  
Repository: meteo_system  
Framework: Django

Энэ checklist нь системийг production эсвэл шинэ version гаргахын өмнө заавал шалгах алхмуудыг тодорхойлно.

---

# 1. Purpose

Release checklist-ийн зорилго:

- production алдаа гарахаас сэргийлэх
- migration эвдрэлээс хамгаалах
- admin UI тогтвортой эсэхийг шалгах
- dashboard болон API ажиллаж байгаа эсэхийг баталгаажуулах
- системийн integrity-г хамгаалах

---

# 2. Pre-release Git check

Release хийхээс өмнө repository-г шалгана.

```bash
git status
git branch
git pull

Шалгах зүйлс:

uncommitted changes байхгүй

зөв branch дээр байгаа

remote repository-тэй sync болсон

3. Django system check
python manage.py check

Хүлээгдэх үр дүн:

System check identified no issues
4. Migration safety check

Migration статус шалгах.

python manage.py showmigrations

Хэрвээ unapplied migration байвал:

python manage.py migrate

Мөн migration plan шалгана.

python manage.py migrate --plan
5. Database integrity check

Django shell дээр data шалгана.

python manage.py shell

Example checks:

from inventory.models import Device
Device.objects.count()

Check:

Device data

Location data

InstrumentCatalog data

Organization data

6. Admin interface test

Admin-д нэвтэрч шалгана.

Test:

admin login

device list

device add form

device edit form

location admin

instrument catalog admin

7. Device lifecycle test

Device lifecycle үйлдлүүдийг шалгана.

Test:

device create

maintenance add

calibration add

device movement

adjustment add

Lifecycle history зөв харагдаж байгаа эсэхийг шалгана.

8. Dashboard test

Дараах dashboard-уудыг шалгана.

Routes:

/admin/dashboard/general/
/admin/dashboard/table/
/admin/dashboard/graph/

Шалгах:

chart load болж байна уу

map load болж байна уу

statistics зөв гарч байна уу

console error байхгүй

9. AJAX endpoint test

Browser network tab дээр шалгана.

Endpoints:

ajax/load-sums/
ajax/location-options/
ajax/catalog-by-kind/

Шалгах:

JSON response

status code = 200

dropdown update болж байгаа эсэх

10. Device form cascade test

Device form дээр:

Test:

Aimag → SumDuureg cascade

SumDuureg → Location cascade

Kind → InstrumentCatalog cascade

11. Permission test

User roles шалгана.

Roles:

superuser

aimag engineer

Aimag engineer:

зөвхөн өөрийн аймгийн data

delete permission байхгүй

12. QR system test

QR token generation.

Test:

QR generate

QR revoke

QR public lookup

Example URL:

/qr/public/<uuid>
13. Device passport test

Device passport PDF.

Test:

PDF generate

font зөв харагдаж байгаа

device info зөв

14. Reports test

Reports module.

Test:

CSV export

Excel export

report filters

15. Static files check

Production дээр static файлууд шалгана.

python manage.py collectstatic

Check:

CSS

JS

images

dashboard scripts

16. Security check

Шалгах:

DEBUG = False

SECRET_KEY safe

allowed hosts

admin URL protection

17. Performance sanity check

Large data үед:

admin list load time

dashboard query time

report export time

18. Backup before release

Release хийхээс өмнө:

Git tag үүсгэнэ.

git tag release_v1
git push origin release_v1
19. Release commit

Release commit message.

Example:

release: BURTGEL v1.0 stability release
20. Post-release monitoring

Release дараа:

server logs

admin errors

user feedback

dashboard performance

21. Emergency rollback

Хэрвээ асуудал гарвал:

git checkout previous_commit

эсвэл

git reset --hard
22. Final release rule

Never deploy without running the checklist.

END