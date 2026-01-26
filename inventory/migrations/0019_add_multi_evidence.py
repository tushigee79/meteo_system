# inventory/migrations/0019_add_multi_evidence.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0018_add_service_and_control"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceEvidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="evidence/maintenance/%Y/%m/", verbose_name="Нотлох баримт (файл)")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidences", to="inventory.maintenanceservice", verbose_name="Засвар, үйлчилгээ")),
            ],
            options={
                "verbose_name": "Засварын нотлох баримт",
                "verbose_name_plural": "Засварын нотлох баримтууд",
                "ordering": ["-uploaded_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ControlEvidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="evidence/control/%Y/%m/", verbose_name="Нотлох баримт (файл)")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("control", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidences", to="inventory.controladjustment", verbose_name="Хяналт, тохируулга")),
            ],
            options={
                "verbose_name": "Хяналтын нотлох баримт",
                "verbose_name_plural": "Хяналтын нотлох баримтууд",
                "ordering": ["-uploaded_at", "-id"],
            },
        ),
    ]
