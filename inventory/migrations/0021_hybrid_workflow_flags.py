
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_add_workflow_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenanceservice',
            name='self_verified',
            field=models.BooleanField(default=False, verbose_name='Аймаг өөрөө баталсан'),
        ),
        migrations.AddField(
            model_name='maintenanceservice',
            name='central_verified',
            field=models.BooleanField(default=False, verbose_name='Төвөөр баталгаажсан'),
        ),
        migrations.AddField(
            model_name='maintenanceservice',
            name='central_review_required',
            field=models.BooleanField(default=False, verbose_name='Төвийн баталгаа шаардлагатай'),
        ),
        migrations.AddField(
            model_name='controladjustment',
            name='self_verified',
            field=models.BooleanField(default=False, verbose_name='Аймаг өөрөө баталсан'),
        ),
        migrations.AddField(
            model_name='controladjustment',
            name='central_verified',
            field=models.BooleanField(default=False, verbose_name='Төвөөр баталгаажсан'),
        ),
        migrations.AddField(
            model_name='controladjustment',
            name='central_review_required',
            field=models.BooleanField(default=False, verbose_name='Төвийн баталгаа шаардлагатай'),
        ),
    ]
