# Generated manually for SolicitudEntrega (checkout: delivery o retiro en tienda)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0008_ticketsoporte'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudEntrega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_entrega', models.CharField(choices=[('delivery', 'Delivery'), ('tienda', 'Entrega en la tienda')], max_length=20)),
                ('direccion_entrega', models.CharField(blank=True, max_length=255, null=True)),
                ('referencia', models.CharField(blank=True, max_length=255, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('comprador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_entrega', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha_creacion'],
            },
        ),
    ]
