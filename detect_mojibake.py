import os
import sys
import django
import re

# 1. Django орчныг тохируулах
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meteo_config.settings')

try:
    django.setup()
    print("✅ Django амжилттай ачаалагдлаа.")
except Exception as e:
    print(f"❌ Алдаа: Django-г ачаалж чадсангүй. {e}")
    print("Зөвлөмж: urls.py дээрх бичлэгийн алдаагаа засаарай.")
    sys.exit(1)

from django.apps import apps
from django.db import transaction, OperationalError

# Mojibake илрүүлэх regex
MOJIBAKE_RE = re.compile(r'[\u00C0-\u00FF][\u0080-\u00BF]')

def process_mojibake(fix=False):
    found_count = 0
    fixed_count = 0
    
    for model in apps.get_models():
        # Зөвхөн текст төрлийн талбаруудыг шүүх
        fields = [f.name for f in model._meta.fields if f.get_internal_type() in ("CharField", "TextField")]
        if not fields:
            continue
            
        print(f"🔎 Шалгаж байна: {model._meta.app_label}.{model.__name__}...")
        
        try:
            # .only() ашиглах нь багана дутуу үед алдаа заагаад байгаа тул 
            # бүх талбараар нь ачаалж, алдааг барьж авна.
            queryset = model.objects.all()
            
            for obj in queryset:
                needs_fix = False
                for field in fields:
                    try:
                        val = getattr(obj, field)
                    except Exception:
                        continue # Хэрэв багана өгөгдлийн санд байхгүй бол алгасах
                    
                    if isinstance(val, str) and MOJIBAKE_RE.search(val):
                        found_count += 1
                        try:
                            corrected = val.encode('latin-1').decode('utf-8')
                            print(f"  [Олдлоо] ID:{obj.pk} | Талбар:{field}")
                            print(f"    Буруу: {val}")
                            print(f"    Зөв:   {corrected}")
                            
                            if fix:
                                setattr(obj, field, corrected)
                                needs_fix = True
                        except:
                            continue
                
                if fix and needs_fix:
                    try:
                        obj.save()
                        fixed_count += 1
                    except Exception as e:
                        print(f"  ❌ Хадгалж чадсангүй ID:{obj.pk}: {e}")

        except OperationalError as e:
            print(f"  ⚠️ Энэ хүснэгтийг алгаслаа (Migration алдаатай): {e}")
            continue

    print(f"\n{'-'*30}")
    print(f"📊 ҮР ДҮН:")
    print(f"Нийт олдсон алдаатай талбар: {found_count}")
    if fix:
        print(f"Амжилттай зассан бичлэг: {fixed_count}")

if __name__ == "__main__":
    should_fix = len(sys.argv) > 1 and sys.argv[1].lower() == 'fix'
    
    if should_fix:
        print("⚠️ АНХААР: Өгөгдлийг засаж эхэллээ...")
        try:
            with transaction.atomic():
                process_mojibake(fix=True)
        except Exception as e:
            print(f"❌ Гүйлгээ цуцлагдлаа: {e}")
    else:
        process_mojibake(fix=False)