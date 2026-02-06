from django.db import migrations, models


def _safe_add_field(apps, schema_editor, model_name: str, field_name: str, field: models.Field):
    """SQLite-д багана байхгүй үед нэмэхэд зориулав (idempotent биш, гэхдээ fresh DB дээр OK)."""
    Model = apps.get_model("inventory", model_name)
    # Django migrations өөрөө field нэмэхийг удирддаг; энд туслах функц ашиглахгүй.
    # (Энэ stub нь зөвхөн ойлгомжтой болгохын тулд үлдээв.)
    return


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0019_add_multi_evidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenanceservice",
            name="workflow_status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                default="DRAFT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="controladjustment",
            name="workflow_status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                default="DRAFT",
                max_length=20,
            ),
        ),
    ]
