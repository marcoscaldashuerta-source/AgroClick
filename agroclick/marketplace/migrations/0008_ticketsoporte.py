# Generated manually for TicketSoporte (panel de soporte)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0007_carrito_itemcarrito'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketSoporte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razon', models.CharField(choices=[('problema_tecnico', 'Problema técnico'), ('pedido_producto', 'Consulta sobre pedido o producto'), ('cuenta_perfil', 'Problema con mi cuenta o perfil'), ('reclamo', 'Reclamo'), ('otro', 'Otro')], max_length=30)),
                ('descripcion', models.TextField()),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('en_proceso', 'En proceso'), ('resuelto', 'Resuelto')], default='pendiente', max_length=20)),
                ('respuesta_admin', models.TextField(blank=True, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('atendido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets_atendidos', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets_soporte', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha_creacion'],
            },
        ),
    ]
