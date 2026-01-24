# inventory/migrations/00XX_add_service_and_control.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
       ("inventory", "0017_alter_instrumentcatalog_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="Огноо")),
                ("reason", models.CharField(choices=[("NORMAL", "Хэвийн засвар үйлчилгээ"), ("LIMITED", "Хязгаарлагдмал ажиллагаа"), ("NOT_WORKING", "Ажиллагаагүй болсон")], default="NORMAL", max_length=20, verbose_name="Засвар хийсэн шалтгаан")),
                ("performer_type", models.CharField(choices=[("ENGINEER", "Инженер"), ("ORG", "Байгууллага")], default="ENGINEER", max_length=10, verbose_name="Хийсэн этгээд (төрөл)")),
                ("performer_engineer_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Хийсэн инженер (нэр)")),
                ("performer_org_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Хийсэн байгууллага (нэр)")),
                ("evidence", models.FileField(blank=True, null=True, upload_to="evidence/maintenance/%Y/%m/", verbose_name="Нотлох баримт (файл)")),
                ("note", models.TextField(blank=True, default="", verbose_name="Тайлбар / тэмдэглэл")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="maintenance_services", to="inventory.device", verbose_name="Багаж / Төхөөрөмж")),
            ],
            options={
                "verbose_name": "Засвар, үйлчилгээ",
                "verbose_name_plural": "Засвар, үйлчилгээ",
                "ordering": ["-date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ControlAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="Огноо")),
                ("result", models.CharField(choices=[("PASS", "PASS - Хэвийн"), ("LIMITED", "Хязгаарлагдмал"), ("FAIL", "FAIL - Ажиллагаагүй")], default="PASS", max_length=20, verbose_name="Үр дүн")),
                ("performer_type", models.CharField(choices=[("ENGINEER", "Инженер"), ("ORG", "Байгууллага")], default="ENGINEER", max_length=10, verbose_name="Хийсэн этгээд (төрөл)")),
                ("performer_engineer_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Хийсэн инженер (нэр)")),
                ("performer_org_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Хийсэн байгууллага (нэр)")),
                ("evidence", models.FileField(blank=True, null=True, upload_to="evidence/control/%Y/%m/", verbose_name="Нотлох баримт (файл)")),
                ("note", models.TextField(blank=True, default="", verbose_name="Тайлбар / тэмдэглэл")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_adjustments", to="inventory.device", verbose_name="Багаж / Төхөөрөмж")),
            ],
            options={
                "verbose_name": "Хяналт, тохируулга",
                "verbose_name_plural": "Хяналт, тохируулга",
                "ordering": ["-date", "-id"],
            },
        ),
    ]
