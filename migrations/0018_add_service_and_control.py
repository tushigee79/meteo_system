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
                ("date", models.DateField(verbose_name="ÐžÐ³Ð½Ð¾Ð¾")),
                ("reason", models.CharField(choices=[("NORMAL", "Ð¥ÑÐ²Ð¸Ð¹Ð½ Ð·Ð°ÑÐ²Ð°Ñ€ Ò¯Ð¹Ð»Ñ‡Ð¸Ð»Ð³ÑÑ"), ("LIMITED", "Ð¥ÑÐ·Ð³Ð°Ð°Ñ€Ð»Ð°Ð³Ð´Ð¼Ð°Ð» Ð°Ð¶Ð¸Ð»Ð»Ð°Ð³Ð°Ð°"), ("NOT_WORKING", "ÐÐ¶Ð¸Ð»Ð»Ð°Ð³Ð°Ð°Ð³Ò¯Ð¹ Ð±Ð¾Ð»ÑÐ¾Ð½")], default="NORMAL", max_length=20, verbose_name="Ð—Ð°ÑÐ²Ð°Ñ€ Ñ…Ð¸Ð¹ÑÑÐ½ ÑˆÐ°Ð»Ñ‚Ð³Ð°Ð°Ð½")),
                ("performer_type", models.CharField(choices=[("ENGINEER", "Ð˜Ð½Ð¶ÐµÐ½ÐµÑ€"), ("ORG", "Ð‘Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð°")], default="ENGINEER", max_length=10, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ ÑÑ‚Ð³ÑÑÐ´ (Ñ‚Ó©Ñ€Ó©Ð»)")),
                ("performer_engineer_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ Ð¸Ð½Ð¶ÐµÐ½ÐµÑ€ (Ð½ÑÑ€)")),
                ("performer_org_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ Ð±Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð° (Ð½ÑÑ€)")),
                ("evidence", models.FileField(blank=True, null=True, upload_to="evidence/maintenance/%Y/%m/", verbose_name="ÐÐ¾Ñ‚Ð»Ð¾Ñ… Ð±Ð°Ñ€Ð¸Ð¼Ñ‚ (Ñ„Ð°Ð¹Ð»)")),
                ("note", models.TextField(blank=True, default="", verbose_name="Ð¢Ð°Ð¹Ð»Ð±Ð°Ñ€ / Ñ‚ÑÐ¼Ð´ÑÐ³Ð»ÑÐ»")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="maintenance_services", to="inventory.device", verbose_name="Багаж / Ð¢Ó©Ñ…Ó©Ó©Ñ€Ó©Ð¼Ð¶")),
            ],
            options={
                "verbose_name": "Ð—Ð°ÑÐ²Ð°Ñ€, Ò¯Ð¹Ð»Ñ‡Ð¸Ð»Ð³ÑÑ",
                "verbose_name_plural": "Ð—Ð°ÑÐ²Ð°Ñ€, Ò¯Ð¹Ð»Ñ‡Ð¸Ð»Ð³ÑÑ",
                "ordering": ["-date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ControlAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="ÐžÐ³Ð½Ð¾Ð¾")),
                ("result", models.CharField(choices=[("PASS", "PASS - Ð¥ÑÐ²Ð¸Ð¹Ð½"), ("LIMITED", "Ð¥ÑÐ·Ð³Ð°Ð°Ñ€Ð»Ð°Ð³Ð´Ð¼Ð°Ð»"), ("FAIL", "FAIL - ÐÐ¶Ð¸Ð»Ð»Ð°Ð³Ð°Ð°Ð³Ò¯Ð¹")], default="PASS", max_length=20, verbose_name="Ò®Ñ€ Ð´Ò¯Ð½")),
                ("performer_type", models.CharField(choices=[("ENGINEER", "Ð˜Ð½Ð¶ÐµÐ½ÐµÑ€"), ("ORG", "Ð‘Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð°")], default="ENGINEER", max_length=10, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ ÑÑ‚Ð³ÑÑÐ´ (Ñ‚Ó©Ñ€Ó©Ð»)")),
                ("performer_engineer_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ Ð¸Ð½Ð¶ÐµÐ½ÐµÑ€ (Ð½ÑÑ€)")),
                ("performer_org_name", models.CharField(blank=True, default="", max_length=255, verbose_name="Ð¥Ð¸Ð¹ÑÑÐ½ Ð±Ð°Ð¹Ð³ÑƒÑƒÐ»Ð»Ð°Ð³Ð° (Ð½ÑÑ€)")),
                ("evidence", models.FileField(blank=True, null=True, upload_to="evidence/control/%Y/%m/", verbose_name="ÐÐ¾Ñ‚Ð»Ð¾Ñ… Ð±Ð°Ñ€Ð¸Ð¼Ñ‚ (Ñ„Ð°Ð¹Ð»)")),
                ("note", models.TextField(blank=True, default="", verbose_name="Ð¢Ð°Ð¹Ð»Ð±Ð°Ñ€ / Ñ‚ÑÐ¼Ð´ÑÐ³Ð»ÑÐ»")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="control_adjustments", to="inventory.device", verbose_name="Багаж / Ð¢Ó©Ñ…Ó©Ó©Ñ€Ó©Ð¼Ð¶")),
            ],
            options={
                "verbose_name": "Ð¥ÑÐ½Ð°Ð»Ñ‚, Ñ‚Ð¾Ñ…Ð¸Ñ€ÑƒÑƒÐ»Ð³Ð°",
                "verbose_name_plural": "Ð¥ÑÐ½Ð°Ð»Ñ‚, Ñ‚Ð¾Ñ…Ð¸Ñ€ÑƒÑƒÐ»Ð³Ð°",
                "ordering": ["-date", "-id"],
            },
        ),
    ]

