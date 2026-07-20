from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0009_solicitudentrega'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudentrega',
            name='tipo_pago',
            field=models.CharField(
                choices=[('transferencia', 'Transferencia'), ('efectivo', 'Efectivo')],
                default='efectivo',
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
