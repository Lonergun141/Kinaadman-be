from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repository', '0003_thesismetadataversion_thesis_campus_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='thesis',
            name='panel_approval_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='thesis',
            name='panel_approval_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                default='PENDING',
                max_length=20,
            ),
        ),
    ]
