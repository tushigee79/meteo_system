from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    # ⚠️ Adjust dependency to your latest migration if needed
    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowDailyAgg",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField(db_index=True, verbose_name="Огноо (өдөр)")),
                ("kind", models.CharField(blank=True, default="", max_length=20, verbose_name="Device kind")),
                ("location_type", models.CharField(blank=True, default="", max_length=20, verbose_name="Location type")),
                ("ms_submitted", models.PositiveIntegerField(default=0)),
                ("ms_approved", models.PositiveIntegerField(default=0)),
                ("ms_rejected", models.PositiveIntegerField(default=0)),
                ("ca_submitted", models.PositiveIntegerField(default=0)),
                ("ca_approved", models.PositiveIntegerField(default=0)),
                ("ca_rejected", models.PositiveIntegerField(default=0)),
                ("sla_avg_hours", models.FloatField(default=0.0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("aimag", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflow_daily_aggs", to="inventory.aimag")),
            ],
            options={
                "verbose_name": "Workflow daily aggregation",
                "verbose_name_plural": "Workflow daily aggregations",
                "unique_together": {("day", "aimag", "kind", "location_type")},
                "indexes": [
                    models.Index(fields=["day"], name="inventory_wo_day_7b7b4a_idx"),
                    models.Index(fields=["day", "aimag"], name="inventory_wo_day_ai_4b3d30_idx"),
                    models.Index(fields=["day", "kind"], name="inventory_wo_day_ki_35b3fd_idx"),
                    models.Index(fields=["day", "location_type"], name="inventory_wo_day_lo_c4e5bb_idx"),
                ],
            },
        ),
    ]
