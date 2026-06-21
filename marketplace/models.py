from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    ROL_CHOICES = [
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
    ]

    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    aprobado = models.BooleanField(default=False)

    def __str__(self):
        return self.usuario.username