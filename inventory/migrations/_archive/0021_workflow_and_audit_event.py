# inventory/migrations/0020_workflow_and_audit_event.py
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def forwards(apps, schema_editor):
    MaintenanceService = apps.get_model("inventory", "MaintenanceService")
    ControlAdjustment = apps.get_model("inventory", "ControlAdjustment")

    # Existing records-ийг workflow-д "APPROVED" гэж backfill хийнэ (хуучин өгөгдөл гацахгүй)
    MaintenanceService.objects.all().update(workflow_status="APPROVED")
    ControlAdjustment.objects.all().update(workflow_status="APPROVED")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0019_add_multi_evidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("CREATE","CREATE"),("UPDATE","UPDATE"),("DELETE","DELETE"),("SUBMIT","SUBMIT"),("APPROVE","APPROVE"),("REJECT","REJECT"),("LIFECYCLE","LIFECYCLE"),("NOTIFY","NOTIFY")], max_length=20, verbose_name="Үйлдэл")),
                ("model_label", models.CharField(max_length=100, verbose_name="Model")),
                ("object_id", models.CharField(blank=True, default="", max_length=50, verbose_name="Object ID")),
                ("object_repr", models.CharField(blank=True, default="", max_length=255, verbose_name="Object")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("changes", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to="auth.user", verbose_name="Хэрэглэгч")),
            ],
            options={"ordering": ["-created_at", "-id"], "verbose_name": "Audit event", "verbose_name_plural": "Audit events"},
        ),

        # --- MaintenanceService workflow fields ---
        migrations.AddField(
            model_name="maintenanceservice",
            name="workflow_status",
            field=models.CharField(choices=[("DRAFT","Draft"),("SUBMITTED","Submitted"),("APPROVED","Approved"),("REJECTED","Rejected")], default="DRAFT", max_length=12, verbose_name="Workflow төлөв"),
        ),
        migrations.AddField(model_name="maintenanceservice", name="submitted_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Илгээсэн огноо")),
        migrations.AddField(model_name="maintenanceservice", name="approved_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Баталсан огноо")),
        migrations.AddField(model_name="maintenanceservice", name="rejected_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Татгалзсан огноо")),
        migrations.AddField(model_name="maintenanceservice", name="reject_reason", field=models.TextField(blank=True, default="", verbose_name="Reject шалтгаан")),
        migrations.AddField(
            model_name="maintenanceservice",
            name="submitted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ms_submitted", to="auth.user", verbose_name="Илгээсэн хэрэглэгч"),
        ),
        migrations.AddField(
            model_name="maintenanceservice",
            name="approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ms_approved", to="auth.user", verbose_name="Баталсан хэрэглэгч"),
        ),
        migrations.AddField(
            model_name="maintenanceservice",
            name="rejected_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ms_rejected", to="auth.user", verbose_name="Татгалзсан хэрэглэгч"),
        ),

        # --- ControlAdjustment workflow fields ---
        migrations.AddField(
            model_name="controladjustment",
            name="workflow_status",
            field=models.CharField(choices=[("DRAFT","Draft"),("SUBMITTED","Submitted"),("APPROVED","Approved"),("REJECTED","Rejected")], default="DRAFT", max_length=12, verbose_name="Workflow төлөв"),
        ),
        migrations.AddField(model_name="controladjustment", name="submitted_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Илгээсэн огноо")),
        migrations.AddField(model_name="controladjustment", name="approved_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Баталсан огноо")),
        migrations.AddField(model_name="controladjustment", name="rejected_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Татгалзсан огноо")),
        migrations.AddField(model_name="controladjustment", name="reject_reason", field=models.TextField(blank=True, default="", verbose_name="Reject шалтгаан")),
        migrations.AddField(
            model_name="controladjustment",
            name="submitted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ca_submitted", to="auth.user", verbose_name="Илгээсэн хэрэглэгч"),
        ),
        migrations.AddField(
            model_name="controladjustment",
            name="approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ca_approved", to="auth.user", verbose_name="Баталсан хэрэглэгч"),
        ),
        migrations.AddField(
            model_name="controladjustment",
            name="rejected_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ca_rejected", to="auth.user", verbose_name="Татгалзсан хэрэглэгч"),
        ),

        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
